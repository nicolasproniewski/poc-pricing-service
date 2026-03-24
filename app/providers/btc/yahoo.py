"""
Yahoo Finance fallback provider (true last resort).

Uses yfinance which scrapes Yahoo Finance. It is slower than the other providers
and should only be called when both CoinGecko and Kraken have exhausted their
failure budgets.
"""
import logging
from decimal import Decimal

import yfinance as yf

from app.providers.btc.base import BtcProvider, ProviderUnavailableError

logger = logging.getLogger(__name__)


class YahooProvider(BtcProvider):
    name = "yahoo"

    async def fetch(self) -> Decimal:
        try:
            # yfinance is synchronous — acceptable for a last-resort provider
            ticker = yf.Ticker("BTC-USD")
            data = ticker.fast_info
            price = data.last_price
            if price is None or price <= 0:
                raise ValueError("Invalid price returned")
            return Decimal(str(price))
        except Exception as exc:
            raise ProviderUnavailableError(f"Yahoo Finance failed: {exc}") from exc
