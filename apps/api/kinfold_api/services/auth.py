from __future__ import annotations

import re
import secrets

import httpx
import redis as redis_lib
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from kinfold_api.config import get_settings
from kinfold_api.models import ApiKey, Owner
from kinfold_api.services.events import append_event
from kinfold_api.services.keys import create_owner_key, revoke_key

STATE_TTL_SECONDS = 600
GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"


def create_login_state(redis_client: redis_lib.Redis) -> str:
    """A one-time CSRF token for the login round trip, stored in Redis with a
    short TTL. Consumed (deleted) exactly once, on callback."""
    state = secrets.token_urlsafe(24)
    redis_client.set(f"oauth_state:{state}", "1", ex=STATE_TTL_SECONDS)
    return state


def consume_login_state(redis_client: redis_lib.Redis, state: str) -> bool:
    deleted = redis_client.delete(f"oauth_state:{state}")
    return deleted == 1


def github_authorize_url(state: str) -> str:
    settings = get_settings()
    redirect_uri = f"{settings.KINFOLD_PUBLIC_API_URL}/v1/auth/github/callback"
    return str(
        httpx.URL(
            GITHUB_AUTHORIZE_URL,
            params={
                "client_id": settings.GITHUB_CLIENT_ID,
                "redirect_uri": redirect_uri,
                "scope": "read:user",
                "state": state,
            },
        )
    )


def exchange_code_for_token(code: str) -> str:
    settings = get_settings()
    redirect_uri = f"{settings.KINFOLD_PUBLIC_API_URL}/v1/auth/github/callback"
    response = httpx.post(
        GITHUB_TOKEN_URL,
        headers={"Accept": "application/json"},
        data={
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": redirect_uri,
        },
        timeout=10,
    )
    response.raise_for_status()
    token = response.json().get("access_token")
    if not token:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "GitHub did not return an access token.")
    return token


def fetch_github_profile(access_token: str) -> dict:
    response = httpx.get(
        GITHUB_USER_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "kinfold",
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def _derive_unique_handle(db: Session, login: str) -> str:
    base = re.sub(r"[^a-z0-9_-]", "", login.lower())[:40]
    if len(base) < 3:
        base = (base + "user")[:40]

    candidate = base
    suffix = 0
    while db.execute(select(Owner).where(Owner.handle == candidate)).scalar_one_or_none() is not None:
        suffix += 1
        tail = f"-{suffix}"
        candidate = base[: 40 - len(tail)] + tail
    return candidate


def find_or_create_owner_from_github(db: Session, *, github_id: str, login: str) -> Owner:
    existing = db.execute(select(Owner).where(Owner.github_id == github_id)).scalar_one_or_none()
    if existing is not None:
        return existing

    handle = _derive_unique_handle(db, login)
    owner = Owner(handle=handle, github_id=github_id)
    db.add(owner)
    db.flush()
    append_event(
        db, type="owner.created", owner_id=owner.id, payload={"handle": owner.handle, "via": "github"}
    )
    db.commit()
    db.refresh(owner)
    return owner


def issue_login_key(db: Session, *, owner: Owner) -> tuple[ApiKey, str]:
    """Revoke any previously active owner-kind key for this owner, then issue
    one fresh key — one active login per person, by design (docs/decisions.md)."""
    previous_keys = (
        db.execute(
            select(ApiKey).where(
                ApiKey.owner_id == owner.id,
                ApiKey.kind == "owner",
                ApiKey.revoked_at.is_(None),
            )
        )
        .scalars()
        .all()
    )
    for key in previous_keys:
        revoke_key(db, api_key=key)

    api_key, raw_key = create_owner_key(db, owner_id=owner.id, label="github login")
    append_event(
        db,
        type="key.created",
        owner_id=owner.id,
        payload={
            "key_id": str(api_key.id),
            "kind": "owner",
            "prefix": api_key.prefix,
            "via": "github",
        },
    )
    db.commit()
    db.refresh(api_key)
    return api_key, raw_key
