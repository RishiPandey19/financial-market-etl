# Financial Market ETL Pipeline

This is a macOS-friendly ETL project for daily U.S. stock-market data.

It uses:

- Python 3.11+
- Alpha Vantage market-data API
- requests
- pandas
- Pandera
- SQLAlchemy
- PostgreSQL
- Apache Airflow
- Docker Compose
- pytest
- python-dotenv

The default stock universe is `AAPL, MSFT, NVDA, AMZN, GOOGL`.

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

## Technical Interview Guide

A detailed PDF explanation is included at:

```text
docs/technical-interview-guide.pdf
```

It explains the architecture, stack choices, data model, idempotency, failure handling, testing strategy, production tradeoffs, and how to rebuild the project yourself.

## Project Layout

```text
financial-market-etl/
  airflow/dags/financial_market_etl_dag.py
  data/raw/
  db/init/00-create-databases.sql
  docs/technical-interview-guide.pdf
  logs/
  src/market_etl/
  tests/
  .env.example
  .gitignore
  Dockerfile
  docker-compose.yml
  pytest.ini
  requirements.txt
```

## macOS Setup

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

Open Airflow:

```text
http://localhost:8080
```

Default local Airflow login:

```text
username: admin
password: admin
```

Enable the DAG named:

```text
financial_market_daily_etl
```

It is scheduled for:

```text
5:00 PM America/Los_Angeles, Monday through Friday
```

## Run The Pipeline Manually

Start PostgreSQL first:

```bash
docker compose up -d postgres
```

Create a local Python environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the free Alpha Vantage daily update:

```bash
PYTHONPATH=src python -m market_etl.pipeline --output-size compact
```

Run full historical output only if your Alpha Vantage plan supports it:

```bash
PYTHONPATH=src python -m market_etl.pipeline --output-size full
```

Run specific tickers:

```bash
PYTHONPATH=src python -m market_etl.pipeline --tickers AAPL,NVDA --output-size compact
```

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

## API Failure Behavior

Each ticker is retried with exponential backoff. If the API still fails:

- the failure is logged
- existing database records are left untouched
- the Airflow task fails so the problem is visible
- other tickers are attempted before the final failure is raised

Alpha Vantage rate-limit messages are treated as failures and retried according to the configured retry settings.

## Tests

Run unit tests:

```bash
source .venv/bin/activate
pytest tests/unit
```

Run integration tests against PostgreSQL:

```bash
docker compose up -d postgres
RUN_INTEGRATION_TESTS=true DATABASE_URL=postgresql+psycopg2://etl:etl@localhost:5433/market_data pytest tests/integration
```

Run everything:

```bash
pytest
```

Integration tests are skipped unless `RUN_INTEGRATION_TESTS=true`.

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
