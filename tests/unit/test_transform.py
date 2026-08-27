from __future__ import annotations

from market_etl.transform import transform_alpha_vantage_daily


def sample_payload() -> dict:
    return {
        "Meta Data": {"2. Symbol": "AAPL"},
        "Time Series (Daily)": {
            "2024-01-03": {
                "1. open": "184.2200",
                "2. high": "185.8800",
                "3. low": "183.4300",
                "4. close": "184.2500",
                "5. adjusted close": "184.2500",
                "6. volume": "58414500",
            },
            "2024-01-02": {
                "1. open": "187.1500",
                "2. high": "188.4400",
                "3. low": "183.8900",
                "4. close": "185.6400",
                "5. adjusted close": "185.6400",
                "6. volume": "82488700",
            },
        },
    }


def free_daily_payload() -> dict:
    return {
        "Meta Data": {"2. Symbol": "AAPL"},
        "Time Series (Daily)": {
            "2024-01-02": {
                "1. open": "187.1500",
                "2. high": "188.4400",
                "3. low": "183.8900",
                "4. close": "185.6400",
                "5. volume": "82488700",
            },
        },
    }


def test_transform_orders_rows_and_adds_metrics() -> None:
    frame = transform_alpha_vantage_daily("aapl", sample_payload())

    assert list(frame["ticker"]) == ["AAPL", "AAPL"]
    assert list(frame["trading_date"].dt.strftime("%Y-%m-%d")) == ["2024-01-02", "2024-01-03"]
    assert frame.loc[0, "daily_return"] != frame.loc[0, "daily_return"]
    assert round(frame.loc[1, "daily_return"], 6) == round((184.25 / 185.64) - 1, 6)
    assert frame.loc[1, "moving_average_7d"] == (185.64 + 184.25) / 2


def test_transform_accepts_free_daily_payload_shape() -> None:
    frame = transform_alpha_vantage_daily("aapl", free_daily_payload())

    assert frame.loc[0, "close"] == 185.64
    assert frame.loc[0, "adjusted_close"] == 185.64
    assert frame.loc[0, "volume"] == 82488700


def test_transform_requires_daily_series() -> None:
    try:
        transform_alpha_vantage_daily("AAPL", {"Meta Data": {}})
    except ValueError as exc:
        assert "Time Series (Daily)" in str(exc)
    else:
        raise AssertionError("Expected ValueError for missing time series")
