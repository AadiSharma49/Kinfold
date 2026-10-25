from __future__ import annotations

import redis as redis_lib
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from kinfold_api.db import get_db
from kinfold_api.deps import get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
def health(
    db: Session = Depends(get_db),
    redis_client: redis_lib.Redis = Depends(get_redis),
) -> dict:
    database_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        database_status = "error"

    redis_status = "ok"
    try:
        redis_client.ping()
    except Exception:
        redis_status = "error"

    overall = "ok" if database_status == "ok" and redis_status == "ok" else "degraded"
    return {"status": overall, "database": database_status, "redis": redis_status}
