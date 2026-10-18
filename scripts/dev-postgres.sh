#!/bin/sh
# Local dev Postgres (no Docker). Usage: scripts/dev-postgres.sh start|stop|url
# Data lives in ~/.local/share/ausold/pg, outside the repo.
set -eu

PORT="${AUSOLD_PG_PORT:-54329}"
DIR="${AUSOLD_PG_DIR:-$HOME/.local/share/ausold/pg}"
SOCK="${TMPDIR:-/tmp}/ausold-pg"
BIN="${PG_BIN:-$(dirname "$(command -v pg_ctl 2>/dev/null || echo /opt/homebrew/opt/postgresql@15/bin/pg_ctl)")}"
export LC_ALL=C

case "${1:-}" in
  start)
    mkdir -p "$SOCK"
    [ -d "$DIR" ] || "$BIN/initdb" -D "$DIR" -U postgres --auth=trust -E UTF8 --locale=C >/dev/null
    "$BIN/pg_ctl" -D "$DIR" -o "-p $PORT -k $SOCK -c listen_addresses=127.0.0.1" -w -l "$DIR/log" start
    "$BIN/psql" -h 127.0.0.1 -p "$PORT" -U postgres -tc "SELECT 1 FROM pg_database WHERE datname='ausold'" | grep -q 1 \
      || "$BIN/createdb" -h 127.0.0.1 -p "$PORT" -U postgres ausold
    echo "postgresql://postgres@127.0.0.1:$PORT/ausold"
    ;;
  stop) "$BIN/pg_ctl" -D "$DIR" -m fast stop ;;
  url) echo "postgresql://postgres@127.0.0.1:$PORT/ausold" ;;
  *) echo "usage: $0 start|stop|url" >&2; exit 2 ;;
esac
