from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReportCreateRequest(BaseModel):
    target_type: str  # "duel" | "entry" | "judgment"
    target_id: uuid.UUID
    reason: str = Field(min_length=1, max_length=500)


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    reason: str
    created_at: datetime
    resolved_at: datetime | None
