from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class BtcPriceOut(BaseModel):
    price_usd: Decimal
    source: str
    fetched_at: datetime

    model_config = {"from_attributes": True}


class BtcPriceHistory(BaseModel):
    count: int
    items: list[BtcPriceOut]
