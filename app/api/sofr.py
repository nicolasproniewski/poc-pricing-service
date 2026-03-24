from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.sofr_rate import SofrRate
from app.schemas.sofr_rate import SofrRateHistory, SofrRateOut

router = APIRouter(prefix="/sofr", tags=["sofr"])


@router.get("/latest", response_model=SofrRateOut)
async def get_sofr_latest(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SofrRate).order_by(desc(SofrRate.rate_date)).limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="No SOFR rate data available yet")
    return row


@router.get("/history", response_model=SofrRateHistory)
async def get_sofr_history(
    limit: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SofrRate).order_by(desc(SofrRate.rate_date)).limit(limit)
    )
    rows = result.scalars().all()
    return SofrRateHistory(count=len(rows), items=rows)
