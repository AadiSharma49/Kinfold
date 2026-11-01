from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DataStatsOut(BaseModel):
    open_weight_preference_pairs: int
    target_for_first_training_run: int
    as_of: datetime
