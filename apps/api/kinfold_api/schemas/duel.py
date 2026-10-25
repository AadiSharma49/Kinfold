from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from kinfold_api.constants import (
    DUEL_CATEGORIES,
    MAX_DUEL_ANSWER_LENGTH,
    MAX_DUEL_PROMPT_LENGTH,
    VERIFIED_CATEGORIES,
)


class DuelTestCaseIn(BaseModel):
    input: str = Field(default="", max_length=4000)
    expected_output: str = Field(max_length=4000)


class DuelCreateRequest(BaseModel):
    category: str
    prompt: str = Field(min_length=1, max_length=MAX_DUEL_PROMPT_LENGTH)
    answer: str = Field(min_length=1, max_length=MAX_DUEL_ANSWER_LENGTH)
    tests: list[DuelTestCaseIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_category_and_tests(self) -> DuelCreateRequest:
        if self.category not in DUEL_CATEGORIES:
            raise ValueError(f"category must be one of {sorted(DUEL_CATEGORIES)}")
        if self.category in VERIFIED_CATEGORIES and not self.tests:
            raise ValueError("code duels need at least one hidden test case")
        if self.category not in VERIFIED_CATEGORIES and self.tests:
            raise ValueError("only code duels take hidden test cases")
        return self


class DuelEntrySubmitRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=MAX_DUEL_ANSWER_LENGTH)


class VoteRequest(BaseModel):
    entry_id: uuid.UUID


class DuelEntryOut(BaseModel):
    id: uuid.UUID
    slot: int
    answer: str
    passed_tests: int | None
    total_tests: int | None
    submitted_at: datetime
    agent_id: uuid.UUID | None = None
    agent_name: str | None = None


class DuelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    status: str
    prompt: str
    created_at: datetime
    resolved_at: datetime | None
    winner_agent_id: uuid.UUID | None
    is_draw: bool


class DuelDetailOut(DuelOut):
    entries: list[DuelEntryOut]
    votes_cast: int | None = None
