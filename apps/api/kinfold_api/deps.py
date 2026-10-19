from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime

import redis as redis_lib
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from kinfold_api.config import get_settings
from kinfold_api.db import get_db
from kinfold_api.models import ApiKey
from kinfold_api.security import hash_key
from kinfold_api.services.rate_limit import enforce_rate_limit

settings = get_settings()
_redis_client = redis_lib.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def get_redis() -> Generator[redis_lib.Redis, None, None]:
    yield _redis_client


def get_current_key(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> ApiKey:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing or malformed Authorization header")

    raw_key = authorization.removeprefix("Bearer ").strip()
    if not raw_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing or malformed Authorization header")

    api_key = db.execute(
        select(ApiKey).where(ApiKey.key_hash == hash_key(raw_key))
    ).scalar_one_or_none()

    if api_key is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")
    if api_key.revoked_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "API key has been revoked")

    api_key.last_used_at = datetime.now(UTC)
    db.commit()
    db.refresh(api_key)
    return api_key


def require_owner_key(
    key: ApiKey = Depends(get_current_key),
    redis_client: redis_lib.Redis = Depends(get_redis),
) -> ApiKey:
    if key.kind != "owner":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "An owner key is required for this route")
    enforce_rate_limit(redis_client, key.id, settings.KINFOLD_RATE_LIMIT_PER_MINUTE)
    return key


def require_agent_key(
    key: ApiKey = Depends(get_current_key),
    redis_client: redis_lib.Redis = Depends(get_redis),
) -> ApiKey:
    if key.kind != "agent":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "An agent key is required for this route")
    enforce_rate_limit(redis_client, key.id, settings.KINFOLD_RATE_LIMIT_PER_MINUTE)
    return key
