from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApiKeyOut(BaseModel):
    """Never includes key_hash."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    owner_id: uuid.UUID
    agent_id: uuid.UUID | None
    prefix: str
    label: str | None
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None


class ApiKeyCreatedOut(ApiKeyOut):
    key: str
    warning: str = (
        "This is the only time the full key is shown. Store it now; it cannot be shown again."
    )


class CreateKeyRequest(BaseModel):
    label: str | None = Field(default=None, max_length=80)


def build_created_out(api_key, raw_key: str) -> ApiKeyCreatedOut:
    return ApiKeyCreatedOut(
        id=api_key.id,
        kind=api_key.kind,
        owner_id=api_key.owner_id,
        agent_id=api_key.agent_id,
        prefix=api_key.prefix,
        label=api_key.label,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        revoked_at=api_key.revoked_at,
        key=raw_key,
    )
