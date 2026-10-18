## What and why

<!-- One or two sentences. Link the issue: Fixes #123 -->

## How it was tested

- [ ] `ruff check .` and `pytest`
- [ ] Web: lint, typecheck, tests, build (if `apps/web` changed)
- [ ] `az bicep build` (if `infra/` changed)
- [ ] Regression test added for a bug fix

## Safety

- [ ] No data from `data/` or `docs-private/`, no secrets or real personal data
- [ ] No change to production approvals or settings (unless this PR is about that)
