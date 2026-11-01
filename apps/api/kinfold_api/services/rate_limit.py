from __future__ import annotations

import time
import uuid

import redis as redis_lib
from fastapi import HTTPException, status


def enforce_rate_limit(
    redis_client: redis_lib.Redis, identifier: str | uuid.UUID, limit_per_minute: int
) -> None:
    """identifier is usually an API key's id (per-key limiting on
    authenticated routes) but can be any string — e.g. a client IP, for
    the public-route limiter in main.py's middleware, which covers every
    unauthenticated endpoint uniformly instead of relying on each route
    remembering to opt in. See docs/security.md."""
    window = int(time.time() // 60)
    bucket_key = f"ratelimit:{identifier}:{window}"

    count = redis_client.incr(bucket_key)
    if count == 1:
        redis_client.expire(bucket_key, 60)

    if count > limit_per_minute:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Rate limit exceeded")
