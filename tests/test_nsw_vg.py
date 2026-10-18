import io
import zipfile
from datetime import date

import pytest

from au_sold_prices import cli
from au_sold_prices.models import Sale
from au_sold_prices.nsw_vg import NswValuerGeneralSource, parse_line, parse_lines
from au_sold_prices.sources import SalesSource


def b_row(
    *,
    district="001",
    prop_id="1001",
    unit="",
    house="1",
    street="EXAMPLE STREET",
    locality="EXAMPLEVILLE",
    postcode="2000",
    contract="20260105",
    settlement="20260201",
    price="800000",
    nature="R",
    strata="",
):
    fields = [
        "B", district, prop_id, "1", "202601100000", "", unit, house, street,
        locality, postcode, "500", "M", contract, settlement, price, "R2",
        nature, "RESIDENCE", strata, "", "", "100", "AA000001",
    ]  # fmt: skip
    return ";".join(fields) + ";"


def make_zip(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def test_parse_line_maps_sale_fields():
    sale = parse_line(b_row(house="12", street="SAMPLE ROAD", locality="TESTTOWN"))
    assert sale == Sale(
        "12 Sample Road", "Testtown", "NSW", "2000", 800_000, date(2026, 1, 5), "house"
    )


def test_parse_line_unit_address_and_type():
    sale = parse_line(b_row(unit="3", house="12", strata="3"))
    assert sale is not None
    assert sale.address == "3/12 Example Street"
    assert sale.property_type == "unit"


@pytest.mark.parametrize(
    ("nature", "expected"), [("R", "house"), ("V", "vacant land"), ("3", "other")]
)
def test_parse_line_property_type(nature, expected):
    assert parse_line(b_row(nature=nature)).property_type == expected


def test_parse_line_falls_back_to_settlement_date():
    sale = parse_line(b_row(contract=""))
    assert sale is not None
    assert sale.sold_date == date(2026, 2, 1)


@pytest.mark.parametrize(
    "line",
    [
        "A;RTSALES;20260110;",
        "Z;1;2;3",
        "",
        "B;too;short",
        b_row(price=""),
        b_row(price="0"),
        b_row(price="12.5"),
        b_row(contract="", settlement=""),
        b_row(contract="notadate", settlement=""),
        b_row(locality=""),
    ],
)
def test_parse_line_skips_unusable_rows(line):
    assert parse_line(line) is None


def test_parse_line_handles_line_endings():
    assert parse_line(b_row() + "\r\n") is not None


def test_parse_lines_drops_duplicates():
    rows = [b_row(), b_row(), b_row(prop_id="1002"), b_row(price="900000")]
    assert len(list(parse_lines(rows))) == 3


def test_source_reads_nested_zip_and_loose_dat(tmp_path):
    weekly = make_zip({"week1.DAT": "\n".join(["A;HEADER", b_row(price="700000")]) + "\n"})
    annual = make_zip({"week1.zip": weekly, "readme.txt": "ignored"})
    (tmp_path / "annual.zip").write_bytes(annual)
    (tmp_path / "loose.dat").write_text(b_row(prop_id="2002", price="900000") + "\r\n")
    (tmp_path / "bad.zip").write_bytes(b"not a zip")
    (tmp_path / "notes.txt").write_text(b_row(prop_id="3003"))

    source = NswValuerGeneralSource(tmp_path)

    assert isinstance(source, SalesSource)
    prices = sorted(s.sold_price for s in source.fetch("exampleville", "nsw"))
    assert prices == [700_000, 900_000]


def test_source_filters_suburb_and_state(tmp_path):
    rows = [b_row(locality="ALPHA"), b_row(prop_id="1002", locality="BETA")]
    (tmp_path / "a.zip").write_bytes(make_zip({"a.DAT": "\n".join(rows)}))
    source = NswValuerGeneralSource(tmp_path)

    assert [s.suburb for s in source.fetch("Alpha", "NSW")] == ["Alpha"]
    assert list(source.fetch("Alpha", "VIC")) == []
    assert list(source.fetch("Gamma", "NSW")) == []


def test_source_missing_directory(tmp_path):
    source = NswValuerGeneralSource(tmp_path / "missing")
    assert list(source.fetch("Alpha", "NSW")) == []


def test_cli_median_uses_nsw_data_and_filters_house(tmp_path, capsys):
    rows = [
        b_row(prop_id="1", price="700000"),
        b_row(prop_id="2", price="900000"),
        b_row(prop_id="3", price="1000000", unit="1", strata="1"),
        b_row(prop_id="4", price="100000", nature="V"),
    ]
    (tmp_path / "sales.zip").write_bytes(make_zip({"s.DAT": "\n".join(rows)}))
    data_dir = str(tmp_path)

    assert cli.main(["median", "Exampleville", "NSW", "--data-dir", data_dir]) == 0
    assert capsys.readouterr().out == "$800,000\n"

    argv = ["median", "Exampleville", "NSW", "--data-dir", data_dir, "--property-type", "unit"]
    assert cli.main(argv) == 0
    assert capsys.readouterr().out == "$1,000,000\n"


def test_cli_median_nsw_without_data(tmp_path, capsys):
    argv = ["median", "Exampleville", "NSW", "--data-dir", str(tmp_path / "none")]
    assert cli.main(argv) == 0
    assert capsys.readouterr().out == "No data available\n"


CSV_HEADER = [
    "District code", "Property ID", "Property unit number", "Property house number",
    "Property street name", "Property locality", "Property post code", "Contract date",
    "Settlement date", "Purchase price", "Nature of property", "Strata lot number",
    "Dealing number", "Part interest flag", "Non-market price flag", "Date error flag",
]  # fmt: skip


def csv_text(*rows):
    def line(values):
        return ",".join(f'"{v}"' for v in values)

    return "\n".join([line(CSV_HEADER), *(line(r) for r in rows)]) + "\n"


def csv_row(prop_id="1", price="800000.0", locality="Exampleville", **over):
    values = {
        "District code": "001", "Property ID": prop_id, "Property unit number": "",
        "Property house number": "5", "Property street name": "Sample Rd",
        "Property locality": locality, "Property post code": "2000",
        "Contract date": "2026-01-05", "Settlement date": "2026-02-01",
        "Purchase price": price, "Nature of property": "R", "Strata lot number": "",
        "Dealing number": "AA1", "Part interest flag": "False",
        "Non-market price flag": "False", "Date error flag": "False",
    }  # fmt: skip
    values.update(over)
    return [values[h] for h in CSV_HEADER]


def test_source_reads_csv_inside_zip_and_loose(tmp_path):
    (tmp_path / "a.zip").write_bytes(make_zip({"d.csv": csv_text(csv_row("1", "700000.0"))}))
    (tmp_path / "loose.csv").write_text(csv_text(csv_row("2", "900000"), csv_row("1", "700000")))

    sales = list(NswValuerGeneralSource(tmp_path).fetch("EXAMPLEVILLE", "NSW"))

    assert sorted(s.sold_price for s in sales) == [700_000, 900_000]
    first = sales[0]
    assert (first.address, first.suburb, first.postcode, first.sold_date) == (
        "5 Sample Rd", "Exampleville", "2000", date(2026, 1, 5),
    )  # fmt: skip


def test_csv_skips_flagged_and_invalid_rows(tmp_path):
    rows = [
        csv_row("1"),
        csv_row("2", **{"Part interest flag": "True"}),
        csv_row("3", **{"Non-market price flag": "True"}),
        csv_row("4", **{"Date error flag": "True"}),
        csv_row("5", price="abc"),
        csv_row("6", price="0"),
        csv_row("7", **{"Contract date": "", "Settlement date": ""}),
        csv_row("8", locality=""),
    ]
    (tmp_path / "s.csv").write_text(csv_text(*rows))

    sales = list(NswValuerGeneralSource(tmp_path).fetch("Exampleville", "NSW"))

    assert len(sales) == 1


def test_csv_unit_and_type(tmp_path):
    row = csv_row("1", **{"Property unit number": "3", "Strata lot number": "3"})
    (tmp_path / "s.csv").write_text(csv_text(row, csv_row("2", **{"Nature of property": "V"})))

    types = {s.address: s.property_type for s in NswValuerGeneralSource(tmp_path).fetch("Exampleville", "NSW")}

    assert types == {"3/5 Sample Rd": "unit", "5 Sample Rd": "vacant land"}
