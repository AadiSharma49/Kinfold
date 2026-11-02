from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from kinfold_api.schemas.agent import CategoryRecordOut
from kinfold_api.schemas.api_key import ApiKeyCreatedOut


class OwnerDevSignupRequest(BaseModel):
    handle: str = Field(min_length=3, max_length=40)


class OwnerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    handle: str
    is_admin: bool
    # A real, elo-updated rating for duels this person enters directly as
    # a human — see docs/decisions.md, 2026-11-02. Untouched by anything
    # their agents do; starts at 1200, same as an agent's.
    rating: int
    wins: int
    losses: int
    draws: int
    created_at: datetime


class OwnerWithKeyOut(BaseModel):
    owner: OwnerOut
    key: ApiKeyCreatedOut


class OwnerPublicOut(BaseModel):
    """Deliberately narrower than OwnerOut — no id, no is_admin, nothing
    that isn't meant for a public profile page."""

    model_config = ConfigDict(from_attributes=True)

    handle: str
    rating: int
    wins: int
    losses: int
    draws: int
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
    # Real per-category elo for the crowd duels this person has entered
    # themselves (debate/explain/hinglish — the only categories open to a
    # human entrant) — see docs/decisions.md, 2026-11-02.
    category_record: dict[str, CategoryRecordOut]
    human_duel_history: list[HumanDuelHistoryEntryOut]
