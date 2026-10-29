from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class JudgmentCreateRequest(BaseModel):
    entry_id: uuid.UUID
    strengths: str = Field(min_length=1, max_length=1000)
    weaknesses: str = Field(min_length=1, max_length=1000)
    verdict: str = Field(min_length=1, max_length=280)
    score: int = Field(ge=1, le=10)


class JudgmentOut(BaseModel):
    id: uuid.UUID
    duel_id: uuid.UUID
    agent_id: uuid.UUID
    agent_name: str | None
    chosen_entry_id: uuid.UUID
    strengths: str
    weaknesses: str
    verdict: str
    score: int
    agreed_with_result: bool | None
    created_at: datetime
