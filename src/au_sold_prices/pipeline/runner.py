"""Engine-neutral runner for the silver and gold SQL.

The same SQL files run on DuckDB (local) and Spark SQL (Databricks). Callers pass an
`execute(sql)` function and a `scalar(sql)` function for their engine.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from importlib import resources

SQL_PACKAGE = "au_sold_prices.pipeline"
SILVER_FILE = "01_silver.sql"
GOLD_FILE = "02_gold.sql"
DAYS_MACRO = re.compile(r"@days\(\s*([^,()]+?)\s*,\s*((?:[^()]|\([^()]*\))+?)\s*\)")


@dataclass(frozen=True)
class Schemas:
    bronze: str = "bronze"
    silver: str = "silver"
    gold: str = "gold"


def read_sql(name: str) -> str:
    return (resources.files(SQL_PACKAGE) / "sql" / name).read_text(encoding="utf-8")


def days_between(engine: str, sql: str) -> str:
    """Rewrite @days(start, end) into the engine's whole-days-between expression."""

    def repl(match: re.Match[str]) -> str:
        start, end = match.group(1), match.group(2)
        if engine == "spark":
            return f"datediff({end}, {start})"
        return f"date_diff('day', {start}, {end})"

    return DAYS_MACRO.sub(repl, sql)


def split_statements(sql: str) -> list[str]:
    statements = []
    for part in sql.split(";\n"):
        lines = [ln for ln in part.splitlines() if not ln.strip().startswith("--")]
        text = "\n".join(lines).strip().rstrip(";")
        if text:
            statements.append(text)
    return statements


def years_before(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year - years)
    except ValueError:  # 29 Feb
        return day.replace(year=day.year - years, day=28)


def render(sql: str, engine: str, **params: str) -> str:
    return days_between(engine, sql).format(**params)


def run_silver(execute: Callable[[str], object], schemas: Schemas, engine: str) -> None:
    sql = render(read_sql(SILVER_FILE), engine, bronze=schemas.bronze, silver=schemas.silver)
    for statement in split_statements(sql):
        execute(statement)


def run_gold(
    execute: Callable[[str], object],
    scalar: Callable[[str], object],
    schemas: Schemas,
    engine: str,
) -> date:
    """Build gold tables. Returns the data-as-of date (newest arms-length sale)."""
    as_of = scalar(f"SELECT max(sale_date) FROM {schemas.silver}.sales WHERE is_arms_length")
    if as_of is None:
        raise ValueError("no arms-length sales in silver; cannot build gold")
    params = {f"as_of_{n}y": years_before(as_of, n).isoformat() for n in range(1, 7)}
    sql = render(
        read_sql(GOLD_FILE),
        engine,
        silver=schemas.silver,
        gold=schemas.gold,
        as_of=as_of.isoformat(),
        **params,
    )
    for statement in split_statements(sql):
        execute(statement)
    return as_of
