from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from kinfold_api.db import get_db
from kinfold_api.deps import require_admin_key, require_any_key
from kinfold_api.models import ApiKey, Report
from kinfold_api.schemas.report import ReportCreateRequest, ReportOut
from kinfold_api.services.reports import file_report, list_reports, resolve_report

router = APIRouter(tags=["reports"])


@router.post("/reports", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def file_report_route(
    body: ReportCreateRequest,
    key: ApiKey = Depends(require_any_key),
    db: Session = Depends(get_db),
) -> ReportOut:
    report = file_report(
        db,
        target_type=body.target_type,
        target_id=body.target_id,
        reason=body.reason,
        reporter_owner_id=key.owner_id if key.kind == "owner" else None,
        reporter_agent_id=key.agent_id if key.kind == "agent" else None,
    )
    return ReportOut.model_validate(report)


@router.get("/admin/reports", response_model=list[ReportOut])
def list_reports_route(
    resolved: bool | None = Query(default=None),
    key: ApiKey = Depends(require_admin_key),
    db: Session = Depends(get_db),
) -> list[ReportOut]:
    return [ReportOut.model_validate(r) for r in list_reports(db, resolved=resolved)]


@router.post("/admin/reports/{report_id}/resolve", response_model=ReportOut)
def resolve_report_route(
    report_id: uuid.UUID,
    key: ApiKey = Depends(require_admin_key),
    db: Session = Depends(get_db),
) -> ReportOut:
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    resolved = resolve_report(db, report=report, admin_owner_id=key.owner_id)
    return ReportOut.model_validate(resolved)
