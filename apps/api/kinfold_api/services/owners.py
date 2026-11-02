from __future__ import annotations

import re
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from kinfold_api.constants import HANDLE_PATTERN
from kinfold_api.models import Agent, ApiKey, Owner
from kinfold_api.services.events import append_event
from kinfold_api.services.keys import create_owner_key

_HANDLE_RE = re.compile(HANDLE_PATTERN)


def create_owner_with_key(db: Session, *, handle: str) -> tuple[Owner, ApiKey, str]:
    handle = handle.lower()
    if not _HANDLE_RE.match(handle):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Handle must be 3-40 characters: lowercase letters, numbers, _ or -.",
        )

    existing = db.execute(select(Owner).where(Owner.handle == handle)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "That handle is already taken.")

    owner = Owner(handle=handle)
    db.add(owner)
    db.flush()

    append_event(db, type="owner.created", owner_id=owner.id, payload={"handle": owner.handle})

    api_key, raw_key = create_owner_key(db, owner_id=owner.id, label="first key")
    append_event(
        db,
        type="key.created",
        owner_id=owner.id,
        payload={"key_id": str(api_key.id), "kind": "owner", "prefix": api_key.prefix},
    )

    db.commit()
    db.refresh(owner)
    db.refresh(api_key)
    return owner, api_key, raw_key


def request_account_deletion(db: Session, owner: Owner) -> Owner:
    """Self-service "right to erasure" request — see docs/decisions.md,
    2026-11-02, and the privacy page. Anonymizes identity (handle,
    github_id), disables every agent this owner runs, and revokes every
    key tied to this owner (their own and all of their agents') so the
    account can't be used again. Does NOT delete duel content or event
    log entries: those are the historical arena record other people's
    results depend on, and the event log is append-only by design — full
    erasure of public duel content isn't possible without destroying
    that record, an honest limitation stated on the privacy page."""
    if owner.deleted_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This account is already deleted.")

    now = datetime.now(UTC)
    owner.deleted_at = now
    owner.handle = f"deleted-{owner.id.hex[:16]}"
    owner.github_id = None

    agents = db.execute(select(Agent).where(Agent.owner_id == owner.id)).scalars().all()
    for agent in agents:
        agent.is_disabled = True

    keys = db.execute(
        select(ApiKey).where(ApiKey.owner_id == owner.id, ApiKey.revoked_at.is_(None))
    ).scalars().all()
    for key in keys:
        key.revoked_at = now

    append_event(db, type="owner.deletion_requested", owner_id=owner.id, payload={})
    db.commit()
    db.refresh(owner)
    return owner
