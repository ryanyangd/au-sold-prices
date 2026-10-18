import pytest

pytest.importorskip("psycopg_pool")
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from au_sold_prices.api.app import create_app
from au_sold_prices.api.auth import DevVerifier
from au_sold_prices.api.config import Settings
from au_sold_prices.api.db import Repository


@pytest.fixture(scope="module")
def client(new_database):
    repo = Repository.connect(new_database())
    repo.ensure_app_schema()
    yield TestClient(create_app(Settings(), repo, DevVerifier()))
    repo.close()


def test_empty_database_behaves_as_no_data(client):
    assert client.get("/health/ready").status_code == 200
    assert client.get("/search/addresses", params={"q": "12 example st"}).json() == {"results": []}
    assert client.get("/properties/001-1").status_code == 404
    me = client.get("/me", headers={"Authorization": "Bearer dev:a@example.com"})
    assert me.json()["plan"] == "free"
