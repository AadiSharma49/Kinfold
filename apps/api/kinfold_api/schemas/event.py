from __future__ import annotations

from pydantic import BaseModel


class EventVerifyOut(BaseModel):
    ok: bool
    broken_at_seq: int | None = None
