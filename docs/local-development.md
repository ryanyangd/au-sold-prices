# Local development: start, stop and test the stack

Everything runs on your machine: Postgres, the API and the web app. No Azure account is needed.
All state (database files, logs, PID files) lives in `~/.local/share/ausold`, never in the repo.

## Quick reference

```sh
scripts/dev-stack.sh start          # Postgres + API + web
scripts/dev-stack.sh status
scripts/dev-stack.sh stop
scripts/dev-stack.sh restart api    # or: db | web | all
scripts/dev-stack.sh logs api       # or: web | db   (Ctrl-C to leave)
scripts/dev-stack.sh load-data      # download if missing, build gold tables, load Postgres
scripts/dev-stack.sh make-pro you@example.com
scripts/dev-stack.sh check          # ruff + pytest + web lint/typecheck/tests
```

| Service | URL / port | Notes |
|---|---|---|
| Web | http://localhost:3000 | Next.js dev server, talks to the real local API |
| API | http://localhost:8000 (docs at `/docs`) | FastAPI, `AUTH_MODE=dev` |
| Postgres | `postgresql://postgres@127.0.0.1:54329/ausold` | Homebrew Postgres 15, no Docker |

Change ports with `AUSOLD_WEB_PORT`, `AUSOLD_API_PORT` and `AUSOLD_PG_PORT`. Use mock data in the
web app (no API needed) with `USE_MOCK=true scripts/dev-stack.sh start web`.

## One-time setup

Requirements: Python 3.10+, Node 22+, Homebrew PostgreSQL (`brew install postgresql@15`), and
optionally the Azure CLI and GitHub CLI for the deployment steps.

```sh
python3 -m venv .venv
.venv/bin/pip install -e ".[dev,pipeline,api]"
(cd apps/web && npm install)
```

## First run with data

```sh
scripts/dev-stack.sh load-data      # about a minute: download, build bronze/silver/gold, load Postgres
scripts/dev-stack.sh start
```

`load-data` uses the cleaned NSW archive in `./data` (a symlink to `~/.local/share/ausold/data`
if you ran `scripts/install-launchd.sh`). If `./data` has no `nsw-property-sales-data-*` file it
downloads one. You can also drop a CSV or ZIP in there yourself. `data/` is git-ignored; never
commit it.

Run the steps by hand if you prefer:

```sh
ausold download-nsw --force         # fetch the latest archive into ./data
ausold build-gold                   # bronze -> silver -> gold in data/lake.duckdb (about 15 s)
export DATABASE_URL=postgresql://postgres@127.0.0.1:54329/ausold
ausold load-postgres                # swap the gold tables into Postgres (about 20 s)
```

## Day-to-day

Start in the morning, stop at night:

```sh
scripts/dev-stack.sh start
# ... work ...
scripts/dev-stack.sh stop
```

The API and web server reload on code changes. After changing SQL under
`src/au_sold_prices/pipeline/sql/`, rebuild the data: `ausold build-gold && ausold load-postgres`.

## Testing the app by hand

1. Open http://localhost:3000 and type an address (3+ letters), for example `12 smith st`,
   `unit 3 12 church` or a suburb. Pick a suggestion to open the property page.
2. **Free view:** signed out you see the key metrics and suburb snapshot; trend, price
   distribution, sale history and comparable sales are locked.
3. **Pro view:** `scripts/dev-stack.sh make-pro you@example.com`, then sign in at `/login` using
   the dev login with that email.
4. Pricing and checkout (`/pricing`, `/account`) need Stripe keys, so locally they show
   "billing is not configured". That is expected.

Dev login: any email works; the API accepts the bearer token `dev:<email>`. For example:

```sh
curl -H "Authorization: Bearer dev:you@example.com" http://localhost:8000/me
curl "http://localhost:8000/search/addresses?q=12%20smith%20st"
```

## Automated tests

```sh
scripts/dev-stack.sh check          # everything below in one go
.venv/bin/ruff check .
.venv/bin/pytest                    # 120+ tests; DB tests start a throwaway Postgres on a free port
cd apps/web && npm run lint && npm run typecheck && npm test && npm run build
```

Tests only use invented sample rows (`tests/sample_data.py`). To run the DB tests against a
Postgres you already have, set `TEST_DATABASE_URL` (a superuser URL; the tests create their own
databases).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `start` says a service did not come up | `scripts/dev-stack.sh logs api` (or `web`, `db`) |
| Port already in use | `scripts/dev-stack.sh stop`, or set another port with `AUSOLD_*_PORT` |
| Search returns nothing | Data not loaded: `scripts/dev-stack.sh load-data` |
| `ausold: command not found` | Use `.venv/bin/ausold` or activate the venv |
| Postgres will not start (`invalid locale` or stale `postmaster.pid`) | `scripts/dev-stack.sh stop db`; if it still fails remove `~/.local/share/ausold/pg/postmaster.pid` |
| Web shows "Failed to fetch" | API is down or the web was started with another API port; restart both |
| Pro features locked | Run `make-pro <email>` and sign in with exactly that email |
| Start from scratch | `scripts/dev-stack.sh stop`, delete `~/.local/share/ausold/pg`, then `scripts/dev-stack.sh load-data` |

## The background download job (optional)

`scripts/install-launchd.sh` installs a macOS job that downloads the latest archive daily to
`~/.local/share/ausold/data`. It is independent of the stack above. Remove it with:

```sh
launchctl bootout gui/$(id -u)/com.ausold.download-nsw
rm ~/Library/LaunchAgents/com.ausold.download-nsw.plist
```
