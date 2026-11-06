from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


# Keep these exact strings in sync with the roles in
# apps/web/src/lib/waitlist.ts.
class WaitlistRole(StrEnum):
    watcher = "watcher"
    agent_builder = "agent builder"
    open_model_trainer = "open model trainer"
    researcher = "researcher"
    other = "other"


_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class WaitlistCreateRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    role: WaitlistRole
    bring: str | None = Field(default=None, max_length=280)
    # Honeypot. Real people never fill this hidden field, so a value means
    # the submission is a bot; it is accepted but never stored.
    company: str = Field(default="", max_length=200)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = value.strip().lower()
        if not _EMAIL_PATTERN.match(email):
            raise ValueError("enter a valid email address")
        return email

    @field_validator("bring")
    @classmethod
    def normalize_bring(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None

    @field_validator("company")
    @classmethod
    def normalize_company(cls, value: str) -> str:
        return value.strip()


class WaitlistResponse(BaseModel):
    status: Literal["ok", "duplicate"]
    message: str | None = None
