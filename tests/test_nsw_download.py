import io
import urllib.error
import zipfile
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import pytest

from au_sold_prices import cli, nsw_download
from au_sold_prices.nsw_download import BlockedError, DownloadError

MODIFIED = datetime(2026, 9, 13, 19, 3, tzinfo=timezone.utc)
NOW = MODIFIED + timedelta(days=1)
HEADER = '"Property locality","Purchase price","Contract date"\n'
TARGET = "nsw-property-sales-data-20260913.zip"


def zip_bytes(csv_text=HEADER + '"Testtown","800000","2026-01-01"\n'):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("data.csv", csv_text)
    return buffer.getvalue()


class FakeResponse(io.BytesIO):
    def __init__(self, body=b"", headers=None):
        super().__init__(body)
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def http_error(code):
    return urllib.error.HTTPError("http://x", code, "err", None, None)


@pytest.fixture
def server(monkeypatch):
    """Fake network. Set server["HEAD"]/server["GET"] to a value or a list of them."""
    routes = {"HEAD": FakeResponse(headers={"Last-Modified": format_datetime(MODIFIED)})}
    calls = []

    def fake_open(url, method="GET", timeout=0):
        calls.append(method)
        value = routes[method]
        if isinstance(value, list):
            value = value.pop(0)
        if isinstance(value, Exception):
            raise value
        if isinstance(value, bytes):
            return FakeResponse(value)
        return value

    monkeypatch.setattr(nsw_download, "_open", fake_open)
    routes["calls"] = calls
    return routes


def no_sleep(_):
    pass


def test_downloads_and_replaces_older_archive(tmp_path, server):
    server["GET"] = zip_bytes()
    old = tmp_path / "nsw-property-sales-data-20260801.zip"
    old.write_bytes(zip_bytes())

    result = nsw_download.download_latest(tmp_path, NOW, no_sleep)

    assert result.downloaded and result.filename == TARGET and not result.stale
    assert zipfile.is_zipfile(tmp_path / TARGET)
    assert not old.exists()
    assert not list(tmp_path.glob("*.part"))


def test_skips_when_already_current(tmp_path, server):
    (tmp_path / TARGET).write_bytes(zip_bytes())

    result = nsw_download.download_latest(tmp_path, NOW, no_sleep)

    assert not result.downloaded
    assert server["calls"] == ["HEAD"]


def test_flags_stale_source(tmp_path, server):
    (tmp_path / TARGET).write_bytes(zip_bytes())
    result = nsw_download.download_latest(tmp_path, MODIFIED + timedelta(days=20), no_sleep)
    assert result.stale


def test_retries_transient_errors(tmp_path, server):
    delays = []
    server["HEAD"] = [
        urllib.error.URLError("offline"),
        http_error(503),
        FakeResponse(headers={"Last-Modified": format_datetime(MODIFIED)}),
    ]
    server["GET"] = zip_bytes()

    nsw_download.download_latest(tmp_path, NOW, delays.append)

    assert delays == list(nsw_download.RETRY_DELAYS[:2])


def test_gives_up_after_retries(tmp_path, server):
    server["HEAD"] = [urllib.error.URLError("offline")] * 10
    with pytest.raises(DownloadError):
        nsw_download.download_latest(tmp_path, NOW, no_sleep)


@pytest.mark.parametrize("code", [403, 404])
def test_client_errors_are_not_retried(tmp_path, server, code):
    delays = []
    server["HEAD"] = [http_error(code)]
    with pytest.raises(BlockedError):
        nsw_download.download_latest(tmp_path, NOW, delays.append)
    assert delays == []


@pytest.mark.parametrize(
    "body",
    [b"<html>challenge</html>", zip_bytes("no,csv,header\n"), zip_bytes("").replace(b"data.csv", b"data.txt")],
)
def test_invalid_download_is_rejected(tmp_path, server, body):
    server["GET"] = body
    with pytest.raises(DownloadError):
        nsw_download.download_latest(tmp_path, NOW, no_sleep)
    assert not list(tmp_path.iterdir())


def test_missing_last_modified(tmp_path, server):
    server["HEAD"] = FakeResponse()
    with pytest.raises(DownloadError):
        nsw_download.download_latest(tmp_path, NOW, no_sleep)


def test_run_if_due_schedule_and_backoff(tmp_path, server):
    server["GET"] = zip_bytes()

    assert nsw_download.run_if_due(tmp_path, now=NOW, sleep=no_sleep).downloaded
    assert nsw_download.run_if_due(tmp_path, now=NOW + timedelta(hours=3)) is None
    later = NOW + timedelta(days=1)
    assert not nsw_download.run_if_due(tmp_path, now=later, sleep=no_sleep).downloaded


def test_failed_attempt_waits_for_cooldown(tmp_path, server):
    server["HEAD"] = [http_error(403)]
    with pytest.raises(BlockedError):
        nsw_download.run_if_due(tmp_path, now=NOW, sleep=no_sleep)

    assert not nsw_download.is_due(tmp_path, NOW + timedelta(hours=1))
    assert nsw_download.is_due(tmp_path, NOW + timedelta(hours=7))


def test_cli_download_reports_failure(tmp_path, server, capsys):
    server["HEAD"] = [http_error(403)]
    assert cli.main(["download-nsw", "--data-dir", str(tmp_path)]) == 1
    assert "NSW download failed" in capsys.readouterr().err


def test_cli_download_success(tmp_path, server, capsys):
    server["GET"] = zip_bytes()
    assert cli.main(["download-nsw", "--data-dir", str(tmp_path), "--force"]) == 0
    assert f"Downloaded {TARGET}" in capsys.readouterr().out
