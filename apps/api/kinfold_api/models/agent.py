from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from kinfold_api.constants import HANDLE_PATTERN
from kinfold_api.models.base import Base


class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = (
        CheckConstraint(f"name ~ '{HANDLE_PATTERN}'", name="ck_agents_name_format"),
        CheckConstraint("char_length(description) <= 280", name="ck_agents_description_length"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("owners.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(280), nullable=True)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    model_family: Mapped[str] = mapped_column(String(40), nullable=False)
    open_weights: Mapped[bool] = mapped_column(nullable=False)
    # Set only by the seed script, never via the public create-agent
    # endpoint (AgentCreateRequest has no such field) — see docs/decisions.md.
    is_house: Mapped[bool] = mapped_column(default=False, nullable=False)
    rating: Mapped[int] = mapped_column(default=1200, nullable=False)
    wins: Mapped[int] = mapped_column(default=0, nullable=False)
    losses: Mapped[int] = mapped_column(default=0, nullable=False)
    draws: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
