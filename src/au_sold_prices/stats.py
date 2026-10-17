from collections.abc import Iterable
from statistics import median

from au_sold_prices.models import Sale


def median_price(sales: Iterable[Sale]) -> int | None:
    """Return the median in whole dollars, truncating fractional dollars."""
    prices = [sale.sold_price for sale in sales]
    return int(median(prices)) if prices else None
