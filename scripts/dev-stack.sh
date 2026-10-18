#!/bin/sh
# Local dev stack: Postgres + API + web, started and stopped as background processes.
#
#   scripts/dev-stack.sh start [db|api|web|all]   (default: all)
#   scripts/dev-stack.sh stop  [db|api|web|all]
#   scripts/dev-stack.sh restart [db|api|web|all]
#   scripts/dev-stack.sh status
#   scripts/dev-stack.sh logs  <api|web|db>       (follows the log; Ctrl-C to leave)
#   scripts/dev-stack.sh load-data                (download if needed, build gold, load Postgres)
#   scripts/dev-stack.sh check                    (ruff + pytest + web lint/typecheck/tests)
#   scripts/dev-stack.sh make-pro <email>         (give a dev-login user a Pro subscription)
#
# State (PID files, logs, database files) lives in ~/.local/share/ausold, never in the repo.
set -eu

REPO="$(cd "$(dirname "$0")/.." && pwd)"
STATE="${AUSOLD_STATE_DIR:-$HOME/.local/share/ausold}"
RUN="$STATE/run"
LOGS="$STATE/logs"
API_PORT="${AUSOLD_API_PORT:-8000}"
WEB_PORT="${AUSOLD_WEB_PORT:-3000}"
PG_PORT="${AUSOLD_PG_PORT:-54329}"
DATABASE_URL="postgresql://postgres@127.0.0.1:$PG_PORT/ausold"
PATH="/opt/homebrew/bin:/opt/homebrew/opt/postgresql@15/bin:/usr/local/bin:$PATH"
export PATH

mkdir -p "$RUN" "$LOGS"

alive() { [ -f "$RUN/$1.pid" ] && kill -0 "$(cat "$RUN/$1.pid")" 2>/dev/null; }

wait_http() { # url name seconds
  i=0
  while [ "$i" -lt "$3" ]; do
    if curl -fsS -o /dev/null "$1" 2>/dev/null; then echo "  $2 is up: $1"; return 0; fi
    i=$((i + 1)); sleep 1
  done
  echo "  $2 did not come up in $3s; see: scripts/dev-stack.sh logs ${4:-$2}" >&2
  return 1
}

start_db() {
  AUSOLD_PG_PORT="$PG_PORT" "$REPO/scripts/dev-postgres.sh" start >/dev/null
  echo "  db is up: $DATABASE_URL"
}

start_api() {
  if alive api; then echo "  api already running"; return 0; fi
  [ -x "$REPO/.venv/bin/uvicorn" ] || { echo "Run: python -m venv .venv && .venv/bin/pip install -e '.[dev,pipeline,api]'" >&2; exit 1; }
  (cd "$REPO" && DATABASE_URL="$DATABASE_URL" AUTH_MODE=dev CORS_ORIGINS="http://localhost:$WEB_PORT" \
    nohup .venv/bin/uvicorn au_sold_prices.api.app:build_default_app --factory --port "$API_PORT" \
    >"$LOGS/api.log" 2>&1 & echo $! >"$RUN/api.pid")
  wait_http "http://localhost:$API_PORT/health/ready" api 30
}

start_web() {
  if alive web; then echo "  web already running"; return 0; fi
  [ -d "$REPO/apps/web/node_modules" ] || (cd "$REPO/apps/web" && npm install --no-audit --no-fund)
  (cd "$REPO/apps/web" && NEXT_PUBLIC_USE_MOCK="${USE_MOCK:-false}" NEXT_PUBLIC_API_BASE_URL="http://localhost:$API_PORT" \
    nohup npm run dev -- --port "$WEB_PORT" >"$LOGS/web.log" 2>&1 & echo $! >"$RUN/web.pid")
  wait_http "http://localhost:$WEB_PORT/" web 60
}

