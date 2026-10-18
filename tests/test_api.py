import pytest

pytest.importorskip("duckdb")
pytest.importorskip("psycopg_pool")
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient
from sample_data import make_row, scenario_rows, write_csv

from au_sold_prices.api.app import create_app
from au_sold_prices.api.auth import DevVerifier
from au_sold_prices.api.config import Settings
from au_sold_prices.api.db import Repository
from au_sold_prices.pipeline import local, serving


class FakeBilling:
    def __init__(self):
        self.customers = []
        self.events = {}

    def create_customer(self, email, name, user_id):
        self.customers.append(email)
        return f"cus_{len(self.customers)}"

    def checkout_url(self, customer_id, price_id, success_url, cancel_url):
        return f"https://pay.example/{customer_id}/{price_id}"

    def portal_url(self, customer_id, return_url):
        return f"https://portal.example/{customer_id}"

    def parse_event(self, payload, signature):
        if signature != "good":
            raise ValueError("bad signature")
        import json

        return json.loads(payload)


def extra_rows():
    street = {"Property street name": "Example St", "Property house number": "12"}
    return [
        make_row("101", "2025-09-01", "900000", **street),
        make_row("102", "2026-04-01", "950000", **{**street, "Property house number": "14"}),
        make_row(
            "103", "2026-05-01", "500000",
            **{**street, "Property unit number": "3", "Strata lot number": "7"},
        ),
        make_row("104", "2026-05-05", "700000", **{"Property street name": "Other Rd",
                                                    "Property locality": "Otherville"}),
    ]


@pytest.fixture(scope="module")
def env(new_database, tmp_path_factory):
    url = new_database()
    tmp = tmp_path_factory.mktemp("api")
    write_csv(tmp / "nsw-property-sales-data-20260701.csv", scenario_rows() + extra_rows())
    db = tmp / "lake.duckdb"
    local.build_local(tmp, db)
    serving.load_postgres(db, url)
    repo = Repository.connect(url)
    repo.ensure_app_schema()
    billing = FakeBilling()
    settings = Settings(
        database_url=url,
        stripe_price_monthly="price_m",
        stripe_price_annual="price_a",
        app_base_url="http://app.example",
    )
    client = TestClient(create_app(settings, repo, DevVerifier(), billing))
    yield client, repo, billing
    repo.close()


def auth(email):
    return {"Authorization": f"Bearer dev:{email}"}


def make_pro(repo, email, customer="cus_pro"):
    user = repo.upsert_user(f"dev|{email}", email, None)
    repo.set_customer_id(user.id, customer)
    repo.upsert_subscription(f"sub_{customer}", user.id, "active", None)


def test_health(env):
    client, _, _ = env
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/health/ready").json() == {"status": "ok"}


def search(client, q, **params):
    response = client.get("/search/addresses", params={"q": q, **params})
    assert response.status_code == 200
    return response.json()["results"]


def test_search_prefix_and_abbreviation(env):
    client, _, _ = env
    for query in ("12 example st", "12 Example Street", "12 exa"):
        results = search(client, query)
        assert results[0]["address"] == "12 Example St"
        assert results[0]["display"] == "12 Example St, Exampleville NSW 2000"
    assert {r["address"] for r in search(client, "12 example st")} == {
        "12 Example St",
        "3/12 Example St",  # found by the contains-all-words fallback
    }


def test_search_unit_formats(env):
    client, _, _ = env
    assert search(client, "unit 3, 12 example")[0]["address"] == "3/12 Example St"
    assert search(client, "3/12 ex")[0]["property_type"] == "unit"


def test_search_by_suburb_and_word_order(env):
    client, _, _ = env
    assert any(r["suburb"] == "Otherville" for r in search(client, "otherville"))
    assert search(client, "rd other")[0]["address"] == "5 Other Rd"


def test_search_edge_cases(env):
    client, _, _ = env
    assert search(client, "ab") == []
    assert search(client, "%%%") == []
    assert search(client, "zzzzzz") == []
    assert len(search(client, "sample", limit=2)) == 2
    assert client.get("/search/addresses").status_code == 422
    assert client.get("/search/addresses", params={"q": "x" * 101}).status_code == 422


def test_search_result_shape(env):
    client, _, _ = env
    result = search(client, "12 example st")[0]
    assert set(result) == {
        "property_id", "address", "suburb", "postcode", "state", "property_type", "display",
        "last_sale_price", "last_sale_date",
    }  # fmt: skip
    assert result["property_id"] == "001-101" and result["last_sale_price"] == 900000


def test_property_free_plan_locks_sections(env):
    client, _, _ = env
    body = client.get("/properties/001-1").json()
    assert body["access"] == {
        "plan": "free",
        "locked_sections": ["sales_history", "trend", "distribution", "comparables"],
    }
    assert body["sales"] is body["trend"] is body["distribution"] is body["comparables"] is None
    assert body["property"]["id"] == "001-1" and body["property"]["sale_count"] == 2
    assert body["metrics"]["last_sale_price"] == 700000
    assert body["metrics"]["last_sale_date"] == "2026-03-01"
    assert body["metrics"]["cagr_pct"] == pytest.approx(4.9, abs=0.1)
    assert body["suburb"]["name"] == "Exampleville"
    assert body["suburb"]["median_12m"] is not None and body["suburb"]["sales_12m"] >= 3
    assert body["data_as_of"] == "2026-06-30"


