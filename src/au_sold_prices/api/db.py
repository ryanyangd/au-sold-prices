"""Database access for the API (psycopg 3). All queries are parameterised."""

import math
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from psycopg import errors
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from au_sold_prices.api.search import escape_like, normalise_query

APP_SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS app;
CREATE TABLE IF NOT EXISTS app.users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  auth_subject text UNIQUE NOT NULL,
  email text,
  name text,
  stripe_customer_id text UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS app.subscriptions (
  stripe_subscription_id text PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES app.users (id),
  status text NOT NULL,
  current_period_end timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS app.stripe_events (
  event_id text PRIMARY KEY,
  received_at timestamptz NOT NULL DEFAULT now()
);
"""

ACTIVE_STATUSES = ("active", "trialing")
HISTOGRAM_BUCKETS = 10
TREND_MONTHS = 60
COMPARABLES = 8


@dataclass(frozen=True)
class UserRecord:
    id: str
    email: str | None
    name: str | None
    stripe_customer_id: str | None
    plan: str
    status: str


def _price_buckets(prices: list[int]) -> list[dict[str, Any]]:
    """Equal-width histogram clipped to the 2nd-98th percentile so outliers don't flatten it."""
    if not prices:
        return []
    prices = sorted(prices)
    lo = prices[int(0.02 * (len(prices) - 1))]
    hi = prices[math.ceil(0.98 * (len(prices) - 1))]
    if hi <= lo:
        return [{"bucket_from": lo, "bucket_to": hi, "count": len(prices)}]
    width = (hi - lo) / HISTOGRAM_BUCKETS
    counts = [0] * HISTOGRAM_BUCKETS
    for price in prices:
        index = min(HISTOGRAM_BUCKETS - 1, max(0, int((price - lo) / width)))
        counts[index] += 1
    return [
        {
            "bucket_from": round(lo + i * width),
            "bucket_to": round(lo + (i + 1) * width),
            "count": count,
        }
        for i, count in enumerate(counts)
    ]


class Repository:
    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    @classmethod
    def connect(cls, database_url: str, timeout: float = 5) -> "Repository":
        # Fail fast (5 s) when the database is down, and drop dead connections after a restart.
        pool = ConnectionPool(
            database_url,
            min_size=1,
            max_size=10,
            timeout=timeout,
            max_lifetime=1800,
            check=ConnectionPool.check_connection,
            kwargs={"row_factory": dict_row},
            open=True,
        )
        return cls(pool)

    def close(self) -> None:
        self._pool.close()

    def _all(self, sql: str, params: dict[str, Any] | tuple = ()) -> list[dict[str, Any]]:
        try:
            with self._pool.connection() as conn:
                return conn.execute(sql, params).fetchall()
        except (errors.UndefinedTable, errors.InvalidSchemaName):
            if "serving." in sql:  # data not loaded yet: behave as "no data"
                return []
            raise

    def _one(self, sql: str, params: dict[str, Any] | tuple = ()) -> dict[str, Any] | None:
        rows = self._all(sql, params)
        return rows[0] if rows else None

    def ensure_app_schema(self) -> None:
        with self._pool.connection() as conn:
            conn.execute(APP_SCHEMA_SQL)

    def ping(self) -> bool:
        return self._one("SELECT 1 AS ok") is not None

    def data_as_of(self) -> date | None:
        row = self._one("SELECT data_as_of FROM serving.meta LIMIT 1")
        return row["data_as_of"] if row else None

    # ---- search ----

    def search_addresses(self, query: str, limit: int) -> list[dict[str, Any]]:
        norm = normalise_query(query)
        if len(norm) < 3:
            return []
        columns = (
            "property_key, address_display, suburb, postcode, state, property_type, "
            "last_sale_price, last_sale_date"
        )
        rows = self._all(
            f"SELECT {columns} FROM serving.property WHERE search_text LIKE %(p)s "
            "ORDER BY sale_count DESC, length(search_text) LIMIT %(n)s",
            {"p": escape_like(norm) + "%", "n": limit},
        )
        if len(rows) < limit:
            tokens = [t for t in norm.split(" ") if t]
            conditions = " AND ".join(f"search_text LIKE %(t{i})s" for i in range(len(tokens)))
            params: dict[str, Any] = {f"t{i}": f"%{escape_like(t)}%" for i, t in enumerate(tokens)}
            params["n"] = limit - len(rows)
            params["seen"] = [r["property_key"] for r in rows] or [""]
            rows += self._all(
                f"SELECT {columns} FROM serving.property WHERE {conditions} "
                "AND NOT (property_key = ANY(%(seen)s)) "
                "ORDER BY sale_count DESC, length(search_text) LIMIT %(n)s",
                params,
            )
        return rows

    # ---- property ----

    def get_property(self, property_key: str) -> dict[str, Any] | None:
        return self._one("SELECT * FROM serving.property WHERE property_key = %s", (property_key,))

    def get_sales(self, property_key: str) -> list[dict[str, Any]]:
        return self._all(
            "SELECT sale_date, settlement_date, price, change_pct, years_held "
            "FROM serving.sale WHERE property_key = %s ORDER BY sale_date DESC",
            (property_key,),
        )

    def get_suburb_stats(self, suburb: str, state: str, property_type: str) -> dict | None:
        return self._one(
            "SELECT * FROM serving.suburb_stats "
            "WHERE suburb = %s AND state = %s AND property_type = %s",
            (suburb, state, property_type),
        )

    def get_trend(self, suburb: str, state: str, property_type: str) -> list[dict[str, Any]]:
        rows = self._all(
            "SELECT month, median_price, sales_count FROM serving.suburb_month "
            "WHERE suburb = %s AND state = %s AND property_type = %s "
            "ORDER BY month DESC LIMIT %s",
            (suburb, state, property_type, TREND_MONTHS),
        )
        return list(reversed(rows))

    def get_distribution(
        self, suburb: str, state: str, property_type: str, as_of: date
    ) -> list[dict[str, Any]]:
        rows = self._all(
            "SELECT price FROM serving.sale "
            "WHERE suburb = %(s)s AND state = %(st)s AND property_type = %(t)s AND is_stat_sale "
            "AND sale_date > %(a)s::date - interval '12 months' AND sale_date <= %(a)s",
            {"s": suburb, "st": state, "t": property_type, "a": as_of},
        )
        return _price_buckets([r["price"] for r in rows])

    def get_comparables(self, prop: dict[str, Any], as_of: date) -> list[dict[str, Any]]:
        return self._all(
            "SELECT property_key, address_display, property_type, price, sale_date, land_area_m2 "
            "FROM serving.sale "
            "WHERE suburb = %(s)s AND state = %(st)s AND property_type = %(t)s AND is_stat_sale "
            "AND property_key <> %(k)s "
            "AND sale_date > %(a)s::date - interval '24 months' AND sale_date <= %(a)s "
            "ORDER BY abs(land_area_m2 - %(area)s) NULLS LAST, sale_date DESC LIMIT %(n)s",
            {
                "s": prop["suburb"],
                "st": prop["state"],
                "t": prop["property_type"],
                "k": prop["property_key"],
                "a": as_of,
                "area": prop["land_area_m2"],
                "n": COMPARABLES,
            },
        )

    # ---- users and subscriptions ----

    def upsert_user(self, subject: str, email: str | None, name: str | None) -> UserRecord:
        self._one(
            "INSERT INTO app.users (auth_subject, email, name) VALUES (%s, %s, %s) "
            "ON CONFLICT (auth_subject) DO UPDATE SET "
            "email = COALESCE(EXCLUDED.email, app.users.email), "
            "name = COALESCE(EXCLUDED.name, app.users.name) RETURNING id",
            (subject, email, name),
        )
        user = self._user_where("u.auth_subject = %s", (subject,))
        assert user is not None
        return user

    def _user_where(self, where: str, params: tuple) -> UserRecord | None:
        row = self._one(
            "SELECT u.id::text AS id, u.email, u.name, u.stripe_customer_id, "
            "  s.status, s.current_period_end "
            "FROM app.users u LEFT JOIN LATERAL ("
            "  SELECT status, current_period_end FROM app.subscriptions "
            "  WHERE user_id = u.id ORDER BY (status IN ('active','trialing')) DESC, "
            "  updated_at DESC LIMIT 1) s ON true "
            f"WHERE {where}",
            params,
        )
        if row is None:
            return None
        status = row["status"] or "none"
        paid = status in ACTIVE_STATUSES
        if status == "past_due" and row["current_period_end"] is not None:
            paid = row["current_period_end"] > _now()
        return UserRecord(
            row["id"], row["email"], row["name"], row["stripe_customer_id"],
            "pro" if paid else "free", status,
        )  # fmt: skip

    def get_user_by_customer(self, customer_id: str) -> UserRecord | None:
        return self._user_where("u.stripe_customer_id = %s", (customer_id,))

    def set_customer_id(self, user_id: str, customer_id: str) -> None:
        self._one(
            "UPDATE app.users SET stripe_customer_id = %s WHERE id = %s::uuid RETURNING id",
            (customer_id, user_id),
        )

    def record_stripe_event(self, event_id: str) -> bool:
        """True if this event is new; False if it was already processed."""
        row = self._one(
            "INSERT INTO app.stripe_events (event_id) VALUES (%s) "
            "ON CONFLICT DO NOTHING RETURNING event_id",
            (event_id,),
        )
        return row is not None

    def forget_stripe_event(self, event_id: str) -> None:
        self._one(
            "DELETE FROM app.stripe_events WHERE event_id = %s RETURNING event_id", (event_id,)
        )

    def upsert_subscription(
        self, subscription_id: str, user_id: str, status: str, period_end: Any
    ) -> None:
        self._one(
            "INSERT INTO app.subscriptions "
            "(stripe_subscription_id, user_id, status, current_period_end) "
            "VALUES (%s, %s::uuid, %s, %s) ON CONFLICT (stripe_subscription_id) DO UPDATE SET "
            "status = EXCLUDED.status, current_period_end = EXCLUDED.current_period_end, "
            "updated_at = now() RETURNING stripe_subscription_id",
            (subscription_id, user_id, status, period_end),
        )


def _now() -> datetime:
    return datetime.now(timezone.utc)
