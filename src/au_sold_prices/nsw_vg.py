"""Readers for local NSW property sales files.

Two formats are supported, loose or inside ZIPs (ZIPs may be nested):

* NSW Valuer General bulk ``.DAT`` files: semicolon-delimited, no header. Only
  ``B`` (sales) records are used. Column positions follow the published layout
  as understood so far and should be checked against the official data
  dictionary.
* A cleaned ``.csv`` export with a header row (e.g. from nswpropertysalesdata.com).

Source data is licensed by the NSW Government; keep it local and do not
redistribute it.
"""

import csv
import io
import zipfile
from collections.abc import Iterable, Iterator
from datetime import date, datetime
from pathlib import Path
from typing import IO

from au_sold_prices.models import Sale
from au_sold_prices.sources import SalesSource

STATE = "NSW"
DELIMITER = ";"
SALE_RECORD = "B"
MAX_ZIP_DEPTH = 3

DISTRICT = 1
PROPERTY_ID = 2
UNIT_NUMBER = 6
HOUSE_NUMBER = 7
STREET_NAME = 8
LOCALITY = 9
POSTCODE = 10
CONTRACT_DATE = 13
SETTLEMENT_DATE = 14
PRICE = 15
NATURE_OF_PROPERTY = 17
STRATA_LOT = 19
DEALING_NUMBER = 23
MIN_FIELDS = STRATA_LOT + 1

CSV_FLAGS_TO_SKIP = ("Part interest flag", "Non-market price flag", "Date error flag")

Record = tuple[tuple[str, ...], Sale]


def _field(fields: list[str], index: int) -> str:
    return fields[index].strip() if index < len(fields) else ""


def _parse_date(value: str, fmt: str = "%Y%m%d") -> date | None:
    try:
        return datetime.strptime(value, fmt).date()
    except ValueError:
        return None


def _property_type(nature: str, strata_lot: str) -> str:
    nature = nature.upper()
    if nature == "R":
        return "unit" if strata_lot else "house"
    if nature == "V":
        return "vacant land"
    return "other"


def _join_address(unit: str, house: str, street: str) -> str:
    number = f"{unit}/{house}" if unit and house else unit or house
    return f"{number} {street}".strip()


def _parse_dat_record(line: str) -> Record | None:
    fields = line.rstrip("\r\n").split(DELIMITER)
    if _field(fields, 0).upper() != SALE_RECORD or len(fields) < MIN_FIELDS:
        return None

    price_text = _field(fields, PRICE)
    if not price_text.isdigit() or int(price_text) <= 0:
        return None
    sold_date = _parse_date(_field(fields, CONTRACT_DATE)) or _parse_date(
        _field(fields, SETTLEMENT_DATE)
    )
    suburb = _field(fields, LOCALITY).title()
    if sold_date is None or not suburb:
        return None

    unit = _field(fields, UNIT_NUMBER)
    strata = _field(fields, STRATA_LOT)
    sale = Sale(
        address=_join_address(
            unit, _field(fields, HOUSE_NUMBER), _field(fields, STREET_NAME).title()
        ),
        suburb=suburb,
        state=STATE,
        postcode=_field(fields, POSTCODE),
        sold_price=int(price_text),
        sold_date=sold_date,
        property_type=_property_type(_field(fields, NATURE_OF_PROPERTY), strata),
    )
    key = (
        _field(fields, DISTRICT),
        _field(fields, PROPERTY_ID),
        sold_date.isoformat(),
        price_text,
        unit,
        strata,
        _field(fields, DEALING_NUMBER),
    )
    return key, sale


