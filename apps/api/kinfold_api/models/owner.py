from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from kinfold_api.constants import HANDLE_PATTERN
from kinfold_api.models.base import Base


class Owner(Base):
    __tablename__ = "owners"
    __table_args__ = (
        CheckConstraint(f"handle ~ '{HANDLE_PATTERN}'", name="ck_owners_handle_format"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    handle: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    github_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    is_admin: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
