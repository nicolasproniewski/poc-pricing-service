"""
BTC price fetching with cascading provider fallback.

Provider priority: CoinGecko → Kraken WS cache → Yahoo Finance

Each provider has an independent consecutive-failure counter. After 3 consecutive
failures, that provider is skipped for the current tick. The next tick always
starts from the highest-priority non-exhausted provider, so CoinGecko
self-heals automatically once it recovers.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.database import AsyncSessionLocal
from app.models.btc_price import BtcPrice
from app.providers.btc.base import BtcProvider, ProviderUnavailableError
from app.providers.btc.coingecko import CoinGeckoProvider
from app.providers.btc.kraken_ws import KrakenProvider
from app.providers.btc.yahoo import YahooProvider

logger = logging.getLogger(__name__)

FAILURE_THRESHOLD = 3


@dataclass
class _ProviderState:
    provider: BtcProvider
    consecutive_failures: int = field(default=0)

    @property
    def exhausted(self) -> bool:
        return self.consecutive_failures >= FAILURE_THRESHOLD


# Module-level state — resets on service restart (fine for POC)
_states: list[_ProviderState] = [
    _ProviderState(CoinGeckoProvider()),
    _ProviderState(KrakenProvider()),
    _ProviderState(YahooProvider()),
]


async def fetch_and_store() -> None:
    """Called by the scheduler every minute."""
    for state in _states:
        if state.exhausted:
            continue  # skip until a previous tick resets this provider

        provider = state.provider
        try:
            price = await provider.fetch()
        except (ProviderUnavailableError, Exception) as exc:
            state.consecutive_failures += 1
            logger.warning(
                "Provider '%s' failed (attempt %d/%d): %s",
                provider.name,
                state.consecutive_failures,
                FAILURE_THRESHOLD,
                exc,
            )
            if state.exhausted:
                logger.warning(
                    "Provider '%s' exhausted — switching to next provider",
                    provider.name,
                )
            continue

        # Success: reset this provider's counter and persist
        state.consecutive_failures = 0
        await _persist(price, provider.name)
        logger.debug("BTC price %.2f stored via %s", price, provider.name)
        return

    logger.critical(
        "All BTC providers exhausted — no price stored for this tick. "
        "Manual intervention may be required."
    )


async def _persist(price, source: str) -> None:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            session.add(
                BtcPrice(
                    price_usd=price,
                    source=source,
                    fetched_at=datetime.now(timezone.utc),
                )
            )
