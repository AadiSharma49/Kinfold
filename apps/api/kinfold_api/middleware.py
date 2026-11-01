"""One middleware, two jobs, both cross-cutting concerns that don't belong
in any single route:

1. A per-IP rate limit for every request that doesn't carry an API key at
   all — the existing per-key limiter (services/rate_limit.py, used by
   deps.py) only ever runs for routes behind require_*_key, which left
   every public GET (and dev-signup) with no limit whatsoever. This closes
   that gap uniformly instead of hoping each new public route remembers to
   opt in. Authenticated routes get this too, on top of their own per-key
   limit — defense in depth against one IP spamming many different keys.
2. A request ID (generated or passed through via X-Request-Id) attached to
   the response and to one structured JSON log line per request.

See docs/security.md for the full reasoning.
"""

from __future__ import annotations

import ipaddress
import json
import logging
import time
import uuid

from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from kinfold_api.config import get_settings
from kinfold_api.deps import get_redis_client
from kinfold_api.services.rate_limit import enforce_rate_limit

logger = logging.getLogger("kinfold_api.requests")

_EXEMPT_PATHS = {"/v1/health"}


def _parse_trusted_proxies(raw: str) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    networks = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        try:
            networks.append(ipaddress.ip_network(entry, strict=False))
        except ValueError:
            continue  # a malformed entry in config shouldn't crash every request
    return networks


def _is_trusted_proxy(ip_str: str, trusted: list) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return any(ip in network for network in trusted)


def _client_ip(request: Request) -> str:
    """The direct TCP peer is always the source of truth. X-Forwarded-For
    is only believed when that direct peer is itself a configured trusted
    proxy (Caddy in production) — otherwise any client could spoof the
    header to claim a different IP on every request and dodge the rate
    limiter entirely. See KINFOLD_TRUSTED_PROXY_IPS and docs/security.md.
    """
    direct_ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if not forwarded:
        return direct_ip

    trusted = _parse_trusted_proxies(get_settings().KINFOLD_TRUSTED_PROXY_IPS)
    if not _is_trusted_proxy(direct_ip, trusted):
        return direct_ip

    return forwarded.split(",")[0].strip()


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        client_ip = _client_ip(request)
        path = request.url.path

        if path not in _EXEMPT_PATHS:
            limit = get_settings().KINFOLD_PUBLIC_RATE_LIMIT_PER_MINUTE
            try:
                enforce_rate_limit(get_redis_client(), f"ip:{client_ip}", limit)
            except HTTPException as exc:
                return JSONResponse(
                    {"detail": exc.detail},
                    status_code=exc.status_code,
                    headers={"X-Request-Id": request_id},
                )

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        response.headers["X-Request-Id"] = request_id
        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "method": request.method,
                    "path": path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                    "client_ip": client_ip,
                }
            )
        )
        return response
