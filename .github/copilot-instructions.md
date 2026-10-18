# Copilot instructions for au-sold-prices

Sold-price analytics for Australian (currently NSW) property. Python data pipeline and API,
Next.js web app, Azure infrastructure in Bicep, deployed by GitHub Actions.

## Layout
- `src/au_sold_prices/` Python package: `pipeline/` (silver/gold SQL shared by DuckDB and Spark),
  `api/` (FastAPI), `nsw_*.py` (local file readers/downloader), `cli.py` (`ausold` command).
- `apps/web/` Next.js (TypeScript, Tailwind). Only `lib/api.ts` talks to the network.
- `pipelines/databricks/` notebooks and the Databricks bundle (ingest, bronze, silver/gold, load).
- `infra/` Bicep (`main.bicep`, `modules/`, `main.bicepparam`).
- `scripts/` local dev and one-time setup scripts; `scripts/ci/` used by workflows.
- `tests/` pytest suite using only synthetic data (`tests/sample_data.py`).

## Commands (run before opening a PR)
```sh
ruff check .
pytest                                   # DB tests start a throwaway local Postgres if available
cd apps/web && npm run lint && npm run typecheck && npm test && npm run build
az bicep build --file infra/main.bicep   # when infra/ changed
```
`scripts/dev-stack.sh check` runs the first three.

## Rules
- Never commit anything from `data/` or `docs-private/`, real sales data, secrets, keys or
  connection strings. Tests use invented rows only.
- Keep silver/gold SQL portable: it runs on DuckDB and Spark SQL. Add or change a test in
  `tests/test_pipeline.py` for every SQL change.
- API changes: keep the JSON contract in `apps/web/lib/types.ts` in sync and update
  `tests/test_api.py`.
- Free vs Pro gating happens in the API (`api/app.py`), never only in the UI.
- Do not edit `.github/workflows/deploy*.yml`, `infra/` or `scripts/ci/` unless the task is
  about deployment. Never change production settings or approvals.
- Small, focused PRs with a clear description. Prefer fixing the root cause and adding a
  regression test for every bug fix.
- Data licensing is unresolved for commercial use: do not add new data sources or change
  attribution text without being asked.