stop_proc() { # name
  if alive "$1"; then
    pid="$(cat "$RUN/$1.pid")"
    # Stop the child processes (npm -> next) first, then the parent.
    for child in $(pgrep -P "$pid" 2>/dev/null || true); do
      for grandchild in $(pgrep -P "$child" 2>/dev/null || true); do kill "$grandchild" 2>/dev/null || true; done
      kill "$child" 2>/dev/null || true
    done
    kill "$pid" 2>/dev/null || true
    echo "  $1 stopped"
  else
    echo "  $1 not running"
  fi
  rm -f "$RUN/$1.pid"
}

stop_api() { stop_proc api; }
stop_web() { stop_proc web; }

stop_db() {
  "$REPO/scripts/dev-postgres.sh" stop >/dev/null 2>&1 && echo "  db stopped" || echo "  db not running"
}

targets() { case "${1:-all}" in all) echo "db api web" ;; db|api|web) echo "$1" ;; *) echo "unknown target: $1" >&2; exit 2 ;; esac; }

status() {
  for p in api web; do
    if alive "$p"; then echo "  $p: running (pid $(cat "$RUN/$p.pid"))"; else echo "  $p: stopped"; fi
  done
  if pg_isready -q -h 127.0.0.1 -p "$PG_PORT" 2>/dev/null; then echo "  db: running (port $PG_PORT)"; else echo "  db: stopped"; fi
  curl -fsS "http://localhost:$API_PORT/health/ready" >/dev/null 2>&1 && echo "  api health: ok" || true
  curl -fsS -o /dev/null "http://localhost:$WEB_PORT/" 2>/dev/null && echo "  web health: ok" || true
}

case "${1:-}" in
  start)
    echo "Starting..."
    for t in $(targets "${2:-all}"); do "start_$t"; done
    echo "Web: http://localhost:$WEB_PORT   API docs: http://localhost:$API_PORT/docs"
    ;;
  stop)
    echo "Stopping..."
    # Reverse order: web, api, db.
    for t in $(targets "${2:-all}" | tr ' ' '\n' | sed '1!G;h;$!d'); do "stop_$t"; done
    ;;
  restart) "$0" stop "${2:-all}"; "$0" start "${2:-all}" ;;
  status) status ;;
  logs)
    case "${2:-}" in
      api|web) tail -n 100 -f "$LOGS/$2.log" ;;
      db) tail -n 100 -f "${AUSOLD_PG_DIR:-$STATE/pg}/log" ;;
      *) echo "usage: $0 logs api|web|db" >&2; exit 2 ;;
    esac
    ;;
  load-data)
    cd "$REPO"
    start_db
    [ -n "$(ls data/nsw-property-sales-data-* 2>/dev/null)" ] || .venv/bin/ausold download-nsw --force
    .venv/bin/ausold build-gold
    DATABASE_URL="$DATABASE_URL" .venv/bin/ausold load-postgres
    ;;
  check)
    cd "$REPO"
    .venv/bin/ruff check .
    .venv/bin/pytest -q
    (cd apps/web && npm run lint && npm run typecheck && npm test)
    ;;
  make-pro)
    EMAIL="${2:?usage: $0 make-pro <email>}"
    # Dev logins use the token "dev:<email>"; this gives that user an active subscription.
    psql -h 127.0.0.1 -p "$PG_PORT" -U postgres ausold -q \
      -v email="$EMAIL" -v subject="dev|$EMAIL" <<'SQL'
INSERT INTO app.users (auth_subject, email, name) VALUES (:'subject', :'email', split_part(:'email', '@', 1))
  ON CONFLICT (auth_subject) DO NOTHING;
INSERT INTO app.subscriptions (stripe_subscription_id, user_id, status)
  SELECT 'sub_local_' || id, id, 'active' FROM app.users WHERE auth_subject = :'subject'
  ON CONFLICT (stripe_subscription_id) DO UPDATE SET status = 'active';
SQL
    echo "  $EMAIL is Pro (sign in with the dev login using this email)"
    ;;
  *)
    sed -n "2,14p" "$0" | sed 's/^# \{0,1\}//'
    exit 2
    ;;
esac
