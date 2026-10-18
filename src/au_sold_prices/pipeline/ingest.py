"""Download the NSW sales archive into a raw zone (no cloud SDK imports).

Layout written per source version:
    nsw_psi/<YYYYMMDD>/archive.zip
    nsw_psi/<YYYYMMDD>/data.csv
    nsw_psi/<YYYYMMDD>/_manifest.json   (written last; its presence means "complete")

On Databricks the raw zone is a Unity Catalog volume (a normal path under /Volumes/...), see
`PathStore`.
"""

import hashlib
import json
import logging
import shutil
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Protocol

USER_AGENT = "ausold-ingest/0.1 (+personal, non-commercial)"
REQUIRED_COLUMNS = ("Property locality", "Purchase price", "Contract date")
RETRY_DELAYS = (5, 30, 120)
TIMEOUT = 120
STALE_AFTER = timedelta(days=14)
PREFIX = "nsw_psi"

log = logging.getLogger("ingest")


class IngestError(Exception):
    pass


class BlockedError(IngestError):
    """The server refused the request; retrying will not help."""


class LakeStore(Protocol):
    def exists(self, path: str) -> bool: ...

    def upload_file(self, path: str, local_path: Path) -> None: ...

    def upload_text(self, path: str, text: str) -> None: ...


class PathStore:
    """LakeStore backed by a directory, e.g. a Databricks volume mounted at /Volumes/..."""

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)

    def exists(self, path: str) -> bool:
        return (self._root / path).exists()

    def upload_file(self, path: str, local_path: Path) -> None:
        target = self._root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(local_path, target)

    def upload_text(self, path: str, text: str) -> None:
        target = self._root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def _open(url: str, method: str = "GET"):
    request = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(request, timeout=TIMEOUT)


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
            raise IngestError(f"giving up: {error}") from error
        log.warning("transient error, retrying: %s", error)
        sleep(RETRY_DELAYS[attempt])


def remote_last_modified(url: str, sleep: Callable[[float], None]) -> datetime:
    def head() -> str | None:
        with _open(url, "HEAD") as response:
            return response.headers.get("Last-Modified")

    header = _with_retries(head, sleep)
    try:
        return parsedate_to_datetime(str(header)).astimezone(timezone.utc)
    except (TypeError, ValueError) as exc:
        raise IngestError("server did not send a usable Last-Modified header") from exc


def _download(url: str, target: Path, sleep: Callable[[float], None]) -> None:
    def fetch() -> None:
        with _open(url) as response, target.open("wb") as out:
            shutil.copyfileobj(response, out, 1 << 20)

    _with_retries(fetch, sleep)


def _extract_csv(archive_path: Path, target: Path) -> None:
    if not zipfile.is_zipfile(archive_path):
        raise BlockedError("response was not a ZIP file")
    with zipfile.ZipFile(archive_path) as archive:
        names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if len(names) != 1:
            raise IngestError(f"expected exactly one CSV in the archive, found {len(names)}")
        with archive.open(names[0]) as src, target.open("wb") as out:
            shutil.copyfileobj(src, out, 1 << 20)
    with target.open("rb") as stream:
        header = stream.readline().decode("utf-8-sig", errors="replace")
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        raise IngestError(f"unexpected CSV header, missing columns: {missing}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def run_ingest(
    source_url: str,
    lake: LakeStore,
    now: datetime | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    """Copy the source archive into the lake if this version is not there yet."""
    now = now or datetime.now(timezone.utc)
    modified = remote_last_modified(source_url, sleep)
    folder = f"{PREFIX}/{modified:%Y%m%d}"
    stale = now - modified > STALE_AFTER
    if stale:
        log.warning("STALE_SOURCE: source last modified %s", modified.isoformat())

    if lake.exists(f"{folder}/_manifest.json"):
        log.info("already ingested %s", folder)
        return {"status": "skipped", "folder": folder, "stale": stale}

    with tempfile.TemporaryDirectory() as tmp:
        archive_path = Path(tmp) / "archive.zip"
        csv_path = Path(tmp) / "data.csv"
        _download(source_url, archive_path, sleep)
        _extract_csv(archive_path, csv_path)

        manifest = {
            "source_url": source_url,
            "source_last_modified": modified.isoformat(),
            "retrieved_at": now.isoformat(),
            "archive_bytes": archive_path.stat().st_size,
            "archive_sha256": _sha256(archive_path),
            "csv_bytes": csv_path.stat().st_size,
            "csv_sha256": _sha256(csv_path),
        }
        lake.upload_file(f"{folder}/archive.zip", archive_path)
        lake.upload_file(f"{folder}/data.csv", csv_path)
        lake.upload_text(f"{folder}/_manifest.json", json.dumps(manifest, indent=2))

    log.info("ingested %s", folder)
    return {"status": "ingested", "folder": folder, "stale": stale}
