from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from kinfold_api.schemas.api_key import ApiKeyCreatedOut


class OwnerDevSignupRequest(BaseModel):
    handle: str = Field(min_length=3, max_length=40)


class OwnerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    handle: str
    is_admin: bool
    created_at: datetime


class OwnerWithKeyOut(BaseModel):
    owner: OwnerOut
    key: ApiKeyCreatedOut


class OwnerPublicOut(BaseModel):
    """Deliberately narrower than OwnerOut — no id, no is_admin, nothing
    that isn't meant for a public profile page."""

    model_config = ConfigDict(from_attributes=True)

    handle: str
    created_at: datetime


class HumanDuelHistoryEntryOut(BaseModel):
    duel_id: uuid.UUID
    category: str
    prompt: str
    resolved_at: datetime | None
    result: str  # "win" | "loss" | "draw"
    time_taken_seconds: int | None
    declared_ai_tools: str | None
    opponent_agent_name: str | None
    opponent_agent_is_house: bool | None


class OwnerProfileOut(BaseModel):
    owner: OwnerPublicOut
    human_duel_history: list[HumanDuelHistoryEntryOut]
