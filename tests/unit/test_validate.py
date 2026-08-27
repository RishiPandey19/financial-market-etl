from __future__ import annotations

import pandas as pd
import pytest
from pandera.errors import SchemaErrors

from market_etl.validate import validate_market_prices


def valid_frame() -> pd.DataFrame:
    return pd.DataFrame(
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


def test_validate_accepts_valid_market_prices() -> None:
    validated = validate_market_prices(valid_frame())
    assert len(validated) == 1


def test_validate_rejects_invalid_high_low_relationship() -> None:
    frame = valid_frame()
    frame.loc[0, "high"] = 180.0

    with pytest.raises(SchemaErrors):
        validate_market_prices(frame)
