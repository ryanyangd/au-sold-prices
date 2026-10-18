# au-sold-prices

Open-source tool to help homeowners, buyers and sellers track house sold prices in Australia.

**Early development:** a prototype reads NSW Valuer General bulk sales files
from a local directory. Other states currently report `No data available`.

## Install

Requires Python 3.10 or newer. From the repository root:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

On Windows, activate the environment with `.venv\Scripts\activate` instead.

## CLI usage

```sh
ausold --version
ausold median Richmond VIC
ausold median "South Yarra" VIC
```

With data available, the median is printed in whole Australian dollars, for
example `$850,000`. Fractional dollars are truncated.

For NSW, place the Valuer General bulk sales ZIP (or `.DAT`) files, downloaded
from the official source, in `./data` (or pass `--data-dir`):

```sh
ausold median Parramatta NSW
ausold median Parramatta NSW --property-type unit
```

Only `house` sales are included by default. The `data/` directory is
git-ignored; never commit downloaded data.

### Daily download job (macOS)

```sh
./scripts/install-launchd.sh
```

This installs a per-user launchd job that runs `ausold download-nsw` at login
and hourly while the Mac is on. The command checks the source's `Last-Modified`
header at most once a day, downloads the cleaned NSW sales archive only when it
changed (replacing the previous one), retries transient network errors with
backoff, and waits 6 hours after a failed attempt, so a Mac that was off or
offline catches up on its own. It warns when the source has not updated for
over 14 days. Files go to `~/.local/share/ausold/data` (`./data` links to it);
logs are in `~/.local/share/ausold/logs`. Re-run the script after pulling code
changes. Run `ausold download-nsw --force` to check now.

The data is a third-party re-publication of NSW Valuer General data, for
personal, non-commercial use only. The downloader identifies itself honestly
and does not work around blocks; a 4xx response fails the run.

## Local app stack (data pipeline, API, web)

Day-to-day commands (start, stop, status, logs, tests) are in
[docs/local-development.md](docs/local-development.md); deploying to Azure is in
[docs/deployment.md](docs/deployment.md). In short: `scripts/dev-stack.sh start|stop|status`.

```sh
pip install -e ".[dev,pipeline,api]"

ausold download-nsw --force               # fetch the cleaned NSW archive into ./data
ausold build-gold                         # bronze -> silver -> gold in DuckDB (about 15 s)
scripts/dev-postgres.sh start             # local Postgres (no Docker); prints the URL
export DATABASE_URL=postgresql://postgres@127.0.0.1:54329/ausold
ausold load-postgres                      # swap gold tables into the `serving` schema

AUTH_MODE=dev uvicorn au_sold_prices.api.app:build_default_app --factory --port 8000
cd apps/web && npm install && NEXT_PUBLIC_USE_MOCK=false npm run dev
```

In `AUTH_MODE=dev` a bearer token `dev:<email>` signs you in; make that user Pro by inserting a
row into `app.subscriptions` (see `tests/test_api.py`). `AUTH_MODE=entra` verifies Microsoft
Entra External ID tokens and is the only mode allowed when `ENVIRONMENT=prod`.

How the pieces fit:

- `src/au_sold_prices/pipeline/sql/` holds the silver and gold SQL, shared by DuckDB (local) and
  Spark SQL (Databricks notebooks in `pipelines/databricks/`).
- `src/au_sold_prices/api/` is the FastAPI service (address search, property analytics with
  free/Pro gating, Entra token verification, Stripe checkout/portal/webhooks).
- `apps/web/` is the Next.js frontend; see its README.
- `infra/` deploys everything to Azure with Bicep; see its README.

## Development

Run lint checks and tests from the repository root:

```sh
ruff check .
pytest
```

Database tests start a throwaway local Postgres (found on `PATH` or under Homebrew) or use
`TEST_DATABASE_URL`; they are skipped if neither is available.

CI runs these checks on Python 3.10 and 3.12.

## Data sources

Data-source implementations must use licensed or open data. Do not scrape sites
whose terms forbid it. Check each source's licence before using or sharing its
data.

## License

MIT; see [LICENSE](LICENSE).
