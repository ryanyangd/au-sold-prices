"""Shared fixtures. `pg_url` starts a throwaway local Postgres (or uses TEST_DATABASE_URL)."""

import os
import shutil
import socket
import subprocess
import tempfile
from pathlib import Path

import pytest

PG_BIN_CANDIDATES = [
    "/opt/homebrew/opt/postgresql@17/bin",
    "/opt/homebrew/opt/postgresql@16/bin",
    "/opt/homebrew/opt/postgresql@15/bin",
    "/usr/lib/postgresql/16/bin",
    "/usr/lib/postgresql/15/bin",
    "/usr/lib/postgresql/14/bin",
]


def _find_pg_bin() -> Path | None:
    found = shutil.which("pg_ctl")
    if found:
        return Path(found).parent
    for candidate in PG_BIN_CANDIDATES:
        if (Path(candidate) / "pg_ctl").exists():
            return Path(candidate)
    return None


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def pg_url(tmp_path_factory):
    existing = os.environ.get("TEST_DATABASE_URL")
    if existing:
        yield existing
        return
    bin_dir = _find_pg_bin()
    if bin_dir is None:
        pytest.skip("PostgreSQL binaries not found (set TEST_DATABASE_URL to run DB tests)")
    data = tmp_path_factory.mktemp("pgdata")
    port = _free_port()
    socket_dir = tempfile.mkdtemp(prefix="pg", dir="/tmp")  # unix socket paths must be short
    subprocess.run(
        [bin_dir / "initdb", "-D", data, "-U", "postgres", "--auth=trust", "-E", "UTF8", "--locale=C"],
        check=True,
        capture_output=True,
        env={**os.environ, "LC_ALL": "C"},
    )
    options = f"-p {port} -k {socket_dir} -c listen_addresses=127.0.0.1 -c fsync=off"
    subprocess.run(
        [bin_dir / "pg_ctl", "-D", data, "-o", options, "-w", "-l", data / "log", "start"],
        check=True,
        capture_output=True,
        env={**os.environ, "LC_ALL": "C"},
    )
    try:
        yield f"postgresql://postgres@127.0.0.1:{port}/postgres"
    finally:
        subprocess.run([bin_dir / "pg_ctl", "-D", data, "-m", "immediate", "stop"], check=False)
        shutil.rmtree(socket_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def new_database(pg_url):
    """Factory returning the URL of a fresh, empty database on the test server."""
    import itertools

    import psycopg

    counter = itertools.count()
    base, _, _ = pg_url.rpartition("/")

    def create() -> str:
        name = f"test_{os.getpid()}_{next(counter)}"
        with psycopg.connect(pg_url, autocommit=True) as conn:
            conn.execute(f'CREATE DATABASE "{name}"')
        return f"{base}/{name}"

    return create
