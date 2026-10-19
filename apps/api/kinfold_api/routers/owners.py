from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from kinfold_api.config import get_settings
from kinfold_api.db import get_db
from kinfold_api.deps import require_owner_key
from kinfold_api.models import ApiKey, Owner
from kinfold_api.schemas.api_key import build_created_out
from kinfold_api.schemas.owner import OwnerDevSignupRequest, OwnerOut, OwnerWithKeyOut
from kinfold_api.services.owners import create_owner_with_key

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
