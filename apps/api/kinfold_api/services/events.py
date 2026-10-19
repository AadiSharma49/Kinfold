from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from kinfold_api.constants import GENESIS_PREV_HASH
from kinfold_api.models import Event


def _canonical_payload(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def compute_hash(
    *,
    prev_hash: str,
    seq: int,
    type_: str,
    agent_id: uuid.UUID | None,
    owner_id: uuid.UUID | None,
    payload: dict,
    created_at: datetime,
) -> str:
    raw = (
        f"{prev_hash}{seq}{type_}{agent_id or ''}{owner_id or ''}"
        f"{_canonical_payload(payload)}{created_at.isoformat()}"
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def append_event(
    db: Session,
    *,
    type: str,
    agent_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None,
    payload: dict,
) -> Event:
    """Append one event to the chain, in the caller's existing transaction.

    Never pass a raw key or key hash in `payload`.
    """
    last = db.execute(
        select(Event).order_by(Event.seq.desc()).limit(1).with_for_update()
    ).scalar_one_or_none()

    seq = (last.seq + 1) if last else 1
    prev_hash = last.hash if last else GENESIS_PREV_HASH
    created_at = datetime.now(UTC)

    hash_ = compute_hash(
        prev_hash=prev_hash,
        seq=seq,
        type_=type,
        agent_id=agent_id,
        owner_id=owner_id,
        payload=payload,
        created_at=created_at,
    )

    event = Event(
        seq=seq,
        type=type,
        agent_id=agent_id,
        owner_id=owner_id,
        payload=payload,
        source="server",
        created_at=created_at,
        prev_hash=prev_hash,
        hash=hash_,
    )
    db.add(event)
    db.flush()
    return event


def verify_chain(db: Session) -> tuple[bool, int | None]:
    """Walk the whole chain. Returns (ok, first_broken_seq)."""
    events = db.execute(select(Event).order_by(Event.seq.asc())).scalars().all()

    expected_prev_hash = GENESIS_PREV_HASH
    for event in events:
        if event.prev_hash != expected_prev_hash:
            return False, event.seq

        recomputed = compute_hash(
            prev_hash=event.prev_hash,
            seq=event.seq,
            type_=event.type,
            agent_id=event.agent_id,
            owner_id=event.owner_id,
            payload=event.payload,
            created_at=event.created_at,
        )
        if recomputed != event.hash:
            return False, event.seq

        expected_prev_hash = event.hash

    return True, None
