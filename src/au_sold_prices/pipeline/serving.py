"""Load gold tables into the Postgres serving schema with an atomic schema swap.

Readers keep using the live `serving` schema while `serving_next` is built; the swap is one
short transaction. The row source is pluggable: DuckDB locally, Spark on Databricks.
"""

from collections.abc import Callable, Iterable
from pathlib import Path

from au_sold_prices.pipeline.runner import read_sql, split_statements

LIVE = "serving"
STAGING = "serving_next"
OLD = "serving_old"
BATCH = 50_000

TABLES = {
    "property": [
        "property_key", "address_display", "unit_number", "house_number", "street_name",
        "suburb", "postcode", "state", "property_type", "land_area_m2", "zoning", "sale_count",
        "first_sale_date", "last_sale_date", "last_sale_price", "cagr_pct", "holding_years",
        "vs_suburb_median_pct", "search_text",
    ],
    "sale": [
        "property_key", "suburb", "state", "postcode", "property_type", "address_display",
        "land_area_m2", "sale_date", "settlement_date", "price", "is_stat_sale",
        "is_multi_parcel", "prev_price", "change_pct", "years_held",
    ],
    "suburb_month": [
        "suburb", "state", "property_type", "month", "median_price", "sales_count",
    ],
    "suburb_stats": [
        "suburb", "state", "property_type", "median_12m", "p25_12m", "p75_12m", "sales_12m",
        "change_1y_pct", "change_3y_pct", "change_5y_pct",
    ],
    "meta": ["data_as_of", "source_version", "silver_rows", "rejected_rows", "built_at"],
}  # fmt: skip

# Yields rows (tuples) of a gold table, selecting the given columns in order.
RowReader = Callable[[str, list[str]], Iterable[tuple]]


def _run_script(cur, name: str, schema: str) -> None:
    for statement in split_statements(read_sql(name).replace("{schema}", schema)):
        cur.execute(statement)


def rebuild_serving(
    database_url: str, read_rows: RowReader, grant_select_to: str | None = None
) -> dict[str, int]:
    """Rebuild the serving schema from `read_rows` and swap it in. Returns row counts."""
    import psycopg

    counts: dict[str, int] = {}
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
            cur.execute(f"DROP SCHEMA IF EXISTS {STAGING} CASCADE")
            _run_script(cur, "serving_tables.sql", STAGING)
            for table, columns in TABLES.items():
                cols = ", ".join(columns)
                total = 0
                with cur.copy(f"COPY {STAGING}.{table} ({cols}) FROM STDIN") as copy:
                    for row in read_rows(table, columns):
                        copy.write_row(row)
                        total += 1
                counts[table] = total
            _run_script(cur, "serving_indexes.sql", STAGING)
            cur.execute(f"ANALYZE {STAGING}.property")
            cur.execute(f"ANALYZE {STAGING}.sale")
            if grant_select_to:
                cur.execute(f'GRANT USAGE ON SCHEMA {STAGING} TO "{grant_select_to}"')
                cur.execute(f'GRANT SELECT ON ALL TABLES IN SCHEMA {STAGING} TO "{grant_select_to}"')
            cur.execute(f"DROP SCHEMA IF EXISTS {OLD} CASCADE")
            cur.execute(f"SELECT 1 FROM pg_namespace WHERE nspname = '{LIVE}'")
            if cur.fetchone():
                cur.execute(f"ALTER SCHEMA {LIVE} RENAME TO {OLD}")
            cur.execute(f"ALTER SCHEMA {STAGING} RENAME TO {LIVE}")
            cur.execute(f"DROP SCHEMA IF EXISTS {OLD} CASCADE")
        conn.commit()
    return counts


def load_postgres(
    duckdb_path: Path,
    database_url: str,
    gold: str = "gold",
    grant_select_to: str | None = None,
) -> dict[str, int]:
    """Rebuild the serving schema from a local gold DuckDB file."""
    import duckdb

    duck = duckdb.connect(str(duckdb_path), read_only=True)

    def read_rows(table: str, columns: list[str]):
        result = duck.execute(f"SELECT {', '.join(columns)} FROM {gold}.{table}")
        while batch := result.fetchmany(BATCH):
            yield from batch

    try:
        return rebuild_serving(database_url, read_rows, grant_select_to)
    finally:
        duck.close()
