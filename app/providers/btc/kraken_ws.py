"""
Kraken public WebSocket provider.

A background coroutine (`run_kraken_ws`) maintains a persistent connection to
Kraken's public WS feed and caches the latest BTC/USD price. The `KrakenProvider`
class reads from this cache — it never opens its own connection.

Start `run_kraken_ws` as an asyncio task in the FastAPI lifespan.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal

import websockets

from app.providers.btc.base import BtcProvider, ProviderUnavailableError

logger = logging.getLogger(__name__)

_WS_URL = "wss://ws.kraken.com"
_SUBSCRIBE = {
    "event": "subscribe",
    "pair": ["XBT/USD"],
    "subscription": {"name": "ticker"},
}
_STALE_SECONDS = 120

# Shared cache written by the background task, read by KrakenProvider.fetch()
kraken_cache: dict = {"price": None, "updated_at": None}
_lock = asyncio.Lock()


async def run_kraken_ws() -> None:
    """Background coroutine — reconnects automatically on any failure."""
    while True:
        try:
            async with websockets.connect(_WS_URL) as ws:
                await ws.send(json.dumps(_SUBSCRIBE))
                logger.info("Kraken WS connected")
                async for raw in ws:
                    msg = json.loads(raw)
                    # Ticker messages are lists: [channelID, data, "ticker", "XBT/USD"]
                    if isinstance(msg, list) and len(msg) == 4 and msg[2] == "ticker":
                        price = float(msg[1]["c"][0])  # "c" = last trade close
                        async with _lock:
                            kraken_cache["price"] = price
                            kraken_cache["updated_at"] = datetime.now(timezone.utc)
        except asyncio.CancelledError:
            logger.info("Kraken WS task cancelled")
            return
        except Exception as exc:
            logger.warning("Kraken WS disconnected (%s), reconnecting in 5s", exc)
            await asyncio.sleep(5)


def kraken_ws_status() -> str:
    """Return 'live', 'stale', or 'disconnected' — used by /health."""
    updated_at = kraken_cache.get("updated_at")
    if updated_at is None:
        return "disconnected"
    age = (datetime.now(timezone.utc) - updated_at).total_seconds()
    return "live" if age <= _STALE_SECONDS else "stale"


class KrakenProvider(BtcProvider):
    name = "kraken"

    async def fetch(self) -> Decimal:
        async with _lock:
            price = kraken_cache.get("price")
            updated_at = kraken_cache.get("updated_at")

        if price is None:
            raise ProviderUnavailableError("Kraken cache is empty — WS not yet connected")

        age = (datetime.now(timezone.utc) - updated_at).total_seconds()
        if age > _STALE_SECONDS:
            raise ProviderUnavailableError(f"Kraken cache is stale ({age:.0f}s old)")

        return Decimal(str(price))
