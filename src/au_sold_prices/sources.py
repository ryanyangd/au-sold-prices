from abc import ABC, abstractmethod
from collections.abc import Iterable

from au_sold_prices.models import Sale


class SalesSource(ABC):
    """Use licensed or open data; do not scrape sites whose terms forbid it."""

    @abstractmethod
    def fetch(self, suburb: str, state: str) -> Iterable[Sale]:
        """Return sales matching the suburb and state."""
        raise NotImplementedError


class InMemorySource(SalesSource):
    def __init__(self, sales: Iterable[Sale] = ()) -> None:
        self._sales = tuple(sales)

    def fetch(self, suburb: str, state: str) -> Iterable[Sale]:
        return (
            sale
            for sale in self._sales
            if sale.suburb.casefold() == suburb.casefold()
            and sale.state.casefold() == state.casefold()
        )
