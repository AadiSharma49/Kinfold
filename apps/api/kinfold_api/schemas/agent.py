from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from kinfold_api.schemas.api_key import ApiKeyCreatedOut


class AgentCreateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=40)
    description: str | None = Field(default=None, max_length=280)
    model_name: str = Field(min_length=1, max_length=120)
    model_family: str = Field(min_length=1, max_length=40)
    open_weights: bool = True


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    description: str | None
    model_name: str
    model_family: str
    open_weights: bool
    rating: int
    wins: int
    losses: int
    draws: int
    created_at: datetime


class AgentPublicOut(AgentOut):
    owner_handle: str


class AgentWithKeyOut(BaseModel):
    agent: AgentOut
    key: ApiKeyCreatedOut
