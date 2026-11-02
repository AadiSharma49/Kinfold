from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from kinfold_api.models.base import Base


class CategoryRating(Base):
    """One entrant's rating within a single duel category — separate from
    (and elo-updated independently of) their one overall rating
    (Agent.rating / Owner.rating). Created lazily, the first time an
    entrant's duel in that category resolves — see
    services/duels.py:_get_or_create_category_rating. See
    docs/decisions.md, 2026-11-02."""

    __tablename__ = "category_ratings"
    __table_args__ = (
        CheckConstraint(
            "category IN ('code', 'bugfix', 'debate', 'explain', 'hinglish')",
            name="ck_category_ratings_category",
        ),
        CheckConstraint(
            "(agent_id IS NOT NULL AND human_owner_id IS NULL) OR "
            "(agent_id IS NULL AND human_owner_id IS NOT NULL)",
            name="ck_category_ratings_entrant_kind",
        ),
        Index(
            "ix_category_ratings_agent_category",
            "agent_id",
            "category",
            unique=True,
            postgresql_where="agent_id IS NOT NULL",
        ),
        Index(
            "ix_category_ratings_human_category",
            "human_owner_id",
            "category",
            unique=True,
            postgresql_where="human_owner_id IS NOT NULL",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True, index=True
    )
    human_owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("owners.id"), nullable=True, index=True
    )
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, default=1200, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    losses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    draws: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
