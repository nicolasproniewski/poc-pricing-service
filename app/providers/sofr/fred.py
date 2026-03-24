"""
FRED (St. Louis Fed) fallback SOFR provider.
Requires FRED_API_KEY in settings. Free to register at fred.stlouisfed.org.
Typically lags NY Fed by 1-3 hours — do not use as primary.
"""
import logging
from datetime import date
from decimal import Decimal

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_URL = (
    "https://api.stlouisfed.org/fred/series/observations"
    "?series_id=SOFR&sort_order=desc&limit=1&file_type=json"
)


async def fetch_sofr() -> tuple[date, Decimal]:
    """
    Returns (effective_date, rate_pct) from FRED.
    Raises on any failure.
    """
    if not settings.fred_api_key:
        raise ValueError("FRED_API_KEY is not configured")

    url = f"{_URL}&api_key={settings.fred_api_key}"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

    observations = data.get("observations", [])
    if not observations:
        raise ValueError("FRED returned empty observations list")

    obs = observations[0]
    if obs.get("value") in (".", None):
        raise ValueError(f"FRED returned a missing value for date {obs.get('date')}")

    effective_date = date.fromisoformat(obs["date"])
    rate_pct = Decimal(obs["value"])
    return effective_date, rate_pct
