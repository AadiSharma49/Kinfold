from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from kinfold_api.db import get_db
from kinfold_api.deps import require_owner_key
from kinfold_api.models import ApiKey
from kinfold_api.schemas.api_key import (
    ApiKeyCreatedOut,
    ApiKeyOut,
    CreateKeyRequest,
    build_created_out,
)
from kinfold_api.services.keys import issue_additional_owner_key, revoke_key

router = APIRouter(tags=["keys"])


@router.post("/owners/keys", response_model=ApiKeyCreatedOut, status_code=status.HTTP_201_CREATED)
def create_additional_owner_key(
    body: CreateKeyRequest,
    key: ApiKey = Depends(require_owner_key),
    db: Session = Depends(get_db),
) -> ApiKeyCreatedOut:
    api_key, raw_key = issue_additional_owner_key(db, owner_id=key.owner_id, label=body.label)
    return build_created_out(api_key, raw_key)


@router.get("/keys", response_model=list[ApiKeyOut])
def list_my_keys(
    key: ApiKey = Depends(require_owner_key),
    db: Session = Depends(get_db),
) -> list[ApiKeyOut]:
    rows = (
        db.execute(select(ApiKey).where(ApiKey.owner_id == key.owner_id).order_by(ApiKey.created_at.asc()))
        .scalars()
        .all()
    )
    return [ApiKeyOut.model_validate(row) for row in rows]


@router.delete("/keys/{key_id}", response_model=ApiKeyOut)
def revoke_my_key(
    key_id: uuid.UUID,
    key: ApiKey = Depends(require_owner_key),
    db: Session = Depends(get_db),
) -> ApiKeyOut:
    target = db.get(ApiKey, key_id)
    if target is None or target.owner_id != key.owner_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    revoked = revoke_key(db, api_key=target)
    return ApiKeyOut.model_validate(revoked)
