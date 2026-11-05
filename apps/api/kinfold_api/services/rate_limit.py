from __future__ import annotations

import logging
import time
import uuid

import redis as redis_lib
from fastapi import HTTPException, status

logger = logging.getLogger("kinfold_api.rate_limit")

# INCR and the first EXPIRE must be one atomic step. The old code did
# INCR, then EXPIRE only when the counter was 1; a crash in between left
# a key with no TTL, so that identifier stayed over the limit forever.
# TTL < 0 means "no expiry"; setting it only then keeps the window fixed
# instead of sliding forward on every request.
_INCR_WITH_TTL = """
local count = redis.call('INCR', KEYS[1])
if redis.call('TTL', KEYS[1]) < 0 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


def enforce_rate_limit(
    redis_client: redis_lib.Redis, identifier: str | uuid.UUID, limit_per_minute: int
) -> None:
    """identifier is usually an API key's id (per-key limiting on
    authenticated routes) but can be any string — e.g. a client IP, for
    the public-route limiter in middleware.py, which covers every
    unauthenticated endpoint uniformly instead of relying on each route
    remembering to opt in. See docs/security.md.

    If Redis is unreachable, the request is allowed: the API's job is to
    serve agents, and a Redis blip should not take the whole product down.
    The tradeoff is explicit — an attacker who can take Redis down can
    also bypass rate limits. See docs/security.md."""
    window = int(time.time() // 60)
    bucket_key = f"ratelimit:{identifier}:{window}"

    try:
        count = redis_client.register_script(_INCR_WITH_TTL)(keys=[bucket_key], args=[60])
    except redis_lib.RedisError:
        logger.warning("rate limiter unavailable; allowing request for %s", identifier)
        return

    if count > limit_per_minute:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Rate limit exceeded")
