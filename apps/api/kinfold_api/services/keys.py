from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from kinfold_api.models import ApiKey
from kinfold_api.security import display_prefix, generate_agent_key, generate_owner_key, hash_key
from kinfold_api.services.events import append_event


def create_owner_key(db: Session, *, owner_id: uuid.UUID, label: str | None = None) -> tuple[ApiKey, str]:
    raw_key = generate_owner_key()
    api_key = ApiKey(
        kind="owner",
        owner_id=owner_id,
        agent_id=None,
        prefix=display_prefix(raw_key),
        key_hash=hash_key(raw_key),
        label=label,
    )
    db.add(api_key)
    db.flush()
    return api_key, raw_key


def issue_additional_owner_key(
    db: Session, *, owner_id: uuid.UUID, label: str | None = None
) -> tuple[ApiKey, str]:
    api_key, raw_key = create_owner_key(db, owner_id=owner_id, label=label)
    append_event(
        db,
        type="key.created",
        owner_id=owner_id,
        payload={"key_id": str(api_key.id), "kind": "owner", "prefix": api_key.prefix},
    )
    db.commit()
    db.refresh(api_key)
    return api_key, raw_key


def issue_additional_agent_key(
    db: Session, *, owner_id: uuid.UUID, agent_id: uuid.UUID, label: str | None = None
) -> tuple[ApiKey, str]:
    api_key, raw_key = create_agent_key(db, owner_id=owner_id, agent_id=agent_id, label=label)
    append_event(
        db,
        type="key.created",
        agent_id=agent_id,
        owner_id=owner_id,
        payload={"key_id": str(api_key.id), "kind": "agent", "prefix": api_key.prefix},
    )
    db.commit()
    db.refresh(api_key)
    return api_key, raw_key


def revoke_key(db: Session, *, api_key: ApiKey) -> ApiKey:
    """Idempotent: revoking an already-revoked key is a no-op (no duplicate event)."""
    if api_key.revoked_at is None:
        api_key.revoked_at = datetime.now(UTC)
        db.flush()
        append_event(
            db,
            type="key.revoked",
            owner_id=api_key.owner_id,
            agent_id=api_key.agent_id,
            payload={"key_id": str(api_key.id)},
        )
        db.commit()
        db.refresh(api_key)
    return api_key


def create_agent_key(
    db: Session, *, owner_id: uuid.UUID, agent_id: uuid.UUID, label: str | None = None
) -> tuple[ApiKey, str]:
    raw_key = generate_agent_key()
    api_key = ApiKey(
        kind="agent",
        owner_id=owner_id,
        agent_id=agent_id,
        prefix=display_prefix(raw_key),
        key_hash=hash_key(raw_key),
        label=label,
    )
    db.add(api_key)
    db.flush()
    return api_key, raw_key
