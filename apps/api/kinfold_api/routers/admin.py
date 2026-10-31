from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from kinfold_api.db import get_db
from kinfold_api.deps import require_admin_key
from kinfold_api.models import Agent, ApiKey, Duel, DuelEntry, Vote
from kinfold_api.schemas.agent import AgentOut
from kinfold_api.schemas.api_key import ApiKeyOut
from kinfold_api.schemas.duel import DuelOut
from kinfold_api.services.admin import (
    admin_revoke_key,
    approve_agent_sandbox,
    disable_agent,
    hide_duel,
    hide_entry,
    hide_judgment,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/duels/{duel_id}/hide", response_model=DuelOut)
def hide_duel_route(
    duel_id: uuid.UUID, key: ApiKey = Depends(require_admin_key), db: Session = Depends(get_db)
) -> DuelOut:
    duel = db.get(Duel, duel_id)
    if duel is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return DuelOut.model_validate(hide_duel(db, duel=duel, admin_owner_id=key.owner_id))


@router.post("/entries/{entry_id}/hide", status_code=status.HTTP_204_NO_CONTENT)
def hide_entry_route(
    entry_id: uuid.UUID, key: ApiKey = Depends(require_admin_key), db: Session = Depends(get_db)
) -> None:
    entry = db.get(DuelEntry, entry_id)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    hide_entry(db, entry=entry, admin_owner_id=key.owner_id)


@router.post("/judgments/{judgment_id}/hide", status_code=status.HTTP_204_NO_CONTENT)
def hide_judgment_route(
    judgment_id: uuid.UUID, key: ApiKey = Depends(require_admin_key), db: Session = Depends(get_db)
) -> None:
    judgment = db.get(Vote, judgment_id)
    if judgment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    hide_judgment(db, judgment=judgment, admin_owner_id=key.owner_id)


@router.post("/agents/{agent_id}/disable", response_model=AgentOut)
def disable_agent_route(
    agent_id: uuid.UUID, key: ApiKey = Depends(require_admin_key), db: Session = Depends(get_db)
) -> AgentOut:
    agent = db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return AgentOut.model_validate(disable_agent(db, agent=agent, admin_owner_id=key.owner_id))


@router.post("/agents/{agent_id}/approve-sandbox", response_model=AgentOut)
def approve_agent_sandbox_route(
    agent_id: uuid.UUID, key: ApiKey = Depends(require_admin_key), db: Session = Depends(get_db)
) -> AgentOut:
    agent = db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return AgentOut.model_validate(approve_agent_sandbox(db, agent=agent, admin_owner_id=key.owner_id))


@router.delete("/keys/{key_id}", response_model=ApiKeyOut)
def admin_revoke_key_route(
    key_id: uuid.UUID, key: ApiKey = Depends(require_admin_key), db: Session = Depends(get_db)
) -> ApiKeyOut:
    target = db.get(ApiKey, key_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return ApiKeyOut.model_validate(admin_revoke_key(db, api_key=target, admin_owner_id=key.owner_id))
