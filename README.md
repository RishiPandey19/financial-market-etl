# Financial Market ETL Pipeline

A production-style ETL pipeline for daily U.S. stock-market data. The project extracts price data from Alpha Vantage, stores raw API responses for auditability, validates transformed records with Pandera, and loads clean market observations into PostgreSQL through idempotent upserts.

The default stock universe is `AAPL, MSFT, NVDA, AMZN, GOOGL`.

## Highlights

- End-to-end Python ETL flow with extraction, transformation, validation, loading, logging, and retry behavior
- Raw-response retention under `data/raw/<TICKER>/` so API output can be audited or replayed
- Pandera data-quality checks before records are written to the database
- PostgreSQL schema with duplicate protection on `ticker + trading_date`
- Airflow DAG for weekday scheduling at 5:00 PM `America/Los_Angeles`
- Docker Compose setup for local PostgreSQL and Airflow
- Unit tests, fixture-based demo mode, and optional PostgreSQL integration tests

## Tech Stack

- Python 3.11+
- Alpha Vantage API
- requests
- pandas
- Pandera
- SQLAlchemy
- PostgreSQL
- Apache Airflow
- Docker Compose
- pytest
- python-dotenv

## Quick Commands

```bash
make setup          # create .venv and install Python dependencies
make test           # run unit tests, integration test is skipped by default
make postgres-up    # start PostgreSQL on localhost:5433
make demo           # load bundled sample data into PostgreSQL, no API key needed
make run            # run the live Alpha Vantage ETL with your .env API key
make airflow-up     # start Airflow and PostgreSQL
```

## What The Pipeline Does

1. Extracts daily stock prices from Alpha Vantage.
2. Saves every raw API response under `data/raw/<TICKER>/`.
3. Transforms API JSON into clean market-price rows.
4. Adds `daily_return`, `moving_average_7d`, and `moving_average_30d`.
5. Runs automated data-quality checks with Pandera.
6. Loads records into PostgreSQL.
7. Prevents duplicate `ticker + trading_date` records with a database upsert.
8. Runs from Airflow at 5:00 PM `America/Los_Angeles` on weekdays.
9. Logs extraction, validation, loading, retries, and failures to `logs/market_etl.log`.

The weekday Airflow schedule matches normal trading-day cadence. On exchange holidays, the job may still run, but the upsert keeps historical data stable and prevents duplicate market observations.

## Architecture

```text
Alpha Vantage API or local demo fixture
        |
        v
Extract raw JSON with retries
        |
        v
Retain raw response under data/raw/
        |
        v
pandas transform to daily price rows
        |
        v
Pandera data-quality validation
        |
        v
PostgreSQL upsert through SQLAlchemy
        |
        v
Airflow scheduled weekday run at 5 PM America/Los_Angeles
```

The Airflow DAG is intentionally thin. It calls the same Python pipeline that can be run manually, which keeps the business logic testable outside Airflow.

## Project Layout

```text
financial-market-etl/
  airflow/dags/financial_market_etl_dag.py
  data/raw/
  db/init/00-create-databases.sql
  docs/
  logs/
  src/market_etl/
  tests/
  tests/fixtures/alpha_vantage_daily_aapl.json
  .github/workflows/tests.yml
  .env.example
  .gitignore
  Dockerfile
  Makefile
  docker-compose.yml
  pytest.ini
  requirements.txt
```

## Setup

Install these first:

- Docker Desktop for Mac
- Python 3.11 or newer
- A free Alpha Vantage API key

Then from this project folder:

```bash
cp .env.example .env
```

Edit `.env` and replace:

```text
ALPHA_VANTAGE_API_KEY=replace_me
```

with your real key. Do not commit `.env`.

## Run With Docker Compose

Airflow and PostgreSQL are intended to run through Docker.

```bash
export AIRFLOW_UID=$(id -u)
docker compose up --build airflow-init
docker compose up --build
```

Open Airflow at `http://localhost:8080`.

Default local Airflow login:

```text
username: admin
password: admin
```

Enable the DAG named `financial_market_daily_etl`.

## Run The Pipeline Manually

Start PostgreSQL first:

```bash
make postgres-up
```

Create a local Python environment:

```bash
make setup
```

Run the free Alpha Vantage daily update:

```bash
make run
```

Run full historical output only if your Alpha Vantage plan supports it:

```bash
PYTHONPATH=src python -m market_etl.pipeline --output-size full
```

Run specific tickers:

```bash
PYTHONPATH=src python -m market_etl.pipeline --tickers AAPL,NVDA --output-size compact
```

## Demo Mode

The project includes a no-API-key demo using `tests/fixtures/alpha_vantage_daily_aapl.json`.

```bash
make setup
make demo
```

Demo mode still uses the real transformation, Pandera validation, raw-response retention, and PostgreSQL upsert path. The only difference is that extraction reads a checked-in fixture instead of calling Alpha Vantage.

## Database Tables

`raw_api_responses`

- Stores provider, ticker, request timestamp, response status, raw file path, and response metadata.

`market_prices`

- Stores cleaned daily market observations.
- Has a unique constraint on `ticker + trading_date`.
- Uses PostgreSQL upsert so reruns update existing observations instead of creating duplicates.

## Data Quality Checks

The Pandera validation layer checks:

- required columns
- ticker format
- non-null trading dates
- positive prices
- nonnegative volume
- `high >= low`
- `high >= open and close`
- `low <= open and close`
- no duplicate `ticker + trading_date` rows inside a batch
- source is `alpha_vantage`

## Failure Behavior

Each ticker is retried with exponential backoff. If the API still fails:

- the failure is logged
- existing database records are left untouched
- the Airflow task fails so the problem is visible
- other tickers are attempted before the final failure is raised

Alpha Vantage rate-limit messages are treated as failures and retried according to the configured retry settings.

## Tests

Run unit tests:

```bash
make test-unit
```

Run integration tests against PostgreSQL:

```bash
make test-integration
```

Run everything:

```bash
make test
```

Integration tests are skipped unless `RUN_INTEGRATION_TESTS=true`. GitHub Actions runs the unit test suite on pushes and pull requests.

## Configuration

Environment variables are loaded from `.env`:

```text
ALPHA_VANTAGE_API_KEY
TICKERS
ALPHA_VANTAGE_OUTPUT_SIZE
DATABASE_URL
RAW_DATA_DIR
LOG_DIR
API_MAX_RETRIES
API_BACKOFF_SECONDS
API_TIMEOUT_SECONDS
RUN_INTEGRATION_TESTS
```

Secrets are never hard-coded. `.env` is ignored by Git.

## Useful PostgreSQL Checks

Connect to the database:

```bash
docker compose exec postgres psql -U etl -d market_data
```

Check latest rows:

```sql
SELECT ticker, trading_date, close, volume, ingested_at
FROM market_prices
ORDER BY trading_date DESC, ticker
LIMIT 20;
```

Check duplicate protection:

```sql
SELECT ticker, trading_date, COUNT(*)
FROM market_prices
GROUP BY ticker, trading_date
HAVING COUNT(*) > 1;
```

That query should return zero rows.

## Design Notes

- Idempotent loads let the same ticker and trading date be reprocessed without duplicate rows.
- Raw API responses are retained so failed or suspicious transformations can be inspected later.
- Pandera catches malformed batches before load, while PostgreSQL constraints protect durable storage.
- Airflow handles scheduling and operational visibility; the ETL logic remains in normal Python modules for local testing.
- Docker Compose makes the local Airflow plus PostgreSQL stack reproducible on macOS.
- Demo mode proves the transform, validation, and load path without exposing or depending on an API key.
