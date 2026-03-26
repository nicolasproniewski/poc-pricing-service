"""
FRED (St. Louis Fed) fallback SOFR provider.
Requires FRED_API_KEY in settings. Free to register at fred.stlouisfed.org.
Typically lags NY Fed by 1-3 hours — do not use as primary.

Series IDs:
  SOFR          → overnight
  SOFR30DAYAVG  → 1m
  SOFR90DAYAVG  → 3m
"""
import logging
from datetime import date
from decimal import Decimal

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_BASE_URL = (
    "https://api.stlouisfed.org/fred/series/observations"
    "?sort_order=desc&limit=1&file_type=json"
)

_SERIES = [
    ("SOFR", "overnight"),
    ("SOFR30DAYAVG", "1m"),
    ("SOFR90DAYAVG", "3m"),
]


async def fetch_sofr() -> list[tuple[date, Decimal, str]]:
    """
    Returns a list of (effective_date, rate_pct, rate_type) tuples.
    Raises on any failure.
    """
    if not settings.fred_api_key:
        raise ValueError("FRED_API_KEY is not configured")

    results: list[tuple[date, Decimal, str]] = []

    async with httpx.AsyncClient(timeout=10) as client:
        for series_id, rate_type in _SERIES:
            url = f"{_BASE_URL}&series_id={series_id}&api_key={settings.fred_api_key}"
            try:
                response = await client.get(url)
                response.raise_for_status()
                observations = response.json().get("observations", [])
                if not observations:
                    logger.warning("FRED returned empty observations for %s", series_id)
                    continue
                obs = observations[0]
                if obs.get("value") in (".", None):
                    logger.warning("FRED missing value for %s on %s", series_id, obs.get("date"))
                    continue
                results.append((
                    date.fromisoformat(obs["date"]),
                    Decimal(obs["value"]),
                    rate_type,
                ))
            except Exception as exc:
                logger.warning("FRED fetch failed for %s: %s", series_id, exc)

    if not results:
        raise ValueError("FRED returned no usable SOFR data")

    return results
