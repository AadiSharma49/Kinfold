from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from kinfold_api.models import Duel, DuelEntry, Report, Vote
from kinfold_api.services.events import append_event

_TARGET_MODELS = {"duel": Duel, "entry": DuelEntry, "judgment": Vote}


def file_report(
    db: Session,
    *,
    target_type: str,
    target_id: uuid.UUID,
    reason: str,
    reporter_owner_id: uuid.UUID | None,
    reporter_agent_id: uuid.UUID | None,
) -> Report:
    model = _TARGET_MODELS.get(target_type)
    if model is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "target_type must be duel, entry, or judgment")
    if db.get(model, target_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That doesn't exist.")

    report = Report(
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        reporter_owner_id=reporter_owner_id,
        reporter_agent_id=reporter_agent_id,
    )
    db.add(report)
    db.flush()

    append_event(
        db,
        type="report.filed",
        owner_id=reporter_owner_id,
        agent_id=reporter_agent_id,
        payload={"report_id": str(report.id), "target_type": target_type, "target_id": str(target_id)},
    )
    db.commit()
    db.refresh(report)
    return report


def list_reports(db: Session, *, resolved: bool | None = None) -> list[Report]:
    query = select(Report).order_by(Report.created_at.desc())
    if resolved is True:
        query = query.where(Report.resolved_at.is_not(None))
    elif resolved is False:
        query = query.where(Report.resolved_at.is_(None))
    return list(db.execute(query).scalars())


def resolve_report(db: Session, *, report: Report, admin_owner_id: uuid.UUID) -> Report:
    """Idempotent: resolving an already-resolved report is a no-op, same
    pattern as revoke_key."""
    if report.resolved_at is None:
        report.resolved_at = datetime.now(UTC)
        report.resolved_by_owner_id = admin_owner_id
        db.flush()
        append_event(
            db,
            type="admin.report_resolved",
            owner_id=admin_owner_id,
            payload={"report_id": str(report.id)},
        )
        db.commit()
        db.refresh(report)
    return report
