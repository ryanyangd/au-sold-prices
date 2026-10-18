"""Run the bronze -> silver -> gold pipeline locally with DuckDB (needs `pip install .[pipeline]`)."""

import re
import tempfile
import zipfile
from datetime import date, datetime
from pathlib import Path

from au_sold_prices.nsw_download import FILE_PREFIX
from au_sold_prices.pipeline.runner import Schemas, run_gold, run_silver

SCHEMAS = Schemas()


def snake_case(name: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^0-9a-z]+", "_", name.lower())).strip("_")


def find_source(data_dir: Path) -> Path:
    """Newest cleaned-CSV source in ``data_dir`` (a downloaded ZIP or a loose CSV)."""
    candidates = [
        p
        for p in data_dir.glob("*")
        if p.is_file() and p.suffix.lower() in (".zip", ".csv") and p.name.startswith(FILE_PREFIX)
    ]
    if not candidates:
        raise FileNotFoundError(f"no {FILE_PREFIX}* ZIP or CSV found in {data_dir}")
    return max(candidates, key=lambda p: (re.findall(r"\d{8}", p.name) or [""])[-1])


def source_version(path: Path) -> str:
    found = re.findall(r"\d{8}", path.name)
    return found[-1] if found else datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y%m%d")


def load_bronze(con, csv_path: Path, version: str) -> None:
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    header = con.execute(
        "SELECT * FROM read_csv(?, all_varchar=true, header=true) LIMIT 0", [str(csv_path)]
    ).description
    columns = [snake_case(d[0]) for d in header]
    select = ", ".join(f'"{d[0]}" AS {snake_case(d[0])}' for d in header)
    con.execute(
        f"CREATE OR REPLACE TABLE bronze.nsw_psi_raw AS SELECT {select}, "
        "? AS _source_version FROM read_csv(?, all_varchar=true, header=true)",
        [version, str(csv_path)],
    )
    if "purchase_price" not in columns:
        raise ValueError("source CSV has no 'Purchase price' column")


def build_local(data_dir: Path, db_path: Path) -> date:
    """Build bronze, silver and gold in a DuckDB file. Returns the data-as-of date."""
    import duckdb

    source = find_source(data_dir)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    try:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = source
            if source.suffix.lower() == ".zip":
                with zipfile.ZipFile(source) as archive:
                    name = next(n for n in archive.namelist() if n.lower().endswith(".csv"))
                    csv_path = Path(archive.extract(name, tmp))
            load_bronze(con, csv_path, source_version(source))
            run_silver(con.execute, SCHEMAS, "duckdb")
            return run_gold(
                con.execute, lambda sql: con.execute(sql).fetchone()[0], SCHEMAS, "duckdb"
            )
    finally:
        con.close()
