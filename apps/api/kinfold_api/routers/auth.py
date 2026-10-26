from __future__ import annotations

import redis as redis_lib
from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from kinfold_api.config import get_settings
from kinfold_api.db import get_db
from kinfold_api.deps import get_redis
from kinfold_api.services.auth import (
    consume_login_state,
    create_login_state,
    exchange_code_for_token,
    fetch_github_profile,
    find_or_create_owner_from_github,
    github_authorize_url,
    issue_login_key,
)

router = APIRouter(prefix="/auth/github", tags=["auth"])


@router.get("/login")
def github_login(redis_client: redis_lib.Redis = Depends(get_redis)) -> RedirectResponse:
    state = create_login_state(redis_client)
    return RedirectResponse(github_authorize_url(state))


@router.get("/callback")
def github_callback(
    code: str = Query(...),
    state: str = Query(...),
    redis_client: redis_lib.Redis = Depends(get_redis),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    settings = get_settings()
    error_redirect = f"{settings.KINFOLD_WEB_URL}/auth/callback#error=1"

    if not consume_login_state(redis_client, state):
        return RedirectResponse(error_redirect)

    try:
        access_token = exchange_code_for_token(code)
        profile = fetch_github_profile(access_token)
        github_id = str(profile["id"])
        login = profile.get("login") or f"user{github_id}"
        owner = find_or_create_owner_from_github(db, github_id=github_id, login=login)
        _, raw_key = issue_login_key(db, owner=owner)
    except Exception as exc:  # noqa: BLE001 - any failure in this external chain lands on an error page
        print(f"github oauth callback failed: {exc!r}")
        return RedirectResponse(error_redirect)

    return RedirectResponse(f"{settings.KINFOLD_WEB_URL}/auth/callback#key={raw_key}")
