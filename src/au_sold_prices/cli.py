import argparse
import os
import sys
from pathlib import Path

from au_sold_prices import __version__
from au_sold_prices.nsw_download import DownloadError, run_if_due
from au_sold_prices.nsw_vg import NswValuerGeneralSource
from au_sold_prices.sources import InMemorySource, SalesSource
from au_sold_prices.stats import median_price


def _select_source(state: str, data_dir: Path) -> SalesSource:
    if state.casefold() == "nsw":
        return NswValuerGeneralSource(data_dir)
    # TODO: Add sources for other states once their licences are checked.
    return InMemorySource()


def _download_nsw(data_dir: Path, force: bool) -> int:
    try:
        result = run_if_due(data_dir, force=force)
    except DownloadError as exc:
        print(f"NSW download failed: {exc}", file=sys.stderr)
        return 1
    if result is None:
        print("NSW data check not due yet.")
        return 0
    action = "Downloaded" if result.downloaded else "Already up to date:"
    print(f"{action} {result.filename} (source updated {result.source_last_modified:%Y-%m-%d})")
    if result.stale:
        print("Warning: the source has not been updated for over 14 days.", file=sys.stderr)
    return 0


def _missing_extra(extra: str, exc: ImportError) -> int:
    print(f"Missing dependency ({exc.name}). Install with: pip install '.[{extra}]'", file=sys.stderr)
    return 1


def _build_gold(data_dir: Path, db: Path) -> int:
    try:
        from au_sold_prices.pipeline.local import build_local

        as_of = build_local(data_dir, db)
    except ImportError as exc:
        return _missing_extra("pipeline", exc)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built gold tables in {db} (data as of {as_of})")
    return 0


def _load_postgres(db: Path, database_url: str) -> int:
    if not database_url:
        print("Set --database-url or DATABASE_URL.", file=sys.stderr)
        return 1
    try:
        from au_sold_prices.pipeline.serving import load_postgres

        counts = load_postgres(db, database_url)
    except ImportError as exc:
        return _missing_extra("pipeline", exc)
    print("Loaded: " + ", ".join(f"{table}={n:,}" for table, n in counts.items()))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ausold")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    median_parser = subparsers.add_parser("median", help="Show a suburb's median sold price")
    median_parser.add_argument("suburb")
    median_parser.add_argument("state")
    median_parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="directory with local NSW Valuer General ZIP/.DAT files (default: ./data)",
    )
    median_parser.add_argument(
        "--property-type",
        default="house",
        help="property type to include, e.g. house or unit (default: house)",
    )
    download_parser = subparsers.add_parser(
        "download-nsw", help="Download the latest cleaned NSW sales archive"
    )
    download_parser.add_argument("--data-dir", type=Path, default=Path("data"))
    download_parser.add_argument(
        "--force", action="store_true", help="run even if a refresh is not yet due"
    )
    gold_parser = subparsers.add_parser(
        "build-gold", help="Build bronze/silver/gold tables locally with DuckDB"
    )
    gold_parser.add_argument("--data-dir", type=Path, default=Path("data"))
    gold_parser.add_argument("--db", type=Path, default=Path("data") / "lake.duckdb")
    load_parser = subparsers.add_parser(
        "load-postgres", help="Load local gold tables into the Postgres serving schema"
    )
    load_parser.add_argument("--db", type=Path, default=Path("data") / "lake.duckdb")
    load_parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""))
    args = parser.parse_args(argv)

    if args.command == "download-nsw":
        return _download_nsw(args.data_dir, args.force)
    if args.command == "build-gold":
        return _build_gold(args.data_dir, args.db)
    if args.command == "load-postgres":
        return _load_postgres(args.db, args.database_url)

    source = _select_source(args.state, args.data_dir)
    wanted_type = args.property_type.casefold()
    price = median_price(
        sale
        for sale in source.fetch(args.suburb, args.state)
        if sale.property_type.casefold() == wanted_type
    )
    print(f"${price:,}" if price is not None else "No data available")
    return 0
