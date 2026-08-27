from __future__ import annotations

import os

import pandas as pd
import pytest
from sqlalchemy import text

from market_etl.database import create_tables, get_engine, market_prices, upsert_market_prices
from market_etl.validate import validate_market_prices


pytestmark = pytest.mark.integration


def test_upsert_prevents_duplicate_ticker_trading_date_records() -> None:
    if os.getenv("RUN_INTEGRATION_TESTS", "false").lower() != "true":
        pytest.skip("Set RUN_INTEGRATION_TESTS=true and DATABASE_URL to run integration tests.")

    engine = get_engine(os.environ["DATABASE_URL"])
    create_tables(engine)

    frame = pd.DataFrame(
        [
            {
                "ticker": "AAPL",
                "trading_date": pd.Timestamp("2024-01-02"),
                "open": 187.15,
                "high": 188.44,
                "low": 183.89,
                "close": 185.64,
                "adjusted_close": 185.64,
                "volume": 82488700,
                "daily_return": None,
                "moving_average_7d": 185.64,
                "moving_average_30d": 185.64,
                "source": "alpha_vantage",
                "raw_file_path": None,
            }
        ]
    )
    validated = validate_market_prices(frame)

    with engine.begin() as connection:
        connection.execute(market_prices.delete().where(market_prices.c.ticker == "AAPL"))

    upsert_market_prices(engine, validated)
    updated = validated.copy()
    updated.loc[0, "close"] = 186.0
    updated.loc[0, "adjusted_close"] = 186.0
    upsert_market_prices(engine, updated)

    with engine.begin() as connection:
        count = connection.execute(
            text("SELECT COUNT(*) FROM market_prices WHERE ticker = 'AAPL' AND trading_date = '2024-01-02'")
        ).scalar_one()
        close = connection.execute(
            text("SELECT close FROM market_prices WHERE ticker = 'AAPL' AND trading_date = '2024-01-02'")
        ).scalar_one()

    assert count == 1
    assert float(close) == 186.0
