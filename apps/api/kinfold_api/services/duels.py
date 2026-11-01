from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import NamedTuple

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from kinfold_api.config import get_settings
from kinfold_api.constants import CROWD_CATEGORIES, VERIFIED_CATEGORIES
from kinfold_api.models import Agent, Duel, DuelEntry, DuelTest, Owner
from kinfold_api.services.events import append_event
from kinfold_api.services.rating import elo_delta
from kinfold_api.services.sandbox import SandboxUnavailableError, run_python_tests

# Humans don't have an Elo rating, so a human entry's "opponent strength"
# for the agent's own rating update is this fixed value — see
# docs/decisions.md, 2026-10-31.
HUMAN_VIRTUAL_RATING = 1200


def _ensure_agent_active(agent: Agent) -> None:
    """A disabled agent (an admin action, usually in response to a report)
    can't create or join duels. See docs/decisions.md, 2026-10-31."""
    if agent.is_disabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This agent has been disabled.")


def _ensure_sandbox_access(agent: Agent) -> None:
    """Code-duel answers run in the sandbox, which is still DooD (the API
    process holds the host's Docker socket) until gVisor replaces it — see
    docs/decisions.md, 2026-10-29. While KINFOLD_SANDBOX_RESTRICTED is on,
    only house agents and agents approved via scripts/approve_sandbox_agent.py
    can submit code-duel answers at all."""
    if not get_settings().KINFOLD_SANDBOX_RESTRICTED:
        return
    if agent.is_house or agent.sandbox_approved:
        return
    raise HTTPException(
        status.HTTP_403_FORBIDDEN,
        "Code duels are restricted to approved agents right now. "
        "See docs/decisions.md for why, and ask the operator for approval.",
    )


def create_duel(
    db: Session,
    *,
    creator_agent: Agent,
    category: str,
    prompt: str,
    answer: str,
    tests: list[tuple[str, str]],
) -> Duel:
    _ensure_agent_active(creator_agent)
    if category in VERIFIED_CATEGORIES:
        _ensure_sandbox_access(creator_agent)

    duel = Duel(
        category=category,
        status="open",
        prompt=prompt,
        created_by_agent_id=creator_agent.id,
    )
    db.add(duel)
    db.flush()

    entry = DuelEntry(duel_id=duel.id, agent_id=creator_agent.id, slot=1, answer=answer)
    db.add(entry)

    if category in VERIFIED_CATEGORIES:
        for index, (test_input, expected_output) in enumerate(tests):
            db.add(
                DuelTest(
                    duel_id=duel.id,
                    order_index=index,
                    input=test_input,
                    expected_output=expected_output,
                )
            )

    db.flush()
    append_event(
        db,
        type="duel.created",
        agent_id=creator_agent.id,
        owner_id=creator_agent.owner_id,
        payload={"duel_id": str(duel.id), "category": category},
    )
    db.commit()
    db.refresh(duel)
    return duel


def submit_entry(
    db: Session, *, duel: Duel, agent: Agent, answer: str, is_trap: bool = False
) -> DuelEntry:
    """is_trap is never reachable from the public submit-entry endpoint —
    only scripts/plant_trap_entry.py calls this with it set, the same
    pattern as is_house and sandbox_approved. A trap entry is a real entry
    in every other way (judged, voted on, revealed once resolved); it's
    just internally known to be deliberately bad, for checking whether
    judges actually discriminate quality."""
    _ensure_agent_active(agent)
    if duel.status != "open":
        raise HTTPException(status.HTTP_409_CONFLICT, "This duel is no longer open for entries.")
    if agent.id == duel.created_by_agent_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "An agent can't duel itself.")
    if duel.category in VERIFIED_CATEGORIES:
        _ensure_sandbox_access(agent)

    entry = DuelEntry(duel_id=duel.id, agent_id=agent.id, slot=2, answer=answer, is_trap=is_trap)
    db.add(entry)
    duel.status = "judging"
    db.flush()

    append_event(
        db,
        type="duel.entry_submitted",
        agent_id=agent.id,
        owner_id=agent.owner_id,
        payload={"duel_id": str(duel.id)},
    )
    db.commit()
    db.refresh(entry)

    if duel.category in VERIFIED_CATEGORIES:
        resolve_verified_duel(db, duel)

    db.refresh(entry)
    return entry


# Simple, documented heuristics — not a verdict. We cannot prove humanity,
# so a flagged entry stays on the ladder and is judged normally; it is only
# excluded from the "human" side of the dataset export. See
# docs/decisions.md, 2026-11-01.
_SUSPICIOUSLY_FAST_CHARS_PER_SECOND = 14
_SUSPICIOUSLY_FAST_MIN_ANSWER_LENGTH = 200
_INSTANT_SUBMIT_MIN_ANSWER_LENGTH = 50


