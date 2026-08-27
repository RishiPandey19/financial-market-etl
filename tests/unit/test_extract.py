from __future__ import annotations

import json
from pathlib import Path

import pytest
import requests

from market_etl.extract import AlphaVantageError, fetch_daily_prices


def sample_payload() -> dict:
    return {
        "Meta Data": {"2. Symbol": "AAPL"},
        "Time Series (Daily)": {
            "2024-01-02": {
                "1. open": "187.1500",
                "2. high": "188.4400",
                "3. low": "183.8900",
                "4. close": "185.6400",
                "5. adjusted close": "185.6400",
                "6. volume": "82488700",
            }
        },
    }


class FakeResponse:
    status_code = 200

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class FlakySession:
    def __init__(self) -> None:
        self.calls = 0

    def get(self, *args, **kwargs) -> FakeResponse:
        self.calls += 1
        if self.calls == 1:
            raise requests.Timeout("temporary timeout")
        return FakeResponse(sample_payload())


def test_fetch_retries_and_writes_raw_payload(tmp_path: Path) -> None:
    session = FlakySession()

    extracted = fetch_daily_prices(
        ticker="aapl",
        api_key="demo",
        base_url="https://example.test/query",
        output_size="compact",
        raw_data_dir=tmp_path,
        max_retries=2,
        backoff_seconds=0,
        timeout_seconds=1,
        session=session,  # type: ignore[arg-type]
    )

    assert session.calls == 2
    assert extracted.ticker == "AAPL"
    assert extracted.raw_file_path.exists()
    assert json.loads(extracted.raw_file_path.read_text(encoding="utf-8"))["Time Series (Daily)"]


def test_fetch_fails_on_alpha_vantage_error_message(tmp_path: Path) -> None:
    class ErrorSession:
        def get(self, *args, **kwargs) -> FakeResponse:
            return FakeResponse({"Error Message": "Invalid API call."})

    with pytest.raises(AlphaVantageError):
        fetch_daily_prices(
            ticker="BAD",
            api_key="demo",
            base_url="https://example.test/query",
            output_size="compact",
            raw_data_dir=tmp_path,
            max_retries=1,
            backoff_seconds=0,
            timeout_seconds=1,
            session=ErrorSession(),  # type: ignore[arg-type]
        )
