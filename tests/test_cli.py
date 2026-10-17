from datetime import date

import pytest

from au_sold_prices import __version__, cli
from au_sold_prices.models import Sale
from au_sold_prices.sources import InMemorySource


def test_median_no_data(capsys):
    assert cli.main(["median", "Richmond", "VIC"]) == 0
    assert capsys.readouterr().out == "No data available\n"


@pytest.mark.parametrize("price", [850_000, 0])
def test_median_formatted_price(monkeypatch, capsys, price):
    source = InMemorySource([
        Sale("1 Example St", "Richmond", "VIC", "3121", price, date(2026, 1, 1)),
    ])
    monkeypatch.setattr(cli, "InMemorySource", lambda: source)

    assert cli.main(["median", "Richmond", "VIC"]) == 0
    assert capsys.readouterr().out == f"${price:,}\n"


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out == f"ausold {__version__}\n"


@pytest.mark.parametrize("argv", [[], ["median", "Richmond"], ["unknown"]])
def test_invalid_arguments(argv):
    with pytest.raises(SystemExit) as exc:
        cli.main(argv)
    assert exc.value.code == 2
