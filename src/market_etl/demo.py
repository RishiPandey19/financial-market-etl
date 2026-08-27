from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from market_etl.config import PROJECT_ROOT, load_settings
from market_etl.database import create_tables, get_engine, insert_raw_response, upsert_market_prices
from market_etl.extract import save_raw_payload
from market_etl.logging_config import configure_logging
from market_etl.transform import transform_alpha_vantage_daily
from market_etl.validate import validate_market_prices


DEFAULT_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "alpha_vantage_daily_aapl.json"


def load_demo_payload(fixture_path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def run_demo(fixture_path: Path = DEFAULT_FIXTURE, ticker: str = "AAPL") -> dict[str, int | str]:
    settings = load_settings(require_api_key=False)
    logger = configure_logging(settings.log_dir)
    engine = get_engine(settings.database_url)
    create_tables(engine)

    payload = load_demo_payload(fixture_path)
    requested_at = datetime.now(timezone.utc)
    raw_file_path = save_raw_payload(settings.raw_data_dir, ticker, requested_at, payload)

    insert_raw_response(
        engine,
        provider="alpha_vantage",
        ticker=ticker,
        requested_at=requested_at,
        status_code=200,
        response_file_path=raw_file_path,
        response_meta={"demo": True, "fixture": str(fixture_path)},
    )

    transformed = transform_alpha_vantage_daily(ticker, payload, raw_file_path)
    validated = validate_market_prices(transformed)
    affected_rows = upsert_market_prices(engine, validated)

    logger.info("Loaded %s demo rows for %s from %s", affected_rows, ticker, fixture_path)
    return {"ticker": ticker.upper(), "rows": affected_rows, "raw_file": str(raw_file_path)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the ETL pipeline with a local fixture instead of the live API.")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE, help="Path to an Alpha Vantage daily JSON fixture.")
    parser.add_argument("--ticker", default="AAPL", help="Ticker symbol to assign to the demo payload.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_demo(fixture_path=args.fixture, ticker=args.ticker)
    print(f"Loaded {result['rows']} demo rows for {result['ticker']}. Raw copy: {result['raw_file']}")


if __name__ == "__main__":
    main()
