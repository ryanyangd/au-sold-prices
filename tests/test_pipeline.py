from datetime import date

import pytest

pytest.importorskip("duckdb")

import duckdb
from sample_data import scenario_rows, write_csv

from au_sold_prices.pipeline import local, runner


@pytest.fixture(scope="module")
def gold(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("pipe")
    write_csv(tmp / "nsw-property-sales-data-20260701.csv", scenario_rows())
    db = tmp / "lake.duckdb"
    as_of = local.build_local(tmp, db)
    con = duckdb.connect(str(db), read_only=True)
    yield con, as_of
    con.close()


def rows(con, sql):
    return con.execute(sql).fetchall()


def test_as_of_is_newest_arms_length_sale(gold):
    assert gold[1] == date(2026, 6, 30)


def test_silver_rejects_and_dedupes(gold):
    con, _ = gold
    rejected = dict(rows(con, "SELECT property_id, reject_reason FROM silver.sales_rejected"))
    assert rejected == {"12": "invalid_price", "13": "invalid_price", "14": "missing_suburb"}
    assert rows(con, "SELECT count(*) FROM silver.sales WHERE property_id = '2'") == [(1,)]
    assert rows(con, "SELECT count(*) FROM silver.sales") == [(13,)]


def test_silver_types_flags_and_fallback_date(gold):
    con, _ = gold
    flags = {
        r[0]: r[1:]
        for r in rows(
            con,
            "SELECT property_id, is_arms_length, is_stat_sale, property_type FROM silver.sales",
        )
    }
    assert flags["6"][:2] == (False, False)
    assert flags["7"][:2] == (False, False)
    assert flags["8"][:2] == (True, False)
    assert flags["9"][:2] == (False, False)
    assert flags["10"] == (True, True, "unit")
    assert flags["1"][2] == "house"
    assert rows(con, "SELECT sale_date FROM silver.sales WHERE property_id = '15'") == [
        (date(2026, 2, 20),)
    ]
    assert rows(con, "SELECT address_display FROM silver.sales WHERE property_id = '10'") == [
        ("3/12 Sample Rd",)
    ]


def test_gold_sale_history_changes(gold):
    con, _ = gold
    sales = rows(
        con,
        "SELECT sale_date, price, prev_price, change_pct, years_held FROM gold.sale "
        "WHERE property_key = '001-1' ORDER BY sale_date",
    )
    assert sales[0][2:] == (None, None, None)
    assert sales[1][2] == 500000
    assert sales[1][3] == pytest.approx(40.0)
    assert sales[1][4] == pytest.approx(7.0, abs=0.01)


def test_suburb_stats_exclude_unreliable_sales(gold):
    con, _ = gold
    stats = rows(
        con,
        "SELECT median_12m, p25_12m, p75_12m, sales_12m, change_1y_pct FROM gold.suburb_stats "
        "WHERE suburb = 'Exampleville' AND property_type = 'house'",
    )[0]
    assert stats[:4] == (pytest.approx(750000), pytest.approx(637500), pytest.approx(825000), 4)
    assert stats[4] == pytest.approx((750000 / 650000 - 1) * 100)


def test_suburb_month_medians(gold):
    con, _ = gold
    assert rows(
        con,
        "SELECT median_price, sales_count FROM gold.suburb_month "
        "WHERE suburb = 'Exampleville' AND property_type = 'house' AND month = DATE '2026-01-01'",
    ) == [(800000.0, 1)]


def test_property_summary(gold):
    con, _ = gold
    prop = rows(
        con,
        "SELECT sale_count, first_sale_date, last_sale_date, last_sale_price, cagr_pct, "
        "holding_years, land_area_m2, search_text FROM gold.property WHERE property_key = '001-1'",
    )[0]
    assert prop[0:4] == (2, date(2019, 3, 1), date(2026, 3, 1), 700000)
    assert prop[4] == pytest.approx((1.4 ** (1 / 7.0) - 1) * 100, abs=0.05)
    assert prop[5] == pytest.approx(121 / 365.25, abs=0.01)
    assert prop[6] == 600.0
    assert prop[7] == "5 sample rd exampleville 2000"
    # Properties with excluded sales never appear.
    assert rows(con, "SELECT count(*) FROM gold.property WHERE property_key IN ('001-6','001-7')") == [
        (0,)
    ]


def test_meta(gold):
    con, _ = gold
    meta = rows(con, "SELECT data_as_of, source_version, rejected_rows FROM gold.meta")[0]
    assert meta == (date(2026, 6, 30), "20260701", 3)


def test_days_macro_rewrites_per_engine():
    sql = "x @days(a.d, DATE '2026-01-01') y @days(b, c)"
    assert runner.days_between("duckdb", sql) == (
        "x date_diff('day', a.d, DATE '2026-01-01') y date_diff('day', b, c)"
    )
    assert runner.days_between("spark", sql) == (
        "x datediff(DATE '2026-01-01', a.d) y datediff(c, b)"
    )


def test_split_statements_skips_comments():
    sql = "-- note; with semicolon\nSELECT 1;\nSELECT 2;\n"
    assert runner.split_statements(sql) == ["SELECT 1", "SELECT 2"]


def test_years_before_handles_leap_day():
    assert runner.years_before(date(2024, 2, 29), 1) == date(2023, 2, 28)


def test_find_source_prefers_newest(tmp_path):
    for name in ("nsw-property-sales-data-20260101.zip", "nsw-property-sales-data-20260301.csv"):
        (tmp_path / name).write_text("x")
    (tmp_path / "other.csv").write_text("x")
    assert local.find_source(tmp_path).name == "nsw-property-sales-data-20260301.csv"
    with pytest.raises(FileNotFoundError):
        local.find_source(tmp_path / "missing")


def test_silver_uses_only_the_newest_source_version(tmp_path):
    write_csv(tmp_path / "nsw-property-sales-data-20260701.csv", scenario_rows())
    db = tmp_path / "lake.duckdb"
    local.build_local(tmp_path, db)
    con = duckdb.connect(str(db))
    try:
        before = con.execute("SELECT count(*) FROM silver.sales").fetchone()[0]
        con.execute(
            "INSERT INTO bronze.nsw_psi_raw SELECT * REPLACE ('20250101' AS _source_version) "
            "FROM bronze.nsw_psi_raw"
        )
        runner.run_silver(con.execute, local.SCHEMAS, "duckdb")
        assert con.execute("SELECT count(*) FROM silver.sales").fetchone()[0] == before
        assert con.execute("SELECT max(source_version) FROM silver.sales").fetchone()[0] == "20260701"
    finally:
        con.close()
