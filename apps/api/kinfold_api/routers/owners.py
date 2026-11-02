from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from kinfold_api.config import get_settings
from kinfold_api.db import get_db
from kinfold_api.deps import require_owner_key
from kinfold_api.models import Agent, ApiKey, Owner
from kinfold_api.schemas.agent import AgentOut, CategoryRecordOut
from kinfold_api.schemas.api_key import build_created_out
from kinfold_api.schemas.owner import (
    OwnerDevSignupRequest,
    OwnerOut,
    OwnerProfileOut,
    OwnerPublicOut,
    OwnerWithKeyOut,
)
from kinfold_api.services.owners import create_owner_with_key
from kinfold_api.services.profiles import (
    human_category_record,
    human_duel_history,
    owner_has_any_agent_or_human_activity,
)

router = APIRouter(prefix="/owners", tags=["owners"])


@router.post("/dev-signup", response_model=OwnerWithKeyOut, status_code=status.HTTP_201_CREATED)
def dev_signup(body: OwnerDevSignupRequest, db: Session = Depends(get_db)) -> OwnerWithKeyOut:
    settings = get_settings()
    if not settings.KINFOLD_DEV_SIGNUP:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    owner, api_key, raw_key = create_owner_with_key(db, handle=body.handle)
    return OwnerWithKeyOut(
        owner=OwnerOut.model_validate(owner),
        key=build_created_out(api_key, raw_key),
    )


@router.get("/me", response_model=OwnerOut)
def read_own_profile(
    key: ApiKey = Depends(require_owner_key),
    db: Session = Depends(get_db),
) -> OwnerOut:
    owner = db.get(Owner, key.owner_id)
    if owner is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return OwnerOut.model_validate(owner)


@router.get("/me/agents", response_model=list[AgentOut])
def list_my_agents(
    key: ApiKey = Depends(require_owner_key),
    db: Session = Depends(get_db),
) -> list[AgentOut]:
    rows = db.execute(
        select(Agent).where(Agent.owner_id == key.owner_id).order_by(Agent.created_at.asc())
    ).scalars().all()
    return [AgentOut.model_validate(row) for row in rows]


@router.get("/{handle}/profile", response_model=OwnerProfileOut)
def read_owner_public_profile(handle: str, db: Session = Depends(get_db)) -> OwnerProfileOut:
    owner = db.execute(select(Owner).where(Owner.handle == handle.lower())).scalar_one_or_none()
    if owner is None or not owner_has_any_agent_or_human_activity(db, owner):
        # Same 404 either way — doesn't reveal whether the handle exists
        # but has never done anything, versus not existing at all.
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    record = human_category_record(db, owner.id)
    return OwnerProfileOut(
        owner=OwnerPublicOut.model_validate(owner),
        category_record={
            category: CategoryRecordOut(rating=r.rating, wins=r.wins, losses=r.losses, draws=r.draws)
            for category, r in record.items()
        },
        human_duel_history=human_duel_history(db, owner.id),
    )
