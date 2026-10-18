import pytest
from sample_data import scenario_rows, write_csv

from au_sold_prices import cli

pytest.importorskip("duckdb")


def test_build_gold_creates_database(tmp_path, capsys):
    write_csv(tmp_path / "nsw-property-sales-data-20260701.csv", scenario_rows())
    db = tmp_path / "lake.duckdb"

    assert cli.main(["build-gold", "--data-dir", str(tmp_path), "--db", str(db)]) == 0

    assert db.exists()
    assert "data as of 2026-06-30" in capsys.readouterr().out


def test_build_gold_without_source(tmp_path, capsys):
    assert cli.main(["build-gold", "--data-dir", str(tmp_path), "--db", str(tmp_path / "x")]) == 1
    assert "Build failed" in capsys.readouterr().err


def test_load_postgres_requires_url(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert cli.main(["load-postgres", "--db", str(tmp_path / "x"), "--database-url", ""]) == 1
    assert "DATABASE_URL" in capsys.readouterr().err
