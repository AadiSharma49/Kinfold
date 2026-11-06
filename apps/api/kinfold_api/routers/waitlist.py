from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from kinfold_api.db import get_db
from kinfold_api.models import WaitlistEntry
from kinfold_api.schemas.waitlist import WaitlistCreateRequest, WaitlistResponse

router = APIRouter(tags=["waitlist"])

DUPLICATE_MESSAGE = "You're already on the list."


@router.post("/waitlist", response_model=WaitlistResponse)
def join_waitlist(
    body: WaitlistCreateRequest,
    db: Session = Depends(get_db),
) -> WaitlistResponse:
    """Public signup. No key is needed, so the request IP rate limit in
    the request middleware is the only gate before validation."""
    if body.company:
        return WaitlistResponse(status="ok")

    existing = db.scalar(select(WaitlistEntry.id).where(WaitlistEntry.email == body.email))
    if existing is not None:
        return WaitlistResponse(status="duplicate", message=DUPLICATE_MESSAGE)

    db.add(WaitlistEntry(email=body.email, role=body.role.value, bring=body.bring))
    try:
        db.commit()
    except IntegrityError:
        # Two simultaneous signups can both pass the lookup above; the
        # unique index on email decides, and the loser is still a success
        # from the visitor's point of view.
        db.rollback()
        return WaitlistResponse(status="duplicate", message=DUPLICATE_MESSAGE)

    return WaitlistResponse(status="ok")
