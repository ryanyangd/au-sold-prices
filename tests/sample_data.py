"""Synthetic rows in the cleaned-CSV layout. No real data."""

import csv
from pathlib import Path

HEADER = [
    "District code", "Property ID", "Valuation number", "Sale counter", "Download date / time",
    "Property name", "Property unit number", "Property house number", "Property street name",
    "Property locality", "Property post code", "Area (m2)", "Area (source)",
    "Area type (source)", "Dimensions", "Contract date", "Settlement date", "Purchase price",
    "Zoning", "Nature of property", "Nature of property (description)", "Primary purpose",
    "Primary purpose (normalised)", "Strata lot number", "Component code", "Sale code",
    "% Interest of sale", "Dealing number", "Parcels in sale", "Property legal description",
    "Part interest flag", "Non-market price flag", "Date error flag",
]  # fmt: skip


def make_row(prop_id="1", contract="2026-01-01", price="500000", **over):
    row = dict.fromkeys(HEADER, "")
    row.update({
        "District code": "001", "Property ID": prop_id, "Sale counter": "1",
        "Download date / time": "2026-07-01 00:00:00", "Property house number": "5",
        "Property street name": "Sample Rd", "Property locality": "Exampleville",
        "Property post code": "2000", "Area (m2)": "600.0", "Contract date": contract,
        "Settlement date": "", "Purchase price": price, "Zoning": "R2",
        "Nature of property": "R", "Nature of property (description)": "Residence",
        "Dealing number": f"AA{prop_id}-{contract}", "Parcels in sale": "1",
        "Property legal description": f"1/{prop_id}", "Part interest flag": "False",
        "Non-market price flag": "False", "Date error flag": "False",
    })  # fmt: skip
    row.update(over)
    return row


def write_csv(path: Path, rows) -> Path:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=HEADER, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)
    return path


def scenario_rows():
    return [
        make_row("1", "2019-03-01", "500000"),
        make_row("1", "2026-03-01", "700000"),
        make_row("2", "2026-01-15", "800000"),
        make_row("2", "2026-01-15", "800000"),  # exact duplicate
        make_row("3", "2026-06-30", "900000"),
        make_row("4", "2025-02-01", "600000"),
        make_row("5", "2025-03-01", "700000"),
        make_row("6", "2026-02-01", "100000", **{"Part interest flag": "True"}),
        make_row("7", "2026-02-01", "100000", **{"Non-market price flag": "True"}),
        make_row("8", "2026-02-01", "2000000", **{"Parcels in sale": "2"}),
        make_row("9", "2026-02-01", "5000"),
        make_row(
            "10", "2026-02-02", "400000",
            **{"Property unit number": "3", "Property house number": "12", "Strata lot number": "5"},
        ),
        make_row("11", "2026-02-03", "650000", **{"Property locality": "Otherville"}),
        make_row("12", "2026-02-03", ""),  # rejected: no price
        make_row("13", "", ""),  # rejected: no price/date
        make_row("14", "2026-02-03", "300000", **{"Property locality": ""}),  # rejected: suburb
        make_row("15", "", "450000", **{"Settlement date": "2026-02-20"}),  # settlement fallback
    ]
