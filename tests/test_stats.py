from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from au_sold_prices.models import Sale
from au_sold_prices.sources import InMemorySource, SalesSource
from au_sold_prices.stats import median_price


def make_sale(price, suburb="Richmond", state="VIC"):
    return Sale("1 Example St", suburb, state, "3121", price, date(2026, 1, 1))


@pytest.mark.parametrize(
    ("prices", "expected"),
    [
        ([900_000, 750_000, 850_000], 850_000),
        ([900_000, 800_000], 850_000),
        ([800_000, 800_001], 800_000),
        ([850_000], 850_000),
        ([], None),
    ],
)
def test_median_price(prices, expected):
    assert median_price(make_sale(price) for price in prices) == expected


def test_median_empty_list():
    assert median_price([]) is None


def test_in_memory_source_filtering():
    matching = make_sale(850_000, "rIcHmOnD", "vIc")
    source = InMemorySource(iter([
        matching,
        make_sale(900_000, state="NSW"),
        make_sale(750_000, suburb="Carlton"),
    ]))

    assert isinstance(source, SalesSource)
    assert list(source.fetch("RICHMOND", "VIC")) == [matching]
    assert list(source.fetch("richmond", "vic")) == [matching]
    assert list(source.fetch("Unknown", "VIC")) == []


def test_sale_is_frozen_and_defaults_to_house():
    sale = make_sale(850_000)
    assert sale.property_type == "house"
    with pytest.raises(FrozenInstanceError):
        sale.sold_price = 900_000
