import io
import json
import urllib.error
import zipfile
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import ingest_core
import pytest
from ingest_core import BlockedError, IngestError, run_ingest

MODIFIED = datetime(2026, 9, 13, 19, 3, tzinfo=timezone.utc)
NOW = MODIFIED + timedelta(days=1)
HEADER = '"Property locality","Purchase price","Contract date"\n'
FOLDER = "nsw_psi/20260913"


def zip_bytes(csv_text=HEADER + '"Testtown","800000","2026-01-01"\n', name="data.csv"):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(name, csv_text)
    return buffer.getvalue()


class FakeResponse(io.BytesIO):
    def __init__(self, body=b"", headers=None):
        super().__init__(body)
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class FakeLake:
    def __init__(self, existing=()):
        self.files = {p: b"" for p in existing}

    def exists(self, path):
        return path in self.files

    def upload_file(self, path, local_path):
        self.files[path] = local_path.read_bytes()

    def upload_text(self, path, text):
        self.files[path] = text.encode()


def http_error(code):
    return urllib.error.HTTPError("http://x", code, "err", None, None)


@pytest.fixture
def server(monkeypatch):
    routes = {"HEAD": FakeResponse(headers={"Last-Modified": format_datetime(MODIFIED)})}
    calls = []

    def fake_open(url, method="GET"):
        calls.append(method)
        value = routes[method]
        if isinstance(value, list):
            value = value.pop(0)
        if isinstance(value, Exception):
            raise value
        return FakeResponse(value) if isinstance(value, bytes) else value

    monkeypatch.setattr(ingest_core, "_open", fake_open)
    routes["calls"] = calls
    return routes


def no_sleep(_):
    pass


def test_ingests_archive_csv_and_manifest(server):
    server["GET"] = zip_bytes()
    lake = FakeLake()

    result = run_ingest("http://src", lake, NOW, no_sleep)

    assert result == {"status": "ingested", "folder": FOLDER, "stale": False}
    assert set(lake.files) == {f"{FOLDER}/{n}" for n in ("archive.zip", "data.csv", "_manifest.json")}
    manifest = json.loads(lake.files[f"{FOLDER}/_manifest.json"])
    assert manifest["source_last_modified"].startswith("2026-09-13T19:03")
    assert manifest["csv_bytes"] == len(lake.files[f"{FOLDER}/data.csv"])
    assert len(manifest["archive_sha256"]) == 64


def test_skips_when_manifest_exists(server):
    lake = FakeLake([f"{FOLDER}/_manifest.json"])

    assert run_ingest("http://src", lake, NOW, no_sleep)["status"] == "skipped"
    assert server["calls"] == ["HEAD"]


def test_incomplete_previous_run_is_redone(server):
    server["GET"] = zip_bytes()
    lake = FakeLake([f"{FOLDER}/archive.zip"])

    assert run_ingest("http://src", lake, NOW, no_sleep)["status"] == "ingested"


def test_stale_source_is_flagged_and_logged(server, caplog):
    lake = FakeLake([f"{FOLDER}/_manifest.json"])

    result = run_ingest("http://src", lake, MODIFIED + timedelta(days=20), no_sleep)

    assert result["stale"]
    assert "STALE_SOURCE" in caplog.text


def test_retries_transient_errors(server):
    delays = []
    server["HEAD"] = [
        urllib.error.URLError("offline"),
        http_error(503),
        FakeResponse(headers={"Last-Modified": format_datetime(MODIFIED)}),
    ]
    server["GET"] = zip_bytes()

    run_ingest("http://src", FakeLake(), NOW, delays.append)

    assert delays == list(ingest_core.RETRY_DELAYS[:2])


def test_gives_up_after_retries(server):
    server["HEAD"] = [urllib.error.URLError("offline")] * 10
    with pytest.raises(IngestError):
        run_ingest("http://src", FakeLake(), NOW, no_sleep)


@pytest.mark.parametrize("code", [403, 404])
def test_client_errors_are_not_retried(server, code):
    delays = []
    server["HEAD"] = [http_error(code)]
    with pytest.raises(BlockedError):
        run_ingest("http://src", FakeLake(), NOW, delays.append)
    assert delays == []


@pytest.mark.parametrize(
    "body",
    [b"<html>challenge</html>", zip_bytes("no,csv,header\n"), zip_bytes(name="data.txt")],
)
def test_invalid_download_writes_nothing(server, body):
    server["GET"] = body
    lake = FakeLake()
    with pytest.raises(IngestError):
        run_ingest("http://src", lake, NOW, no_sleep)
    assert lake.files == {}


def test_missing_last_modified(server):
    server["HEAD"] = FakeResponse()
    with pytest.raises(IngestError):
        run_ingest("http://src", FakeLake(), NOW, no_sleep)
