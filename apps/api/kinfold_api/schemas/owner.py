from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from kinfold_api.schemas.api_key import ApiKeyCreatedOut


class OwnerDevSignupRequest(BaseModel):
    handle: str = Field(min_length=3, max_length=40)


class OwnerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    handle: str
    is_admin: bool
    created_at: datetime


class OwnerWithKeyOut(BaseModel):
    owner: OwnerOut
    key: ApiKeyCreatedOut
