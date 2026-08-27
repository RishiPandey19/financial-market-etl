CREATE USER etl WITH PASSWORD 'etl';

CREATE DATABASE airflow OWNER postgres;
CREATE DATABASE market_data OWNER etl;

\connect market_data

CREATE TABLE IF NOT EXISTS raw_api_responses (
    id BIGSERIAL PRIMARY KEY,
    provider TEXT NOT NULL,
    ticker TEXT NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL,
    status_code INTEGER,
    response_file_path TEXT NOT NULL,
    response_meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_api_responses_ticker_requested_at
    ON raw_api_responses (ticker, requested_at DESC);

CREATE TABLE IF NOT EXISTS market_prices (
    id BIGSERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    trading_date DATE NOT NULL,
    open NUMERIC(18, 6) NOT NULL,
    high NUMERIC(18, 6) NOT NULL,
    low NUMERIC(18, 6) NOT NULL,
    close NUMERIC(18, 6) NOT NULL,
    adjusted_close NUMERIC(18, 6),
    volume BIGINT NOT NULL,
    daily_return NUMERIC(18, 10),
    moving_average_7d NUMERIC(18, 6),
    moving_average_30d NUMERIC(18, 6),
    source TEXT NOT NULL DEFAULT 'alpha_vantage',
    raw_file_path TEXT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_market_prices_ticker_trading_date UNIQUE (ticker, trading_date),
    CONSTRAINT chk_market_prices_high_low CHECK (high >= low),
    CONSTRAINT chk_market_prices_nonnegative_volume CHECK (volume >= 0)
);

CREATE INDEX IF NOT EXISTS idx_market_prices_ticker_date
    ON market_prices (ticker, trading_date DESC);

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO etl;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO etl;