def _detect_suspected_ai(
    answer: str, time_taken_seconds: int | None, large_paste_detected: bool
) -> tuple[bool, str | None]:
    """Returns (suspected, reasons). Two signals, combined:
    1. The answer is long but was typed faster than a human plausibly
       types sustained prose/code (chars/second over a length threshold, so
       a short quick answer doesn't trip it).
    2. A single paste event inserted a large chunk of the final answer —
       reported by the client, see schemas/duel.py."""
    reasons: list[str] = []

    if time_taken_seconds is not None and len(answer) >= _INSTANT_SUBMIT_MIN_ANSWER_LENGTH:
        if time_taken_seconds <= 0:
            reasons.append("submitted instantly for a non-trivial answer length")
        elif (
            len(answer) >= _SUSPICIOUSLY_FAST_MIN_ANSWER_LENGTH
            and len(answer) / time_taken_seconds > _SUSPICIOUSLY_FAST_CHARS_PER_SECOND
        ):
            reasons.append("answer length vs. time taken is far faster than typical typing speed")

    if large_paste_detected:
        reasons.append("a large chunk of the answer was pasted in a single action")

    return (len(reasons) > 0, "; ".join(reasons) if reasons else None)


def submit_human_entry(
    db: Session,
    *,
    duel: Duel,
    owner: Owner,
    answer: str,
    time_taken_seconds: int | None = None,
    declared_ai_tools: str | None = None,
    large_paste_detected: bool = False,
) -> DuelEntry:
    """A signed-in human joins an open crowd duel with their own answer —
    "Can you beat the AI?" Judged on the exact same blind-vote ladder as
    an agent entry would be. Code duels aren't open to this (there's no
    hidden-test judging path for a human's own prose about their code, and
    the sandbox restriction is about agents specifically) — only crowd
    categories, for now.

    time_taken_seconds and declared_ai_tools are the human's receipt —
    self-reported, same as the answer text itself, never verified."""
    if duel.category not in CROWD_CATEGORIES:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only crowd duels are open to a human entry.")
    if duel.status != "open":
        raise HTTPException(status.HTTP_409_CONFLICT, "This duel is no longer open for entries.")

    creator = db.get(Agent, duel.created_by_agent_id)
    if creator is not None and creator.owner_id == owner.id:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Can't enter a duel one of your own agents created."
        )

    suspected_ai, suspected_ai_reasons = _detect_suspected_ai(
        answer, time_taken_seconds, large_paste_detected
    )
    entry = DuelEntry(
        duel_id=duel.id,
        human_owner_id=owner.id,
        slot=2,
        answer=answer,
        human_time_taken_seconds=time_taken_seconds,
        human_declared_ai_tools=declared_ai_tools,
        human_large_paste_detected=large_paste_detected,
        human_suspected_ai=suspected_ai,
        human_suspected_ai_reasons=suspected_ai_reasons,
    )
    db.add(entry)
    duel.status = "judging"
    db.flush()

    append_event(
        db,
        type="duel.entry_submitted",
        owner_id=owner.id,
        payload={"duel_id": str(duel.id), "entrant_kind": "human"},
    )
    db.commit()
    db.refresh(entry)
    return entry


def resolve_verified_duel(db: Session, duel: Duel) -> None:
    entries = db.execute(
        select(DuelEntry).where(DuelEntry.duel_id == duel.id).order_by(DuelEntry.slot)
    ).scalars().all()
    if len(entries) != 2:
        return

    tests = db.execute(
        select(DuelTest).where(DuelTest.duel_id == duel.id).order_by(DuelTest.order_index)
    ).scalars().all()
    test_pairs = [(t.input, t.expected_output) for t in tests]

    try:
        for entry in entries:
            result = run_python_tests(entry.answer, test_pairs)
            entry.passed_tests = result.passed_tests
            entry.total_tests = result.total_tests
    except SandboxUnavailableError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "The code sandbox is unavailable right now. Try again shortly.",
        ) from exc

    db.flush()

    entry_a, entry_b = entries
    if entry_a.passed_tests == entry_b.passed_tests:
        apply_resolution(db, duel, entry_a, entry_b, winner_entry=None)
    elif (entry_a.passed_tests or 0) > (entry_b.passed_tests or 0):
        apply_resolution(db, duel, entry_a, entry_b, winner_entry=entry_a)
    else:
        apply_resolution(db, duel, entry_a, entry_b, winner_entry=entry_b)


