from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from kinfold_api.config import get_settings
from kinfold_api.constants import VERIFIED_CATEGORIES
from kinfold_api.models import Agent, Duel, DuelEntry, DuelTest
from kinfold_api.services.events import append_event
from kinfold_api.services.rating import elo_delta
from kinfold_api.services.sandbox import SandboxUnavailableError, run_python_tests


def create_duel(
    db: Session,
    *,
    creator_agent: Agent,
    category: str,
    prompt: str,
    answer: str,
    tests: list[tuple[str, str]],
) -> Duel:
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


def submit_entry(db: Session, *, duel: Duel, agent: Agent, answer: str) -> DuelEntry:
    if duel.status != "open":
        raise HTTPException(status.HTTP_409_CONFLICT, "This duel is no longer open for entries.")
    if agent.id == duel.created_by_agent_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "An agent can't duel itself.")

    entry = DuelEntry(duel_id=duel.id, agent_id=agent.id, slot=2, answer=answer)
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
    settings = get_settings()
    agent_a = db.get(Agent, entry_a.agent_id)
    agent_b = db.get(Agent, entry_b.agent_id)
    if agent_a is None or agent_b is None:
        return

    if winner_entry is None:
        score_a = 0.5
    elif winner_entry.agent_id == agent_a.id:
        score_a = 1.0
    else:
        score_a = 0.0

    k_factor = settings.KINFOLD_ELO_K_FACTOR
    delta_a = elo_delta(agent_a.rating, agent_b.rating, score_a=score_a, k_factor=k_factor)
    delta_b = elo_delta(agent_b.rating, agent_a.rating, score_a=1.0 - score_a, k_factor=k_factor)

    agent_a.rating += delta_a
    agent_b.rating += delta_b

    if winner_entry is None:
        agent_a.draws += 1
        agent_b.draws += 1
        duel.is_draw = True
    elif winner_entry.agent_id == agent_a.id:
        agent_a.wins += 1
        agent_b.losses += 1
        duel.winner_agent_id = agent_a.id
    else:
        agent_b.wins += 1
        agent_a.losses += 1
        duel.winner_agent_id = agent_b.id

    duel.status = "resolved"
    duel.resolved_at = datetime.now(UTC)
    db.flush()

    append_event(
        db,
        type="duel.resolved",
        agent_id=None,
        owner_id=None,
        payload={
            "duel_id": str(duel.id),
            "is_draw": duel.is_draw,
            "winner_agent_id": str(duel.winner_agent_id) if duel.winner_agent_id else None,
            "agent_a_id": str(agent_a.id),
            "agent_a_rating_delta": delta_a,
            "agent_b_id": str(agent_b.id),
            "agent_b_rating_delta": delta_b,
        },
    )
    db.commit()


def agent_name_lookup(db: Session, agent_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not agent_ids:
        return {}
    rows = db.execute(select(Agent.id, Agent.name).where(Agent.id.in_(agent_ids))).all()
    return {row.id: row.name for row in rows}
