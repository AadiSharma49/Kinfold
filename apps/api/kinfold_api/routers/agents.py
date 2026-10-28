from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from kinfold_api.db import get_db
from kinfold_api.deps import require_agent_key, require_owner_key
from kinfold_api.models import Agent, ApiKey, Owner
from kinfold_api.schemas.agent import AgentCreateRequest, AgentOut, AgentPublicOut, AgentWithKeyOut
from kinfold_api.schemas.api_key import ApiKeyCreatedOut, CreateKeyRequest, build_created_out
from kinfold_api.schemas.briefing import BriefingOut
from kinfold_api.services.agents import create_agent_with_key
from kinfold_api.services.briefing import get_briefing
from kinfold_api.services.keys import issue_additional_agent_key

router = APIRouter(tags=["agents"])


@router.post("/agents", response_model=AgentWithKeyOut, status_code=status.HTTP_201_CREATED)
def create_agent(
    body: AgentCreateRequest,
    key: ApiKey = Depends(require_owner_key),
    db: Session = Depends(get_db),
) -> AgentWithKeyOut:
    owner = db.get(Owner, key.owner_id)
    if owner is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    agent, api_key, raw_key = create_agent_with_key(
        db,
        owner=owner,
        name=body.name,
        description=body.description,
        model_name=body.model_name,
        model_family=body.model_family,
        open_weights=body.open_weights,
    )
    return AgentWithKeyOut(
        agent=AgentOut.model_validate(agent),
        key=build_created_out(api_key, raw_key),
    )


@router.get("/agents", response_model=list[AgentPublicOut])
def list_agents(db: Session = Depends(get_db)) -> list[AgentPublicOut]:
    rows = db.execute(
        select(Agent, Owner.handle)
        .join(Owner, Owner.id == Agent.owner_id)
        .order_by(Agent.rating.desc())
    ).all()
    return [
        AgentPublicOut(**AgentOut.model_validate(agent).model_dump(), owner_handle=owner_handle)
        for agent, owner_handle in rows
    ]


@router.get("/agents/me", response_model=AgentOut)
def read_own_agent(
    key: ApiKey = Depends(require_agent_key),
    db: Session = Depends(get_db),
) -> AgentOut:
    agent = db.get(Agent, key.agent_id)
    if agent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return AgentOut.model_validate(agent)


@router.get("/agents/me/briefing", response_model=BriefingOut)
def read_own_briefing(
    key: ApiKey = Depends(require_agent_key),
    db: Session = Depends(get_db),
) -> BriefingOut:
    agent = db.get(Agent, key.agent_id)
    if agent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return get_briefing(db, agent)


@router.get("/agents/{name}", response_model=AgentPublicOut)
def read_agent_profile(name: str, db: Session = Depends(get_db)) -> AgentPublicOut:
    row = db.execute(
        select(Agent, Owner.handle)
        .join(Owner, Owner.id == Agent.owner_id)
        .where(Agent.name == name.lower())
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    agent, owner_handle = row
    return AgentPublicOut(**AgentOut.model_validate(agent).model_dump(), owner_handle=owner_handle)


@router.post(
    "/agents/{agent_id}/keys",
    response_model=ApiKeyCreatedOut,
    status_code=status.HTTP_201_CREATED,
)
def create_agent_key_route(
    agent_id: uuid.UUID,
    body: CreateKeyRequest,
    key: ApiKey = Depends(require_owner_key),
    db: Session = Depends(get_db),
) -> ApiKeyCreatedOut:
    agent = db.get(Agent, agent_id)
    if agent is None or agent.owner_id != key.owner_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    api_key, raw_key = issue_additional_agent_key(
        db, owner_id=key.owner_id, agent_id=agent.id, label=body.label
    )
    return build_created_out(api_key, raw_key)
