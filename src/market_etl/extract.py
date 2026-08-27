from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


class AlphaVantageError(RuntimeError):
    """Raised when Alpha Vantage does not return usable market data."""


@dataclass(frozen=True)
class ExtractedPayload:
    ticker: str
    payload: dict[str, Any]
    requested_at: datetime
    status_code: int
    raw_file_path: Path
    provider: str = "alpha_vantage"


def _raise_for_api_message(payload: dict[str, Any], ticker: str) -> None:
    if "Error Message" in payload:
        raise AlphaVantageError(f"Alpha Vantage rejected ticker {ticker}: {payload['Error Message']}")
    if "Information" in payload:
        raise AlphaVantageError(f"Alpha Vantage returned an information message for {ticker}: {payload['Information']}")
    if "Note" in payload:
        raise AlphaVantageError(f"Alpha Vantage rate limit or notice for {ticker}: {payload['Note']}")
    if "Time Series (Daily)" not in payload:
        raise AlphaVantageError(f"Alpha Vantage response for {ticker} did not include daily time series data.")


def fetch_daily_prices(
    *,
    ticker: str,
    api_key: str,
    base_url: str,
    output_size: str,
    raw_data_dir: Path,
    max_retries: int,
    backoff_seconds: float,
    timeout_seconds: float,
    session: requests.Session | None = None,
) -> ExtractedPayload:
    """Fetch daily OHLCV prices and persist the raw JSON response."""
    ticker = ticker.upper()
    client = session or requests.Session()
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": ticker,
        "outputsize": output_size,
        "apikey": api_key,
    }

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        requested_at = datetime.now(timezone.utc)
        try:
            response = client.get(base_url, params=params, timeout=timeout_seconds)
            response.raise_for_status()
            payload = response.json()
            _raise_for_api_message(payload, ticker)
            raw_file_path = save_raw_payload(raw_data_dir, ticker, requested_at, payload)
            return ExtractedPayload(
                ticker=ticker,
                payload=payload,
                requested_at=requested_at,
                status_code=response.status_code,
                raw_file_path=raw_file_path,
            )
        except (requests.RequestException, ValueError, AlphaVantageError) as exc:
            last_error = exc
            if attempt == max_retries:
                break
            sleep_seconds = backoff_seconds * (2 ** (attempt - 1))
            time.sleep(sleep_seconds)

    raise AlphaVantageError(f"Failed to extract daily data for {ticker} after {max_retries} attempts.") from last_error


def save_raw_payload(raw_data_dir: Path, ticker: str, requested_at: datetime, payload: dict[str, Any]) -> Path:
    ticker_dir = raw_data_dir / ticker.upper()
    ticker_dir.mkdir(parents=True, exist_ok=True)
    timestamp = requested_at.strftime("%Y%m%dT%H%M%SZ")
    raw_file_path = ticker_dir / f"{ticker.upper()}_{timestamp}.json"
    raw_file_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return raw_file_path
