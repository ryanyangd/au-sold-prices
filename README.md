# au-sold-prices

Open-source tool to help homeowners, buyers and sellers track house sold prices in Australia.

**Early development:** the CLI currently uses an empty in-memory source, so it
reports `No data available`. Real data integrations are not yet implemented.

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

## Development

Run lint checks and tests from the repository root:

```sh
ruff check .
pytest
```

CI runs these checks on Python 3.10 and 3.12.

## Data sources

Data-source implementations must use licensed or open data. Do not scrape sites
whose terms forbid it.

## License

MIT; see [LICENSE](LICENSE).
