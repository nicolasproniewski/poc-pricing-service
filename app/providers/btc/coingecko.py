import logging
from decimal import Decimal

import httpx

from app.config import settings
from app.providers.btc.base import BtcProvider, ProviderUnavailableError

logger = logging.getLogger(__name__)

_URL = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"


class CoinGeckoProvider(BtcProvider):
    name = "coingecko"

    async def fetch(self) -> Decimal:
        headers = {}
        if settings.coingecko_api_key:
            headers["x-cg-demo-api-key"] = settings.coingecko_api_key

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(_URL, headers=headers)
                response.raise_for_status()
                data = response.json()
                price = data["bitcoin"]["usd"]
                return Decimal(str(price))
        except Exception as exc:
            raise ProviderUnavailableError(f"CoinGecko failed: {exc}") from exc
