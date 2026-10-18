"""Download the cleaned NSW property sales archive into a local directory.

Source: https://nswpropertysalesdata.com/ (a third-party re-publication of NSW
Valuer General data). For personal, non-commercial use only; check the licence
of the underlying NSW data before any wider use.

The downloader is polite (one HEAD per run, a GET only when the file changed),
identifies itself, and does not try to get past blocks: a 4xx fails the run.
"""

import json
import time
import urllib.error
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

SOURCE_URL = "https://nswpropertysalesdata.com/data/archive.zip"
USER_AGENT = "ausold-personal-downloader/0.1 (+personal, non-commercial)"
FILE_PREFIX = "nsw-property-sales-data-"
STATE_FILE = ".download_state.json"
REQUIRED_COLUMNS = ("Property locality", "Purchase price", "Contract date")
RETRY_DELAYS = (5, 30, 120)
TIMEOUT = 60
SUCCESS_INTERVAL = timedelta(days=1)
ATTEMPT_COOLDOWN = timedelta(hours=6)
STALE_AFTER = timedelta(days=14)


class DownloadError(Exception):
    pass


class BlockedError(DownloadError):
    """The server refused the request; retrying will not help."""


@dataclass
class DownloadResult:
    downloaded: bool
    filename: str
    source_last_modified: datetime
    stale: bool


def _open(url: str, method: str = "GET", timeout: int = TIMEOUT):
    request = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(request, timeout=timeout)


def _with_retries(action: Callable[[], object], sleep: Callable[[float], None]):
    for attempt in range(len(RETRY_DELAYS) + 1):
        try:
            return action()
        except BlockedError:
            raise
        except urllib.error.HTTPError as exc:
            if 400 <= exc.code < 500 and exc.code != 429:
                raise BlockedError(f"HTTP {exc.code}: request refused") from exc
            error: Exception = exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            error = exc
        if attempt == len(RETRY_DELAYS):
            raise DownloadError(f"giving up: {error}") from error
        sleep(RETRY_DELAYS[attempt])


def remote_last_modified(sleep: Callable[[float], None] = time.sleep) -> datetime:
    def head() -> str | None:
        with _open(SOURCE_URL, "HEAD") as response:
            return response.headers.get("Last-Modified")

    header = _with_retries(head, sleep)
    try:
        return parsedate_to_datetime(str(header)).astimezone(timezone.utc)
    except (TypeError, ValueError) as exc:
        raise DownloadError("server did not send a usable Last-Modified header") from exc


def _validate_archive(path: Path) -> None:
    if not zipfile.is_zipfile(path):
        raise BlockedError("response was not a ZIP file")
    with zipfile.ZipFile(path) as archive:
        names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise DownloadError("archive contains no CSV file")
        with archive.open(names[0]) as stream:
            header = stream.readline().decode("utf-8-sig", errors="replace")
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        raise DownloadError(f"unexpected CSV header, missing columns: {missing}")


def _fetch_archive(target: Path, sleep: Callable[[float], None]) -> None:
    partial = target.with_name(target.name + ".part")

    def fetch() -> None:
        with _open(SOURCE_URL) as response, partial.open("wb") as out:
            while chunk := response.read(1 << 20):
                out.write(chunk)

    try:
        _with_retries(fetch, sleep)
        _validate_archive(partial)
        partial.replace(target)
    finally:
        partial.unlink(missing_ok=True)


def download_latest(
    data_dir: Path,
    now: datetime | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> DownloadResult:
    """Fetch the archive if the remote copy is newer than the local one."""
    now = now or datetime.now(timezone.utc)
    data_dir.mkdir(parents=True, exist_ok=True)
    modified = remote_last_modified(sleep)
    target = data_dir / f"{FILE_PREFIX}{modified:%Y%m%d}.zip"
    stale = now - modified > STALE_AFTER

    if target.exists():
        return DownloadResult(False, target.name, modified, stale)

    _fetch_archive(target, sleep)
    for old in data_dir.glob(f"{FILE_PREFIX}*.zip"):
        if old != target:
            old.unlink()
    return DownloadResult(True, target.name, modified, stale)


def _load_state(data_dir: Path) -> dict[str, str]:
    try:
        return json.loads((data_dir / STATE_FILE).read_text())
    except (OSError, ValueError):
        return {}


def _save_state(data_dir: Path, state: dict[str, str]) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / STATE_FILE).write_text(json.dumps(state))


def _age_at_least(state: dict[str, str], key: str, delta: timedelta, now: datetime) -> bool:
    try:
        return now - datetime.fromisoformat(state[key]) >= delta
    except (KeyError, ValueError):
        return True


def is_due(data_dir: Path, now: datetime | None = None) -> bool:
    """True if the last success is a day old and the last attempt is past its cooldown."""
    now = now or datetime.now(timezone.utc)
    state = _load_state(data_dir)
    return _age_at_least(state, "last_success", SUCCESS_INTERVAL, now) and _age_at_least(
        state, "last_attempt", ATTEMPT_COOLDOWN, now
    )


def run_if_due(
    data_dir: Path,
    force: bool = False,
    now: datetime | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> DownloadResult | None:
    """Download when due (or forced). Returns None when nothing was due."""
    now = now or datetime.now(timezone.utc)
    if not force and not is_due(data_dir, now):
        return None
    state = _load_state(data_dir)
    state["last_attempt"] = now.isoformat()
    _save_state(data_dir, state)
    result = download_latest(data_dir, now, sleep)
    state["last_success"] = now.isoformat()
    _save_state(data_dir, state)
    return result
