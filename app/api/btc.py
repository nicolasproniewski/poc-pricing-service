from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.btc_price import BtcPrice
from app.schemas.btc_price import BtcPriceHistory, BtcPriceOut

router = APIRouter(prefix="/btc", tags=["btc"])


@router.get("/latest", response_model=BtcPriceOut)
async def get_btc_latest(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BtcPrice).order_by(desc(BtcPrice.fetched_at)).limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="No BTC price data available yet")
    return row


@router.get("/history", response_model=BtcPriceHistory)
async def get_btc_history(
    limit: int = Query(default=60, ge=1, le=1440),
    since: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    query = select(BtcPrice).order_by(desc(BtcPrice.fetched_at)).limit(limit)
    if since is not None:
        query = query.where(BtcPrice.fetched_at >= since)

    result = await db.execute(query)
    rows = result.scalars().all()
    return BtcPriceHistory(count=len(rows), items=rows)
