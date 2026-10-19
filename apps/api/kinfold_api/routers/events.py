from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from kinfold_api.db import get_db
from kinfold_api.schemas.event import EventVerifyOut
from kinfold_api.services.events import verify_chain

router = APIRouter(tags=["events"])


@router.get("/events/verify", response_model=EventVerifyOut)
def verify_events(db: Session = Depends(get_db)) -> EventVerifyOut:
    """Walk the whole chain and confirm every hash.

    Public, on purpose: it never returns event payloads, only whether the
    chain is intact and, if not, which seq broke. That lets anyone confirm
    the log hasn't been tampered with, without needing an account, in
    keeping with the "receipts on everything" principle.
    """
    ok, broken_at_seq = verify_chain(db)
    return EventVerifyOut(ok=ok, broken_at_seq=broken_at_seq)
