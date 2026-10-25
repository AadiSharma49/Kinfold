from __future__ import annotations

import re

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from kinfold_api.constants import HANDLE_PATTERN
from kinfold_api.models import ApiKey, Owner
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
