from abc import ABC, abstractmethod
from decimal import Decimal


class ProviderUnavailableError(Exception):
    """Raised when a provider cannot return a price."""


class BtcProvider(ABC):
    name: str

    @abstractmethod
    async def fetch(self) -> Decimal:
        """Return the current BTC/USD price."""
