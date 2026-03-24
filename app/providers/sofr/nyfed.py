"""
NY Fed primary SOFR provider.
No authentication required. Authoritative source.
Published ~8:00 a.m. ET on weekdays.

API docs: https://markets.newyorkfed.org/static/docs/markets-api.html
Endpoint: /api/ref-rates/secured/last/{n}.json
"""
import logging
from datetime import date
from decimal import Decimal

import httpx

logger = logging.getLogger(__name__)

# Returns the most recent N SOFR records. Using 5 ensures we always get
# the latest published rate even if today's hasn't been released yet.
_URL = "https://markets.newyorkfed.org/api/rates/secured/sofr/last/5.json"


async def fetch_sofr() -> tuple[date, Decimal]:
    """
    Returns (effective_date, rate_pct) from the NY Fed.
    Raises on any failure so the caller can fall back to FRED.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(_URL)
        response.raise_for_status()
        data = response.json()

    rates = data.get("refRates", [])
    if not rates:
        raise ValueError("NY Fed returned no SOFR entries")

    latest = rates[0]
    effective_date = date.fromisoformat(latest["effectiveDate"])
    rate_pct = Decimal(str(latest["percentRate"]))
    return effective_date, rate_pct
