import time

import pytest

pytest.importorskip("psycopg_pool")
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from au_sold_prices.api.app import create_app
from au_sold_prices.api.auth import DevVerifier
from au_sold_prices.api.config import Settings
from au_sold_prices.api.db import Repository


@pytest.fixture(scope="module")
def client():
    # Nothing listens on port 1, like a stopped database server.
    repo = Repository.connect("postgresql://postgres@127.0.0.1:1/none", timeout=1)
    yield TestClient(create_app(Settings(), repo, DevVerifier()), raise_server_exceptions=False)
    repo.close()


def test_database_outage_fails_fast_with_503(client):
    started = time.monotonic()
    ready = client.get("/health/ready")
    search = client.get("/search/addresses", params={"q": "12 example st"})

    assert ready.status_code == 503 and search.status_code == 503
    assert search.json() == {"detail": "Service temporarily unavailable"}
    assert time.monotonic() - started < 6


def test_liveness_does_not_depend_on_the_database(client):
    assert client.get("/health").json() == {"status": "ok"}
