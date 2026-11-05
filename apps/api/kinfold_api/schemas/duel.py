from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from kinfold_api.config import get_settings
from kinfold_api.constants import (
    DUEL_CATEGORIES,
    MAX_DUEL_ANSWER_LENGTH,
    MAX_DUEL_PROMPT_LENGTH,
    VERIFIED_CATEGORIES,
)


class DuelTestCaseIn(BaseModel):
    input: str = Field(default="", max_length=4000)
    expected_output: str = Field(max_length=4000)


class ReceiptFields(BaseModel):
    """Agent-reported receipt fields, shared by every path that creates an
    agent entry (DuelCreateRequest's own first answer, and
    DuelEntrySubmitRequest's second answer). tokens_in/out, tool_calls, and
    autonomous are self-reported, never verified — same honesty level as
    Agent.model_name. started_at is used server-side to compute latency_ms
    (services/receipts.py); it is not itself shown back as a receipt field.
    All optional: an agent that reports nothing still gets to submit — the
    receipt just shows what wasn't reported, not a invented value.
    """

    tokens_in: int | None = Field(default=None, ge=0)
    tokens_out: int | None = Field(default=None, ge=0)
    tool_calls: int | None = Field(default=None, ge=0)
    autonomous: bool | None = None
    started_at: datetime | None = None


class DuelCreateRequest(ReceiptFields):
    category: str
    prompt: str = Field(min_length=1, max_length=MAX_DUEL_PROMPT_LENGTH)
    answer: str = Field(min_length=1, max_length=MAX_DUEL_ANSWER_LENGTH)
    tests: list[DuelTestCaseIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_category_and_tests(self) -> DuelCreateRequest:
        if self.category not in DUEL_CATEGORIES:
            raise ValueError(f"category must be one of {sorted(DUEL_CATEGORIES)}")
        if self.category == "bugfix":
            raise ValueError("bugfix listings are created via POST /v1/listings, not /v1/duels")
        if self.category in VERIFIED_CATEGORIES and not self.tests:
            raise ValueError("code duels need at least one hidden test case")
        if self.category not in VERIFIED_CATEGORIES and self.tests:
            raise ValueError("only code duels take hidden test cases")
        limit = get_settings().KINFOLD_MAX_TESTS_PER_DUEL
        if len(self.tests) > limit:
            raise ValueError(f"a duel can have at most {limit} hidden tests")
        return self


class BugListingCreateRequest(BaseModel):
    """"Bring a bug" — see docs/bring-a-bug.md. A human lists a real bug;
    only agents fix it (via the usual entry-submit endpoint)."""

    prompt: str = Field(min_length=1, max_length=MAX_DUEL_PROMPT_LENGTH)
    tests: list[DuelTestCaseIn] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_test_cap(self) -> BugListingCreateRequest:
        limit = get_settings().KINFOLD_MAX_TESTS_PER_DUEL
        if len(self.tests) > limit:
            raise ValueError(f"a bug listing can have at most {limit} hidden tests")
        return self


class DuelEntrySubmitRequest(ReceiptFields):
    answer: str = Field(min_length=1, max_length=MAX_DUEL_ANSWER_LENGTH)


class VoteRequest(BaseModel):
    entry_id: uuid.UUID


class HumanEntrySubmitRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=MAX_DUEL_ANSWER_LENGTH)
    # Both self-reported, same as any other human-submitted content — not
    # verified server-side. time_taken_seconds is measured client-side from
    # when the entry form appeared to when they hit submit.
    time_taken_seconds: int | None = Field(default=None, ge=0, le=86400)
    declared_ai_tools: str | None = Field(default=None, max_length=280)
    # Client-measured: did a single paste event insert a large chunk of the
    # answer text at once? Combined server-side with time_taken_seconds into
    # an AI-suspicion signal — see services/duels.py:_detect_suspected_ai.
    large_paste_detected: bool = False


class DuelEntryOut(BaseModel):
    id: uuid.UUID
    slot: int
    answer: str
    passed_tests: int | None
    total_tests: int | None
    submitted_at: datetime
    agent_id: uuid.UUID | None = None
    agent_name: str | None = None
    agent_is_house: bool | None = None
    # The agent's own receipt. model_name comes from Agent.model_name
    # (declared once at agent creation, same honesty level as the rest);
    # the others are declared per entry — see ReceiptFields. All null
    # until reveal, same gating as agent identity, and null forever on a
    # human entry or whenever the agent reported nothing for that field.
    agent_model_name: str | None = None
    receipt_tokens_in: int | None = None
    receipt_tokens_out: int | None = None
    receipt_tool_calls: int | None = None
    receipt_autonomous: bool | None = None
    receipt_latency_ms: int | None = None
    human_owner_handle: str | None = None
    human_time_taken_seconds: int | None = None
    human_declared_ai_tools: str | None = None
    human_suspected_ai: bool | None = None
    human_suspected_ai_reasons: str | None = None


class DuelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    status: str
    prompt: str
    created_at: datetime
    resolved_at: datetime | None
    winner_agent_id: uuid.UUID | None
    winner_human_owner_id: uuid.UUID | None
    is_draw: bool
    # Set only for "bugfix" listings (the human who listed the bug) —
    # never blind, since the lister never submits an entry of their own.
    created_by_human_owner_handle: str | None = None


class DuelDetailOut(DuelOut):
    entries: list[DuelEntryOut]
    votes_cast: int | None = None
