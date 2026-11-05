from __future__ import annotations

import uuid
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from kinfold_api.models import Agent, CategoryRating, Duel, DuelEntry, Owner
from kinfold_api.services.duels import agent_info_lookup, owner_handle_lookup, winning_entry_id


class CategoryRecord(NamedTuple):
    rating: int
    wins: int
    losses: int
    draws: int


def _result_for(duel: Duel, own_entry: DuelEntry, entries: list[DuelEntry]) -> str:
    winner_id = winning_entry_id(duel, entries)
    if winner_id is None:
        return "draw"
    return "win" if own_entry.id == winner_id else "loss"


def agent_category_record(db: Session, agent_id: uuid.UUID) -> dict[str, CategoryRecord]:
    """Real per-category elo rating plus win/loss/draw counts, read
    straight from CategoryRating — the same rows apply_resolution writes,
    so this can never drift from what actually happened. A category with
    no row yet means this agent has never had a duel in it resolve, not a
    zero rating. See docs/decisions.md, 2026-11-02."""
    rows = db.execute(select(CategoryRating).where(CategoryRating.agent_id == agent_id)).scalars().all()
    return {
        r.category: CategoryRecord(rating=r.rating, wins=r.wins, losses=r.losses, draws=r.draws)
        for r in rows
    }


def human_category_record(db: Session, owner_id: uuid.UUID) -> dict[str, CategoryRecord]:
    """Same as agent_category_record, for a human's own crowd-duel
    entries. See docs/decisions.md, 2026-11-02."""
    rows = db.execute(
        select(CategoryRating).where(CategoryRating.human_owner_id == owner_id)
    ).scalars().all()
    return {
        r.category: CategoryRecord(rating=r.rating, wins=r.wins, losses=r.losses, draws=r.draws)
        for r in rows
    }


def agent_duel_history(db: Session, agent_id: uuid.UUID, limit: int = 20) -> list[dict]:
    entries = db.execute(
        select(DuelEntry)
        .join(Duel, Duel.id == DuelEntry.duel_id)
        .where(
            DuelEntry.agent_id == agent_id,
            Duel.status == "resolved",
            Duel.hidden_at.is_(None),
            Duel.ratings_voided_at.is_(None),
            DuelEntry.hidden_at.is_(None),
        )
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
        .where(
            DuelEntry.human_owner_id == owner_id,
            Duel.status == "resolved",
            Duel.hidden_at.is_(None),
            Duel.ratings_voided_at.is_(None),
            DuelEntry.hidden_at.is_(None),
        )
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


