from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from kinfold_api.models.base import Base


class Duel(Base):
    __tablename__ = "duels"
    __table_args__ = (
        CheckConstraint("category IN ('code', 'debate', 'explain', 'hinglish')", name="ck_duels_category"),
        CheckConstraint(
            "status IN ('open', 'judging', 'resolved')", name="ck_duels_status"
        ),
        CheckConstraint("char_length(prompt) <= 2000", name="ck_duels_prompt_length"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", index=True)
    prompt: Mapped[str] = mapped_column(String(2000), nullable=False)
    created_by_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False
    )
    winner_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )
    is_draw: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
