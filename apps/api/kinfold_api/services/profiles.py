from __future__ import annotations

import uuid
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from kinfold_api.models import Agent, Duel, DuelEntry, Owner
from kinfold_api.services.duels import agent_info_lookup, owner_handle_lookup, winning_entry_id


class CategoryRecord(NamedTuple):
    wins: int
    losses: int
    draws: int


def _result_for(duel: Duel, own_entry: DuelEntry, entries: list[DuelEntry]) -> str:
    winner_id = winning_entry_id(duel, entries)
    if winner_id is None:
        return "draw"
    return "win" if own_entry.id == winner_id else "loss"


def agent_category_record(db: Session, agent_id: uuid.UUID) -> dict[str, CategoryRecord]:
    """Real win/loss/draw counts per category, computed from actual
    resolved duels — not a separate Elo per category, which Kinfold
    doesn't track. See docs/questions-for-owner.md, 2026-10-31."""
    rows = db.execute(
        select(Duel, DuelEntry)
        .join(DuelEntry, DuelEntry.duel_id == Duel.id)
        .where(DuelEntry.agent_id == agent_id, Duel.status == "resolved")
    ).all()

    record: dict[str, list[int]] = {}
    for duel, entry in rows:
        entries = db.execute(
            select(DuelEntry).where(DuelEntry.duel_id == duel.id)
        ).scalars().all()
        result = _result_for(duel, entry, entries)
        bucket = record.setdefault(duel.category, [0, 0, 0])
        bucket[{"win": 0, "loss": 1, "draw": 2}[result]] += 1

    return {category: CategoryRecord(*counts) for category, counts in record.items()}


def agent_duel_history(db: Session, agent_id: uuid.UUID, limit: int = 20) -> list[dict]:
    entries = db.execute(
        select(DuelEntry)
        .join(Duel, Duel.id == DuelEntry.duel_id)
        .where(DuelEntry.agent_id == agent_id, Duel.status == "resolved")
        .order_by(Duel.resolved_at.desc())
        .limit(limit)
    ).scalars().all()

    out = []
    for entry in entries:
        duel = db.get(Duel, entry.duel_id)
        all_entries = db.execute(
            select(DuelEntry).where(DuelEntry.duel_id == duel.id)
        ).scalars().all()
        opponent_entry = next((e for e in all_entries if e.id != entry.id), None)

        opponent_name = None
        opponent_is_house = None
        opponent_human_handle = None
        if opponent_entry is not None:
            if opponent_entry.agent_id:
                info = agent_info_lookup(db, [opponent_entry.agent_id]).get(opponent_entry.agent_id)
                if info:
                    opponent_name = info.name
                    opponent_is_house = info.is_house
            elif opponent_entry.human_owner_id:
                opponent_human_handle = owner_handle_lookup(
                    db, [opponent_entry.human_owner_id]
                ).get(opponent_entry.human_owner_id)

        out.append(
            {
                "duel_id": duel.id,
                "category": duel.category,
                "prompt": duel.prompt,
                "resolved_at": duel.resolved_at,
                "result": _result_for(duel, entry, all_entries),
                "passed_tests": entry.passed_tests,
                "total_tests": entry.total_tests,
                "opponent_agent_name": opponent_name,
                "opponent_agent_is_house": opponent_is_house,
                "opponent_human_owner_handle": opponent_human_handle,
            }
        )
    return out


def human_duel_history(db: Session, owner_id: uuid.UUID, limit: int = 20) -> list[dict]:
    entries = db.execute(
        select(DuelEntry)
        .join(Duel, Duel.id == DuelEntry.duel_id)
        .where(DuelEntry.human_owner_id == owner_id, Duel.status == "resolved")
        .order_by(Duel.resolved_at.desc())
        .limit(limit)
    ).scalars().all()

    out = []
    for entry in entries:
        duel = db.get(Duel, entry.duel_id)
        all_entries = db.execute(
            select(DuelEntry).where(DuelEntry.duel_id == duel.id)
        ).scalars().all()
        opponent_entry = next((e for e in all_entries if e.id != entry.id), None)
        opponent_name = None
        opponent_is_house = None
        if opponent_entry is not None and opponent_entry.agent_id:
            info = agent_info_lookup(db, [opponent_entry.agent_id]).get(opponent_entry.agent_id)
            if info:
                opponent_name = info.name
                opponent_is_house = info.is_house

        out.append(
            {
                "duel_id": duel.id,
                "category": duel.category,
                "prompt": duel.prompt,
                "resolved_at": duel.resolved_at,
                "result": _result_for(duel, entry, all_entries),
                "time_taken_seconds": entry.human_time_taken_seconds,
                "declared_ai_tools": entry.human_declared_ai_tools,
                "opponent_agent_name": opponent_name,
                "opponent_agent_is_house": opponent_is_house,
            }
        )
    return out


def owner_has_any_agent_or_human_activity(db: Session, owner: Owner) -> bool:
    """Used to decide whether a handle resolves to a public profile at
    all — an owner who has never entered a duel as a human and owns no
    agents has nothing public to show."""
    has_agent = db.execute(select(Agent.id).where(Agent.owner_id == owner.id).limit(1)).first()
    has_entry = db.execute(
        select(DuelEntry.id).where(DuelEntry.human_owner_id == owner.id).limit(1)
    ).first()
    return has_agent is not None or has_entry is not None


