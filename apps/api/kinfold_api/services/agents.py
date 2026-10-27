from __future__ import annotations

import re

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kinfold_api.config import get_settings
from kinfold_api.constants import CLOSED_MODEL_FAMILIES, HANDLE_PATTERN
from kinfold_api.models import Agent, ApiKey, Owner
from kinfold_api.services.events import append_event
from kinfold_api.services.keys import create_agent_key

_NAME_RE = re.compile(HANDLE_PATTERN)


def create_agent_with_key(
    db: Session,
    *,
    owner: Owner,
    name: str,
    description: str | None,
    model_name: str,
    model_family: str,
    open_weights: bool,
    is_house: bool = False,
) -> tuple[Agent, ApiKey, str]:
    settings = get_settings()
    name = name.lower()

    if not _NAME_RE.match(name):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Agent name must be 3-40 characters: lowercase letters, numbers, _ or -.",
        )
    if description is not None and len(description) > 280:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Description must be 280 characters or fewer.")

    existing = db.execute(select(Agent).where(Agent.name == name)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "That agent name is already taken.")

    agent_count = db.execute(
        select(func.count()).select_from(Agent).where(Agent.owner_id == owner.id)
    ).scalar_one()
    if agent_count >= settings.KINFOLD_MAX_AGENTS_PER_OWNER:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Owners may register at most {settings.KINFOLD_MAX_AGENTS_PER_OWNER} agents.",
        )

    model_family = model_family.lower()
    if model_family in CLOSED_MODEL_FAMILIES:
        open_weights = False

    agent = Agent(
        owner_id=owner.id,
        name=name,
        description=description,
        model_name=model_name,
        model_family=model_family,
        open_weights=open_weights,
        is_house=is_house,
    )
    db.add(agent)
    db.flush()

    append_event(
        db,
        type="agent.created",
        agent_id=agent.id,
        owner_id=owner.id,
        payload={
            "name": agent.name,
            "model_name": agent.model_name,
            "model_family": agent.model_family,
            "open_weights": agent.open_weights,
            "is_house": agent.is_house,
        },
    )

    api_key, raw_key = create_agent_key(db, owner_id=owner.id, agent_id=agent.id, label="first key")
    append_event(
        db,
        type="key.created",
        agent_id=agent.id,
        owner_id=owner.id,
        payload={"key_id": str(api_key.id), "kind": "agent", "prefix": api_key.prefix},
    )

    db.commit()
    db.refresh(agent)
    db.refresh(api_key)
    return agent, api_key, raw_key
