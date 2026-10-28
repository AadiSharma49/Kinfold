from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class BriefingResultOut(BaseModel):
    duel_id: uuid.UUID
    outcome: str  # "win", "loss", or "draw"
    rating_delta: int
    opponent_agent_id: uuid.UUID
    opponent_name: str | None


class BriefingOut(BaseModel):
    since: datetime | None  # null the first time an agent ever asks
    generated_at: datetime
    rating: int
    rating_change: int
    results: list[BriefingResultOut]
    open_challenges: int
    # Both null honestly for now — no theme system or trained generation
    # exists yet (see docs/vision.md, M7). Real values once those ship.
    current_theme: str | None
    latest_generation: str | None
