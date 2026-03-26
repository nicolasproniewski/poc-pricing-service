"""
NY Fed primary SOFR provider.
No authentication required. Authoritative source.
Published ~8:00 a.m. ET on weekdays.

API docs: https://markets.newyorkfed.org/static/docs/markets-api.html
Endpoints:
  Overnight:  /api/rates/secured/sofr/last/{n}.json
  Averages:   /api/rates/secured/sofravgrates/last/{n}.json
"""
import logging
from datetime import date
from decimal import Decimal

import httpx

logger = logging.getLogger(__name__)

_OVERNIGHT_URL = "https://markets.newyorkfed.org/api/rates/secured/sofr/last/5.json"
# SOFRAI = SOFR Average Index — single record per date containing 30/90/180-day averages
_AVERAGES_URL = "https://markets.newyorkfed.org/api/rates/secured/sofrai/last/1.json"


async def fetch_sofr() -> list[tuple[date, Decimal, str]]:
    """
    Returns a list of (effective_date, rate_pct, rate_type) tuples.
    Always includes overnight; includes 1m and 3m averages if available.
    Raises on complete failure so the caller can fall back to FRED.
    """
    results: list[tuple[date, Decimal, str]] = []

    async with httpx.AsyncClient(timeout=10) as client:
        # Overnight
        response = await client.get(_OVERNIGHT_URL)
        response.raise_for_status()
        rates = response.json().get("refRates", [])
        if not rates:
            raise ValueError("NY Fed returned no overnight SOFR entries")
        latest = rates[0]
        results.append((
            date.fromisoformat(latest["effectiveDate"]),
            Decimal(str(latest["percentRate"])),
            "overnight",
        ))

        # Averages — single SOFRAI record contains average30day and average90day
        try:
            avg_response = await client.get(_AVERAGES_URL)
            avg_response.raise_for_status()
            avg_rates = avg_response.json().get("refRates", [])
            if avg_rates:
                entry = avg_rates[0]
                effective_date = date.fromisoformat(entry["effectiveDate"])
                results.append((effective_date, Decimal(str(entry["average30day"])), "1m"))
                results.append((effective_date, Decimal(str(entry["average90day"])), "3m"))
        except Exception as exc:
            logger.warning("NY Fed averages fetch failed (overnight still stored): %s", exc)

    return results
