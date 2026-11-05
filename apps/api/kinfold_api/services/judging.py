from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from kinfold_api.constants import CROWD_CATEGORIES, TRAP_PRAISE_SCORE_THRESHOLD
from kinfold_api.models import Agent, Duel, DuelEntry, Vote
from kinfold_api.services.critique_moderation import check_critique_text
from kinfold_api.services.duels import agent_info_lookup, winning_entry_id
from kinfold_api.services.events import append_event

# A crude, documented heuristic for "collapse agreement-only critiques" —
# not sentiment analysis, just: is there enough actual text here to be a
# critique at all? See docs/decisions.md, 2026-10-31.
_MIN_SUBSTANTIVE_LENGTH = 15


def _is_substantive(strengths: str, weaknesses: str) -> bool:
    return len(strengths.strip()) >= _MIN_SUBSTANTIVE_LENGTH or (
        len(weaknesses.strip()) >= _MIN_SUBSTANTIVE_LENGTH
    )


def cast_agent_judgment(
    db: Session,
    *,
    duel: Duel,
    judge: Agent,
    entry_id: uuid.UUID,
    strengths: str,
    weaknesses: str,
    verdict: str,
    score: int,
) -> Vote:
    """An agent's structured critique of a crowd duel. Never counts toward
    resolving the duel — only human votes do. "Judge the work, not the
    person" is enforced two ways: by scope (a critique attaches to one
    entry's answer, there's no field for anything else) and by a keyword
    heuristic over the free-text fields (see critique_moderation.py) — the
    heuristic is a known, documented limitation, not full NLP moderation."""
    if judge.is_disabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This agent has been disabled.")
    check_critique_text(strengths, weaknesses, verdict)

    if duel.category not in CROWD_CATEGORIES:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only crowd duels take agent judgments.")
    if duel.status != "judging":
        raise HTTPException(status.HTTP_409_CONFLICT, "This duel isn't open for judging.")

    entries = (
        db.execute(select(DuelEntry).where(DuelEntry.duel_id == duel.id).order_by(DuelEntry.slot))
        .scalars()
        .all()
    )
    if len(entries) != 2:
        raise HTTPException(status.HTTP_409_CONFLICT, "This duel doesn't have two entries yet.")

    chosen = next((e for e in entries if e.id == entry_id), None)
    if chosen is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That entry doesn't belong to this duel.")

    if judge.id in {entry.agent_id for entry in entries}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "An agent can't judge a duel it's entered.")

    # Agents run by the same owner are not independent judges of each
    # other — one owner could otherwise steer the result (and judge
    # rating) with a second agent.
    entrant_owner_ids: set[uuid.UUID] = set()
    for entry in entries:
        if entry.agent_id is not None:
            entrant = db.get(Agent, entry.agent_id)
            if entrant is not None:
                entrant_owner_ids.add(entrant.owner_id)
        if entry.human_owner_id is not None:
            entrant_owner_ids.add(entry.human_owner_id)
    if judge.owner_id in entrant_owner_ids:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Agents run by the same owner as an entrant can't judge this duel.",
        )

    existing = db.execute(
        select(Vote).where(
            Vote.duel_id == duel.id, Vote.voter_type == "agent", Vote.voter_agent_id == judge.id
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This agent has already judged this duel.")

    judgment = Vote(
        duel_id=duel.id,
        voter_type="agent",
        voter_agent_id=judge.id,
        chosen_entry_id=chosen.id,
        strengths=strengths,
        weaknesses=weaknesses,
        verdict=verdict,
        score=score,
    )
    db.add(judgment)
    db.flush()

    append_event(
        db,
        type="judgment.cast",
        agent_id=judge.id,
        owner_id=judge.owner_id,
        payload={"duel_id": str(duel.id), "chosen_entry_id": str(chosen.id)},
    )
    db.commit()
    db.refresh(judgment)
    return judgment


def score_judgments_against_result(db: Session, duel: Duel) -> None:
    """Called once a crowd duel resolves. Every agent judgment on it gets
    scored and moves that agent's judge rating. Two independent checks:

    1. Trap check (takes priority): if this duel has a silently planted
       trap entry and the judgment scored it at or above
       TRAP_PRAISE_SCORE_THRESHOLD, that's a judge getting fooled by a
       known-bad answer — penalized regardless of the human-vote result.
    2. Otherwise, agreement with the human-vote winner: agreement raises
       judge rating, disagreement lowers it. A draw gives no ground truth,
       so non-trap judgments on a drawn duel aren't scored at all.
    """
    from kinfold_api.config import get_settings  # local import avoids a cycle at module load

    k_factor = get_settings().KINFOLD_JUDGE_RATING_K_FACTOR

    entries = (
        db.execute(select(DuelEntry).where(DuelEntry.duel_id == duel.id)).scalars().all()
    )
    trap_entry = next((e for e in entries if e.is_trap), None)
    winner_id = winning_entry_id(duel, entries)

    judgments = db.execute(
        select(Vote).where(Vote.duel_id == duel.id, Vote.voter_type == "agent")
    ).scalars().all()

    for judgment in judgments:
        judge = db.get(Agent, judgment.voter_agent_id)
        if judge is None:
            continue

        praised_trap = (
            trap_entry is not None
            and judgment.chosen_entry_id == trap_entry.id
            and (judgment.score or 0) >= TRAP_PRAISE_SCORE_THRESHOLD
        )

        if praised_trap:
            delta = -k_factor
            event_type = "judgment.trap_praised"
            payload = {
                "duel_id": str(duel.id),
                "judgment_id": str(judgment.id),
                "judge_rating_delta": delta,
            }
        elif winner_id is not None:
            agreed = judgment.chosen_entry_id == winner_id
            delta = k_factor if agreed else -k_factor
            event_type = "judgment.scored"
            payload = {
                "duel_id": str(duel.id),
                "judgment_id": str(judgment.id),
                "agreed": agreed,
                "judge_rating_delta": delta,
            }
        else:
            continue  # draw and not a trap-praise — no ground truth either way

        judge.judge_rating = max(0, judge.judge_rating + delta)
        db.flush()
        append_event(db, type=event_type, agent_id=judge.id, owner_id=judge.owner_id, payload=payload)


def list_judgments(db: Session, duel: Duel) -> list[Vote]:
    """Judgments are shown only once the duel resolves — same rule as
    entries — so they can't sway human votes still being cast. Ordered
    oldest first; judgment_out_data re-sorts substantive critiques first
    for display, which is where "collapse agreement-only" actually
    happens (see docs/decisions.md, 2026-10-31)."""
    if duel.status != "resolved":
        return []
    return list(
        db.execute(
            select(Vote)
            .where(
                Vote.duel_id == duel.id,
                Vote.voter_type == "agent",
                Vote.hidden_at.is_(None),
            )
            .order_by(Vote.created_at.asc())
        ).scalars()
    )


def judgment_out_data(db: Session, duel: Duel, judgments: list[Vote]) -> list[dict]:
    infos = agent_info_lookup(db, [j.voter_agent_id for j in judgments])
    entries = db.execute(select(DuelEntry).where(DuelEntry.duel_id == duel.id)).scalars().all()
    winner_id = winning_entry_id(duel, entries)
    out = []
    for j in judgments:
        info = infos.get(j.voter_agent_id)
        agreed_with_result = None if winner_id is None else j.chosen_entry_id == winner_id
        out.append(
            {
                "id": j.id,
                "duel_id": j.duel_id,
                "agent_id": j.voter_agent_id,
                "agent_name": info.name if info else None,
                "chosen_entry_id": j.chosen_entry_id,
                "strengths": j.strengths,
                "weaknesses": j.weaknesses,
                "verdict": j.verdict,
                "score": j.score,
                "agreed_with_result": agreed_with_result,
                "is_substantive": _is_substantive(j.strengths or "", j.weaknesses or ""),
                "entrant_rated_useful": j.entrant_rated_useful,
                "created_at": j.created_at,
            }
        )
    # Substantive critiques first — an "agreement-only" critique (short,
    # no real reasoning) collapses to the bottom rather than being hidden
    # outright, so nothing is silently deleted.
    out.sort(key=lambda row: (not row["is_substantive"], row["created_at"]))
    return out


def rate_judgment_useful(
    db: Session,
    *,
    judgment: Vote,
    rating_agent_id: uuid.UUID | None,
    rating_owner_id: uuid.UUID | None,
    useful: bool,
) -> Vote:
    """Only the entrant whose answer this judgment critiqued can rate it —
    not the judge, not a bystander. Works whether that entrant is an agent
    or a human (crowd duels can have either since human entries shipped)."""
    entry = db.get(DuelEntry, judgment.chosen_entry_id)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    is_the_entrant = (entry.agent_id is not None and entry.agent_id == rating_agent_id) or (
        entry.human_owner_id is not None and entry.human_owner_id == rating_owner_id
    )
    if not is_the_entrant:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Only the entrant this judgment critiqued can rate it."
        )

    judgment.entrant_rated_useful = useful
    db.flush()

    event_owner_id = rating_owner_id
    if rating_agent_id is not None:
        rating_agent = db.get(Agent, rating_agent_id)
        event_owner_id = rating_agent.owner_id if rating_agent else None

    append_event(
        db,
        type="judgment.rated_useful",
        agent_id=rating_agent_id,
        owner_id=event_owner_id,
        payload={"judgment_id": str(judgment.id), "useful": useful},
    )
    db.commit()
    db.refresh(judgment)
    return judgment
