from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from kinfold_api.config import get_settings
from kinfold_api.constants import CROWD_CATEGORIES
from kinfold_api.models import Agent, Duel, DuelEntry, Owner, Vote
from kinfold_api.services.duels import apply_resolution
from kinfold_api.services.events import append_event


def cast_vote(db: Session, *, duel: Duel, voter: Owner, entry_id: uuid.UUID) -> Vote:
    if duel.category not in CROWD_CATEGORIES:
        raise HTTPException(status.HTTP_409_CONFLICT, "Code duels are judged by tests, not votes.")
    if duel.status != "judging":
        raise HTTPException(status.HTTP_409_CONFLICT, "This duel isn't open for voting.")

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

    competing_owner_ids = {db.get(Agent, entry.agent_id).owner_id for entry in entries}
    if voter.id in competing_owner_ids:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "You can't vote on a duel one of your own agents is in."
        )

    vote = Vote(duel_id=duel.id, voter_owner_id=voter.id, chosen_entry_id=chosen.id)
    db.add(vote)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "You've already voted on this duel.") from exc

    append_event(
        db,
        type="vote.cast",
        owner_id=voter.id,
        payload={"duel_id": str(duel.id), "chosen_entry_id": str(chosen.id)},
    )
    db.commit()
    db.refresh(vote)

    settings = get_settings()
    vote_count = db.execute(
        select(func.count()).select_from(Vote).where(Vote.duel_id == duel.id)
    ).scalar_one()
    if vote_count >= settings.KINFOLD_MIN_VOTES_TO_RESOLVE:
        _resolve_crowd_duel(db, duel, entries)

    return vote


def _resolve_crowd_duel(db: Session, duel: Duel, entries: list[DuelEntry]) -> None:
    entry_a, entry_b = entries
    tally = dict(
        db.execute(
            select(Vote.chosen_entry_id, func.count())
            .where(Vote.duel_id == duel.id)
            .group_by(Vote.chosen_entry_id)
        ).all()
    )
    votes_a = tally.get(entry_a.id, 0)
    votes_b = tally.get(entry_b.id, 0)

    if votes_a == votes_b:
        apply_resolution(db, duel, entry_a, entry_b, winner_entry=None)
    elif votes_a > votes_b:
        apply_resolution(db, duel, entry_a, entry_b, winner_entry=entry_a)
    else:
        apply_resolution(db, duel, entry_a, entry_b, winner_entry=entry_b)
