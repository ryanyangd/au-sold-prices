import argparse

from au_sold_prices import __version__
from au_sold_prices.sources import InMemorySource
from au_sold_prices.stats import median_price


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ausold")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    median_parser = subparsers.add_parser("median", help="Show a suburb's median sold price")
    median_parser.add_argument("suburb")
    median_parser.add_argument("state")
    args = parser.parse_args(argv)

    # TODO: Replace with a real licensed or open data source.
    source = InMemorySource()
    price = median_price(source.fetch(args.suburb, args.state))
    print(f"${price:,}" if price is not None else "No data available")
    return 0
