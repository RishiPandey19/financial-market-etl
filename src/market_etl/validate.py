from __future__ import annotations

import pandas as pd

try:
    import pandera.pandas as pa
except ImportError:  # pragma: no cover - for older Pandera releases
    import pandera as pa


PRICE_COLUMNS = ["open", "high", "low", "close", "adjusted_close"]


market_price_schema = pa.DataFrameSchema(
    columns={
        "ticker": pa.Column(str, pa.Check.str_matches(r"^[A-Z.]{1,10}$"), nullable=False),
        "trading_date": pa.Column(pa.DateTime, nullable=False),
        "open": pa.Column(float, pa.Check.gt(0), nullable=False),
        "high": pa.Column(float, pa.Check.gt(0), nullable=False),
        "low": pa.Column(float, pa.Check.gt(0), nullable=False),
        "close": pa.Column(float, pa.Check.gt(0), nullable=False),
        "adjusted_close": pa.Column(float, pa.Check.gt(0), nullable=False),
        "volume": pa.Column(int, pa.Check.ge(0), nullable=False),
        "daily_return": pa.Column(float, nullable=True),
        "moving_average_7d": pa.Column(float, pa.Check.gt(0), nullable=False),
        "moving_average_30d": pa.Column(float, pa.Check.gt(0), nullable=False),
        "source": pa.Column(str, pa.Check.isin(["alpha_vantage"]), nullable=False),
        "raw_file_path": pa.Column(object, nullable=True),
    },
    checks=[
        pa.Check(lambda df: df["high"] >= df["low"], error="high must be greater than or equal to low"),
        pa.Check(lambda df: df["high"] >= df[["open", "close"]].max(axis=1), error="high must be >= open and close"),
        pa.Check(lambda df: df["low"] <= df[["open", "close"]].min(axis=1), error="low must be <= open and close"),
        pa.Check(
            lambda df: ~df.duplicated(subset=["ticker", "trading_date"]),
            error="payload contains duplicate ticker+trading_date rows",
        ),
    ],
    coerce=True,
    strict=True,
)


def validate_market_prices(frame: pd.DataFrame) -> pd.DataFrame:
    return market_price_schema.validate(frame, lazy=True)
