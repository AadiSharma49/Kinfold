from __future__ import annotations

import time
import uuid

import redis as redis_lib
from fastapi import HTTPException, status


def enforce_rate_limit(redis_client: redis_lib.Redis, key_id: uuid.UUID, limit_per_minute: int) -> None:
    window = int(time.time() // 60)
    bucket_key = f"ratelimit:{key_id}:{window}"

    count = redis_client.incr(bucket_key)
    if count == 1:
        redis_client.expire(bucket_key, 60)

    if count > limit_per_minute:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Rate limit exceeded")
