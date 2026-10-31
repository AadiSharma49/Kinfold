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
    # Set instead of winner_agent_id when a human entry wins — never both.
    winner_human_owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("owners.id"), nullable=True
    )
    is_draw: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Set by an admin action in response to a report. A hidden duel 404s
    # from every public route — see docs/decisions.md, 2026-10-31.
    hidden_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
