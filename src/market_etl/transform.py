from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


ALPHA_DAILY_KEY = "Time Series (Daily)"


def _get_required_value(values: dict[str, Any], field_names: tuple[str, ...], ticker: str, trading_date: str) -> Any:
    for field_name in field_names:
        if field_name in values:
            return values[field_name]
    raise KeyError(f"Missing one of {field_names} for {ticker} on {trading_date}")


def transform_alpha_vantage_daily(
    ticker: str,
    payload: dict[str, Any],
    raw_file_path: Path | None = None,
) -> pd.DataFrame:
    if ALPHA_DAILY_KEY not in payload:
        raise ValueError(f"Payload for {ticker} is missing '{ALPHA_DAILY_KEY}'.")

    rows: list[dict[str, Any]] = []
    for trading_date, values in payload[ALPHA_DAILY_KEY].items():
        close = float(values["4. close"])
        adjusted_close = float(values.get("5. adjusted close", close))
        volume = int(_get_required_value(values, ("6. volume", "5. volume"), ticker, trading_date))
        rows.append(
            {
                "ticker": ticker.upper(),
                "trading_date": pd.to_datetime(trading_date),
                "open": float(values["1. open"]),
                "high": float(values["2. high"]),
                "low": float(values["3. low"]),
                "close": close,
                "adjusted_close": adjusted_close,
                "volume": volume,
                "source": "alpha_vantage",
                "raw_file_path": str(raw_file_path) if raw_file_path else None,
            }
        )

    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame

    frame = frame.sort_values(["ticker", "trading_date"]).reset_index(drop=True)
    frame["daily_return"] = frame.groupby("ticker")["adjusted_close"].pct_change()
    frame["moving_average_7d"] = (
        frame.groupby("ticker")["adjusted_close"]
        .rolling(window=7, min_periods=1)
        .mean()
        .reset_index(level=0, drop=True)
    )
    frame["moving_average_30d"] = (
        frame.groupby("ticker")["adjusted_close"]
        .rolling(window=30, min_periods=1)
        .mean()
        .reset_index(level=0, drop=True)
    )

    return frame[
        [
            "ticker",
            "trading_date",
            "open",
            "high",
            "low",
            "close",
            "adjusted_close",
            "volume",
            "daily_return",
            "moving_average_7d",
            "moving_average_30d",
            "source",
            "raw_file_path",
        ]
    ]
