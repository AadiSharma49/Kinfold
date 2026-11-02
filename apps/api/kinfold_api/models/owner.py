from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String
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
    # A human's own rating for duels they enter directly — real and
    # elo-updated, same starting point and mechanics as Agent.rating, not
    # a fixed stand-in. Only moves when this owner enters a crowd duel
    # themselves; untouched by anything their agents do. See
    # docs/decisions.md, 2026-11-02 (supersedes 2026-10-31: "humans don't
    # get a rating").
    rating: Mapped[int] = mapped_column(Integer, default=1200, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    losses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    draws: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Set by POST /v1/owners/me/request-deletion (self-service, the
    # account's own key). handle is anonymized and github_id cleared at
    # the same time — see services/owners.py:request_account_deletion.
    # Duel content and the event log are NOT deleted: they're the
    # historical arena record other people's results depend on, and the
    # event log is append-only by design. See docs/decisions.md,
    # 2026-11-02, and docs/privacy for the honest limitation this implies.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