def test_property_pro_plan_has_full_analytics(env):
    client, repo, _ = env
    make_pro(repo, "pro@example.com")
    body = client.get("/properties/001-1", headers=auth("pro@example.com")).json()

    assert body["access"] == {"plan": "pro", "locked_sections": []}
    assert [s["price"] for s in body["sales"]] == [700000, 500000]
    assert body["sales"][0]["change_pct"] == pytest.approx(40.0)
    assert body["sales"][1]["change_pct"] is None
    assert body["trend"] and set(body["trend"][0]) == {"month", "median", "sales_count"}
    assert body["trend"] == sorted(body["trend"], key=lambda t: t["month"])
    assert sum(b["count"] for b in body["distribution"]) > 0
    assert body["comparables"]
    assert all(c["property_id"] != "001-1" for c in body["comparables"])
    assert all(c["property_type"] == "house" for c in body["comparables"])


def test_property_not_found_and_bad_token(env):
    client, _, _ = env
    assert client.get("/properties/999-9").status_code == 404
    assert client.get("/properties/001-1", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert client.get("/properties/001-1", headers={"Authorization": "Basic abc"}).status_code == 401


def test_me_requires_auth_and_reports_plan(env):
    client, repo, _ = env
    assert client.get("/me").status_code == 401
    me = client.get("/me", headers=auth("new@example.com")).json()
    assert (me["email"], me["plan"], me["status"]) == ("new@example.com", "free", "none")
    make_pro(repo, "paid@example.com", "cus_paid")
    assert client.get("/me", headers=auth("paid@example.com")).json()["plan"] == "pro"


def test_checkout_flow(env):
    client, _, billing = env
    assert client.post("/billing/checkout", json={"plan": "pro_monthly"}).status_code == 401
    headers = auth("buyer@example.com")
    assert client.post("/billing/checkout", json={"plan": "bogus"}, headers=headers).status_code == 422

    first = client.post("/billing/checkout", json={"plan": "pro_monthly"}, headers=headers)
    second = client.post("/billing/checkout", json={"plan": "pro_annual"}, headers=headers)

    assert first.status_code == 200 and first.json()["url"].endswith("/price_m")
    assert second.json()["url"].endswith("/price_a")
    assert billing.customers.count("buyer@example.com") == 1
    assert client.post("/billing/portal", headers=headers).json()["url"].startswith("https://portal")


def test_checkout_rejects_existing_subscriber(env):
    client, repo, _ = env
    make_pro(repo, "dupe@example.com", "cus_dupe")
    response = client.post(
        "/billing/checkout", json={"plan": "pro_monthly"}, headers=auth("dupe@example.com")
    )
    assert response.status_code == 409


def event(event_id, kind, customer, status="active", sub="sub_evt", **extra):
    obj = {"id": sub, "customer": customer, "status": status, **extra}
    return {"id": event_id, "type": kind, "data": {"object": obj}}


def post_event(client, payload, signature="good"):
    import json

    return client.post(
        "/webhooks/stripe",
        content=json.dumps(payload),
        headers={"Stripe-Signature": signature, "Content-Type": "application/json"},
    )


def test_webhook_activates_and_cancels_subscription(env):
    client, _repo, billing = env
    headers = auth("hook@example.com")
    client.post("/billing/checkout", json={"plan": "pro_monthly"}, headers=headers)
    customer = f"cus_{len(billing.customers)}"
    future = 4_000_000_000

    ok = post_event(client, event("evt_1", "customer.subscription.created", customer,
                                  current_period_end=future))  # fmt: skip
    assert ok.json() == {"status": "ok"}
    assert client.get("/me", headers=headers).json()["plan"] == "pro"

    assert post_event(client, event("evt_1", "customer.subscription.created", customer)).json() == {
        "status": "duplicate"
    }

    post_event(client, event("evt_2", "customer.subscription.deleted", customer, status="canceled"))
    me = client.get("/me", headers=headers).json()
    assert (me["plan"], me["status"]) == ("free", "canceled")


def test_webhook_reads_period_end_from_item_and_past_due_grace(env):
    client, _repo, billing = env
    headers = auth("grace@example.com")
    client.post("/billing/checkout", json={"plan": "pro_monthly"}, headers=headers)
    customer = f"cus_{len(billing.customers)}"
    items = {"data": [{"current_period_end": 4_000_000_000}]}

    post_event(client, event("evt_3", "customer.subscription.updated", customer,
                             status="past_due", sub="sub_grace", items=items))  # fmt: skip
    assert client.get("/me", headers=headers).json()["plan"] == "pro"

    expired = {"data": [{"current_period_end": 1_000_000_000}]}
    post_event(client, event("evt_4", "customer.subscription.updated", customer,
                             status="past_due", sub="sub_grace", items=expired))  # fmt: skip
    assert client.get("/me", headers=headers).json()["plan"] == "free"


def test_webhook_rejects_bad_signature_and_ignores_unknown(env):
    client, _, _ = env
    assert post_event(client, event("evt_x", "customer.subscription.created", "c"), "bad").status_code == 400
    assert client.post("/webhooks/stripe", content=b"{}").status_code == 400
    unknown = post_event(client, event("evt_y", "customer.subscription.created", "cus_nobody"))
    assert unknown.status_code == 200
    other = post_event(client, event("evt_z", "invoice.paid", "cus_nobody"))
    assert other.json() == {"status": "ok"}
