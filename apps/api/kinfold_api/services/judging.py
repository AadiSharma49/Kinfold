from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from kinfold_api.constants import CROWD_CATEGORIES
from kinfold_api.models import Agent, Duel, DuelEntry, Vote
from kinfold_api.services.duels import agent_info_lookup
from kinfold_api.services.events import append_event


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
    resolving the duel — only human votes do. Judge the work, not the
    person: this is enforced by scope (a critique attaches to one entry's
    answer, there's no field for anything else), not by content filtering,
    which is a known gap — see docs/decisions.md."""
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
    checked against the human-vote result and moves that agent's judge
    rating — agreement raises it, disagreement lowers it. A draw gives no
    ground truth, so judgments on a drawn duel are skipped, not scored."""
    if duel.is_draw or duel.winner_agent_id is None:
        return

    from kinfold_api.config import get_settings  # local import avoids a cycle at module load

    k_factor = get_settings().KINFOLD_JUDGE_RATING_K_FACTOR

    judgments = db.execute(
        select(Vote).where(Vote.duel_id == duel.id, Vote.voter_type == "agent")
    ).scalars().all()
    if not judgments:
        return

    entries = (
        db.execute(select(DuelEntry).where(DuelEntry.duel_id == duel.id)).scalars().all()
    )
    winning_entry_id = next(e.id for e in entries if e.agent_id == duel.winner_agent_id)

    for judgment in judgments:
        judge = db.get(Agent, judgment.voter_agent_id)
        if judge is None:
            continue
        agreed = judgment.chosen_entry_id == winning_entry_id
        delta = k_factor if agreed else -k_factor
        judge.judge_rating = max(0, judge.judge_rating + delta)
        db.flush()

        append_event(
            db,
            type="judgment.scored",
            agent_id=judge.id,
            owner_id=judge.owner_id,
            payload={
                "duel_id": str(duel.id),
                "judgment_id": str(judgment.id),
                "agreed": agreed,
                "judge_rating_delta": delta,
            },
        )


def list_judgments(db: Session, duel: Duel) -> list[Vote]:
    """Judgments are shown only once the duel resolves — same rule as
    entries — so they can't sway human votes still being cast."""
    if duel.status != "resolved":
        return []
    return list(
        db.execute(
            select(Vote)
            .where(Vote.duel_id == duel.id, Vote.voter_type == "agent")
            .order_by(Vote.created_at.asc())
        ).scalars()
    )


def judgment_out_data(db: Session, duel: Duel, judgments: list[Vote]) -> list[dict]:
    infos = agent_info_lookup(db, [j.voter_agent_id for j in judgments])
    entries = db.execute(select(DuelEntry).where(DuelEntry.duel_id == duel.id)).scalars().all()
    winning_entry_id = (
        next((e.id for e in entries if e.agent_id == duel.winner_agent_id), None)
        if not duel.is_draw
        else None
    )
    out = []
    for j in judgments:
        info = infos.get(j.voter_agent_id)
        agreed_with_result = (
            None if duel.is_draw or winning_entry_id is None else j.chosen_entry_id == winning_entry_id
        )
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
                "created_at": j.created_at,
            }
        )
    return out
