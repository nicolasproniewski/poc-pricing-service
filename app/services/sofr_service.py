"""
SOFR rate fetching with NY Fed primary and FRED fallback.
Upserts by rate_date so re-runs are idempotent.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert

from app.database import AsyncSessionLocal
from app.models.sofr_rate import SofrRate
from app.providers.sofr import fred, nyfed

logger = logging.getLogger(__name__)


async def fetch_and_store() -> None:
    """Called by the scheduler on weekdays at 8:15am ET."""
    rate_date, rate_pct, source = None, None, None

    # Primary: NY Fed
    try:
        rate_date, rate_pct = await nyfed.fetch_sofr()
        source = "nyfed"
        logger.info("SOFR %.4f for %s fetched from NY Fed", rate_pct, rate_date)
    except Exception as exc:
        logger.warning("NY Fed SOFR fetch failed: %s — trying FRED fallback", exc)

    # Fallback: FRED
    if source is None:
        try:
            rate_date, rate_pct = await fred.fetch_sofr()
            source = "fred"
            logger.info("SOFR %.4f for %s fetched from FRED", rate_pct, rate_date)
        except Exception as exc:
            logger.critical(
                "Both SOFR providers failed. Last error: %s. No rate stored.", exc
            )
            return

    await _upsert(rate_date, rate_pct, source)


async def _upsert(rate_date, rate_pct, source: str) -> None:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            stmt = insert(SofrRate).values(
                rate_date=rate_date,
                rate_pct=rate_pct,
                source=source,
                fetched_at=datetime.now(timezone.utc),
            )
            stmt = stmt.on_conflict_do_update(
                constraint="uq_sofr_rate_date",
                set_={
                    "rate_pct": stmt.excluded.rate_pct,
                    "source": stmt.excluded.source,
                    "fetched_at": stmt.excluded.fetched_at,
                },
            )
            await session.execute(stmt)