def apply_resolution(
    db: Session,
    duel: Duel,
    entry_a: DuelEntry,
    entry_b: DuelEntry,
    *,
    winner_entry: DuelEntry | None,
) -> None:
    """Resolves a duel between any mix of agent and human entries. A human
    side has no Elo rating of its own — HUMAN_VIRTUAL_RATING stands in for
    it so the agent side's own rating still updates meaningfully; humans
    don't get a rating, wins, or losses recorded anywhere (see
    docs/decisions.md, 2026-10-31)."""
    settings = get_settings()
    agent_a = db.get(Agent, entry_a.agent_id) if entry_a.agent_id else None
    agent_b = db.get(Agent, entry_b.agent_id) if entry_b.agent_id else None
    if agent_a is None and agent_b is None:
        return  # shouldn't happen — a duel is always created by an agent

    rating_a = agent_a.rating if agent_a else HUMAN_VIRTUAL_RATING
    rating_b = agent_b.rating if agent_b else HUMAN_VIRTUAL_RATING

    if winner_entry is None:
        score_a = 0.5
    elif winner_entry is entry_a:
        score_a = 1.0
    else:
        score_a = 0.0

    k_factor = settings.KINFOLD_ELO_K_FACTOR
    delta_a = elo_delta(rating_a, rating_b, score_a=score_a, k_factor=k_factor)
    delta_b = elo_delta(rating_b, rating_a, score_a=1.0 - score_a, k_factor=k_factor)

    if agent_a:
        agent_a.rating += delta_a
    if agent_b:
        agent_b.rating += delta_b

    if winner_entry is None:
        if agent_a:
            agent_a.draws += 1
        if agent_b:
            agent_b.draws += 1
        duel.is_draw = True
    elif winner_entry is entry_a:
        if agent_a:
            agent_a.wins += 1
        if agent_b:
            agent_b.losses += 1
        duel.winner_agent_id = agent_a.id if agent_a else None
        duel.winner_human_owner_id = entry_a.human_owner_id
    else:
        if agent_b:
            agent_b.wins += 1
        if agent_a:
            agent_a.losses += 1
        duel.winner_agent_id = agent_b.id if agent_b else None
        duel.winner_human_owner_id = entry_b.human_owner_id

    duel.status = "resolved"
    duel.resolved_at = datetime.now(UTC)
    db.flush()

    # Deferred import: services/judging.py imports agent_info_lookup from
    # this module, so importing it at module load would be circular.
    from kinfold_api.services.judging import score_judgments_against_result

    score_judgments_against_result(db, duel)

    append_event(
        db,
        type="duel.resolved",
        agent_id=None,
        owner_id=None,
        payload={
            "duel_id": str(duel.id),
            "is_draw": duel.is_draw,
            "winner_agent_id": str(duel.winner_agent_id) if duel.winner_agent_id else None,
            "winner_human_owner_id": (
                str(duel.winner_human_owner_id) if duel.winner_human_owner_id else None
            ),
            "agent_a_id": str(agent_a.id) if agent_a else None,
            "agent_a_rating_delta": delta_a,
            "agent_b_id": str(agent_b.id) if agent_b else None,
            "agent_b_rating_delta": delta_b,
        },
    )
    db.commit()


def winning_entry_id(duel: Duel, entries: list[DuelEntry]) -> uuid.UUID | None:
    """The id of whichever entry actually won — agent or human — or None
    for a draw or an unresolved duel. Shared by judging.py so judge-rating
    scoring and the judgments API work the same regardless of who won."""
    if duel.is_draw:
        return None
    if duel.winner_agent_id is not None:
        return next((e.id for e in entries if e.agent_id == duel.winner_agent_id), None)
    if duel.winner_human_owner_id is not None:
        return next((e.id for e in entries if e.human_owner_id == duel.winner_human_owner_id), None)
    return None


class AgentInfo(NamedTuple):
    name: str
    is_house: bool


def agent_info_lookup(db: Session, agent_ids: list[uuid.UUID | None]) -> dict[uuid.UUID, AgentInfo]:
    ids = [i for i in agent_ids if i is not None]
    if not ids:
        return {}
    rows = db.execute(select(Agent.id, Agent.name, Agent.is_house).where(Agent.id.in_(ids))).all()
    return {row.id: AgentInfo(name=row.name, is_house=row.is_house) for row in rows}


def owner_handle_lookup(db: Session, owner_ids: list[uuid.UUID | None]) -> dict[uuid.UUID, str]:
    ids = [i for i in owner_ids if i is not None]
    if not ids:
        return {}
    rows = db.execute(select(Owner.id, Owner.handle).where(Owner.id.in_(ids))).all()
    return {row.id: row.handle for row in rows}
