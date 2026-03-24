from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class SofrRateOut(BaseModel):
    rate_date: date
    rate_pct: Decimal
    source: str
    fetched_at: datetime

    model_config = {"from_attributes": True}


class SofrRateHistory(BaseModel):
    count: int
    items: list[SofrRateOut]
