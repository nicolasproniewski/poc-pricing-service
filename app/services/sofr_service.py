"""
SOFR rate fetching with NY Fed primary and FRED fallback.
Fetches overnight, 1m, and 3m tenors in a single cycle.
Upserts by (rate_date, rate_type) so re-runs are idempotent.
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
    rates, source = None, None

    # Primary: NY Fed
    try:
        rates = await nyfed.fetch_sofr()
        source = "nyfed"
        logger.info("Fetched %d SOFR tenor(s) from NY Fed", len(rates))
    except Exception as exc:
        logger.warning("NY Fed SOFR fetch failed: %s — trying FRED fallback", exc)

    # Fallback: FRED
    if rates is None:
        try:
            rates = await fred.fetch_sofr()
            source = "fred"
            logger.info("Fetched %d SOFR tenor(s) from FRED", len(rates))
        except Exception as exc:
            logger.critical(
                "Both SOFR providers failed. Last error: %s. No rate stored.", exc
            )
            return

    for rate_date, rate_pct, rate_type in rates:
        await _upsert(rate_date, rate_pct, rate_type, source)
        logger.debug("SOFR %s %.4f for %s stored via %s", rate_type, rate_pct, rate_date, source)


async def _upsert(rate_date, rate_pct, rate_type: str, source: str) -> None:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            stmt = insert(SofrRate).values(
                rate_date=rate_date,
                rate_type=rate_type,
                rate_pct=rate_pct,
                source=source,
                fetched_at=datetime.now(timezone.utc),
            )
            stmt = stmt.on_conflict_do_update(
                constraint="uq_sofr_rate_date_type",
                set_={
                    "rate_pct": stmt.excluded.rate_pct,
                    "source": stmt.excluded.source,
                    "fetched_at": stmt.excluded.fetched_at,
                },
            )
            await session.execute(stmt)
