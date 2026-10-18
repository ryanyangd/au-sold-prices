import pytest

pytest.importorskip("duckdb")
pytest.importorskip("psycopg")

import psycopg
from sample_data import scenario_rows, write_csv

from au_sold_prices.pipeline import local, serving


@pytest.fixture(scope="module")
def loaded(new_database, tmp_path_factory):
    pg_url = new_database()
    tmp = tmp_path_factory.mktemp("serve")
    write_csv(tmp / "nsw-property-sales-data-20260701.csv", scenario_rows())
    db = tmp / "lake.duckdb"
    local.build_local(tmp, db)
    counts = serving.load_postgres(db, pg_url)
    return pg_url, counts


def test_load_copies_all_gold_tables(loaded):
    url, counts = loaded
    assert counts["property"] > 0 and counts["sale"] >= counts["property"]
    with psycopg.connect(url) as conn:
        for table, expected in counts.items():
            got = conn.execute(f"SELECT count(*) FROM serving.{table}").fetchone()[0]
            assert got == expected


def test_indexes_exist_and_staging_is_gone(loaded):
    url, _ = loaded
    with psycopg.connect(url) as conn:
        indexes = {
            r[0]
            for r in conn.execute("SELECT indexname FROM pg_indexes WHERE schemaname = 'serving'")
        }
        schemas = {r[0] for r in conn.execute("SELECT nspname FROM pg_namespace")}
    assert {"property_prefix_idx", "property_trgm_idx", "sale_property_idx"} <= indexes
    assert "serving_next" not in schemas and "serving_old" not in schemas


def test_reload_replaces_live_schema(loaded, tmp_path):
    url, counts = loaded
    write_csv(tmp_path / "nsw-property-sales-data-20260702.csv", scenario_rows()[:3])
    db = tmp_path / "lake.duckdb"
    local.build_local(tmp_path, db)

    new_counts = serving.load_postgres(db, url)

    assert new_counts["property"] < counts["property"]
    with psycopg.connect(url) as conn:
        assert conn.execute("SELECT count(*) FROM serving.property").fetchone()[0] == (
            new_counts["property"]
        )
