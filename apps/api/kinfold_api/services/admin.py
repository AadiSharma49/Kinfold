from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from kinfold_api.models import Agent, ApiKey, Duel, DuelEntry, Vote
from kinfold_api.services.duels import void_duel_ratings
from kinfold_api.services.events import append_event
from kinfold_api.services.keys import revoke_key

# Every function here is an admin action — each writes its own event,
# separate from (and in addition to) whatever event the underlying change
# would normally produce, so "an admin did this" is always distinguishable
# from "this happened in the ordinary course of the product." See
# docs/decisions.md, 2026-10-31.


def hide_duel(db: Session, *, duel: Duel, admin_owner_id: uuid.UUID) -> Duel:
    if duel.hidden_at is None:
        duel.hidden_at = datetime.now(UTC)
        db.flush()
        append_event(
            db,
            type="admin.duel_hidden",
            owner_id=admin_owner_id,
            payload={"duel_id": str(duel.id)},
        )
        db.commit()
        db.refresh(duel)
    return duel


def hide_entry(db: Session, *, entry: DuelEntry, admin_owner_id: uuid.UUID) -> DuelEntry:
    if entry.hidden_at is None:
        entry.hidden_at = datetime.now(UTC)
        db.flush()
        duel = db.get(Duel, entry.duel_id)
        if duel is not None:
            # A resolved duel's ratings must not keep depending on content
            # a moderator has removed. Reverses both sides exactly and
            # marks the duel voided for profiles/export.
            void_duel_ratings(db, duel=duel)
        append_event(
            db,
            type="admin.entry_hidden",
            owner_id=admin_owner_id,
            payload={"entry_id": str(entry.id), "duel_id": str(entry.duel_id)},
        )
        db.commit()
        db.refresh(entry)
    return entry


def hide_judgment(db: Session, *, judgment: Vote, admin_owner_id: uuid.UUID) -> Vote:
    if judgment.hidden_at is None:
        judgment.hidden_at = datetime.now(UTC)
        db.flush()
        append_event(
            db,
            type="admin.judgment_hidden",
            owner_id=admin_owner_id,
            payload={"judgment_id": str(judgment.id), "duel_id": str(judgment.duel_id)},
        )
        db.commit()
        db.refresh(judgment)
    return judgment


def disable_agent(db: Session, *, agent: Agent, admin_owner_id: uuid.UUID) -> Agent:
    if not agent.is_disabled:
        agent.is_disabled = True
        db.flush()
        append_event(
            db,
            type="admin.agent_disabled",
            owner_id=admin_owner_id,
            agent_id=agent.id,
            payload={"agent_name": agent.name},
        )
        db.commit()
        db.refresh(agent)
    return agent


def approve_agent_sandbox(db: Session, *, agent: Agent, admin_owner_id: uuid.UUID) -> Agent:
    """API equivalent of scripts/approve_sandbox_agent.py, for an admin
    acting through the product rather than a shell on the server."""
    if not agent.sandbox_approved:
        agent.sandbox_approved = True
        db.flush()
        append_event(
            db,
            type="admin.agent_sandbox_approved",
            owner_id=admin_owner_id,
            agent_id=agent.id,
            payload={"agent_name": agent.name},
        )
        db.commit()
        db.refresh(agent)
    return agent


def admin_revoke_key(db: Session, *, api_key: ApiKey, admin_owner_id: uuid.UUID) -> ApiKey:
    """Revokes any key, regardless of whose it is — revoke_key() itself
    logs the ordinary key.revoked event; this adds a second, admin-
    attributed event so the override is never indistinguishable from a
    self-revoke."""
    revoked = revoke_key(db, api_key=api_key)
    append_event(
        db,
        type="admin.key_revoked",
        owner_id=admin_owner_id,
        payload={"key_id": str(api_key.id), "key_owner_id": str(api_key.owner_id)},
    )
    db.commit()
    return revoked
