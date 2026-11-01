from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from kinfold_api.config import get_settings
from kinfold_api.db import get_db
from kinfold_api.schemas.data_stats import DataStatsOut
from kinfold_api.services.data_export import compute_preference_pairs

router = APIRouter(tags=["data"])


@router.get("/data/stats", response_model=DataStatsOut)
def read_data_stats(db: Session = Depends(get_db)) -> DataStatsOut:
    """Live count, not a cached/stale number — computed from the exact same
    eligibility rules the real export uses (kinfold_api.services.data_export),
    so this page can never show a different number than an actual export
    run would produce."""
    _pairs, manifest = compute_preference_pairs(db)
    return DataStatsOut(
        open_weight_preference_pairs=manifest.pair_count,
        target_for_first_training_run=get_settings().KINFOLD_FIRST_TRAINING_RUN_TARGET_PAIRS,
        as_of=datetime.now(UTC),
    )