def _parse_csv_record(row: dict[str, str]) -> Record | None:
    if any(row.get(flag, "").strip().lower() == "true" for flag in CSV_FLAGS_TO_SKIP):
        return None
    try:
        price = int(float(row.get("Purchase price", "").strip()))
    except ValueError:
        return None
    sold_date = _parse_date(row.get("Contract date", "").strip(), "%Y-%m-%d") or _parse_date(
        row.get("Settlement date", "").strip(), "%Y-%m-%d"
    )
    suburb = row.get("Property locality", "").strip()
    if price <= 0 or sold_date is None or not suburb:
        return None

    unit = row.get("Property unit number", "").strip()
    strata = row.get("Strata lot number", "").strip()
    sale = Sale(
        address=_join_address(
            unit,
            row.get("Property house number", "").strip(),
            row.get("Property street name", "").strip(),
        ),
        suburb=suburb,
        state=STATE,
        postcode=row.get("Property post code", "").strip(),
        sold_price=price,
        sold_date=sold_date,
        property_type=_property_type(row.get("Nature of property", "").strip(), strata),
    )
    key = (
        row.get("District code", "").strip(),
        row.get("Property ID", "").strip(),
        sold_date.isoformat(),
        str(price),
        unit,
        strata,
        row.get("Dealing number", "").strip(),
    )
    return key, sale


def parse_line(line: str) -> Sale | None:
    """Convert one ``.DAT`` line to a Sale, or None if it is not a usable sale."""
    record = _parse_dat_record(line)
    return record[1] if record else None


def _iter_dat(stream: IO[bytes]) -> Iterator[Record]:
    for line in io.TextIOWrapper(stream, encoding="utf-8", errors="replace", newline=""):
        record = _parse_dat_record(line)
        if record:
            yield record


def _iter_csv(stream: IO[bytes]) -> Iterator[Record]:
    text = io.TextIOWrapper(stream, encoding="utf-8-sig", errors="replace", newline="")
    for row in csv.DictReader(text):
        record = _parse_csv_record(row)
        if record:
            yield record


def _iter_file(name: str, stream: IO[bytes]) -> Iterator[Record]:
    lower = name.lower()
    if lower.endswith(".dat"):
        yield from _iter_dat(stream)
    elif lower.endswith(".csv"):
        yield from _iter_csv(stream)


def _iter_zip(archive: zipfile.ZipFile, depth: int) -> Iterator[Record]:
    for name in sorted(archive.namelist()):
        lower = name.lower()
        if lower.endswith((".dat", ".csv")):
            with archive.open(name) as stream:
                yield from _iter_file(name, stream)
        elif lower.endswith(".zip") and depth < MAX_ZIP_DEPTH:
            with archive.open(name) as stream:
                data = io.BytesIO(stream.read())
            try:
                with zipfile.ZipFile(data) as nested:
                    yield from _iter_zip(nested, depth + 1)
            except zipfile.BadZipFile:
                continue


def iter_records(data_dir: Path) -> Iterator[Record]:
    """Yield (dedupe key, Sale) for every usable sale under ``data_dir``."""
    if not data_dir.is_dir():
        return
    for path in sorted(data_dir.rglob("*")):
        if not path.is_file():
            continue
        lower = path.name.lower()
        if lower.endswith((".dat", ".csv")):
            with path.open("rb") as stream:
                yield from _iter_file(path.name, stream)
        elif lower.endswith(".zip"):
            try:
                with zipfile.ZipFile(path) as archive:
                    yield from _iter_zip(archive, 1)
            except zipfile.BadZipFile:
                continue


def _dedupe(records: Iterable[Record]) -> Iterator[Sale]:
    seen: set[int] = set()
    for key, sale in records:
        digest = hash(key)
        if digest in seen:
            continue
        seen.add(digest)
        yield sale


def parse_lines(lines: Iterable[str]) -> Iterator[Sale]:
    """Parse sales from ``.DAT`` lines, dropping repeated records."""
    records = (r for r in map(_parse_dat_record, lines) if r)
    return _dedupe(records)


class NswValuerGeneralSource(SalesSource):
    """Reads NSW sales from files in a local directory."""

    def __init__(self, data_dir: Path | str = "data") -> None:
        self._data_dir = Path(data_dir)

    def fetch(self, suburb: str, state: str) -> Iterable[Sale]:
        if state.casefold() != STATE.casefold():
            return iter(())
        wanted = suburb.casefold()
        matching = (r for r in iter_records(self._data_dir) if r[1].suburb.casefold() == wanted)
        return _dedupe(matching)
