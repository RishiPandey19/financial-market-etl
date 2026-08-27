from __future__ import annotations

import argparse
from typing import Sequence

from market_etl.config import load_settings
from market_etl.database import create_tables, get_engine, insert_raw_response, upsert_market_prices
from market_etl.extract import fetch_daily_prices
from market_etl.logging_config import configure_logging
from market_etl.transform import transform_alpha_vantage_daily
from market_etl.validate import validate_market_prices


def run_pipeline(tickers: Sequence[str] | None = None, output_size: str | None = None) -> dict[str, int]:
    settings = load_settings(require_api_key=True)
    logger = configure_logging(settings.log_dir)
    engine = get_engine(settings.database_url)
    create_tables(engine)

    selected_tickers = tuple(ticker.upper() for ticker in (tickers or settings.tickers))
    selected_output_size = output_size or settings.alpha_vantage_output_size

    logger.info("Starting market ETL for tickers=%s output_size=%s", ",".join(selected_tickers), selected_output_size)

    loaded_by_ticker: dict[str, int] = {}
    failures: dict[str, str] = {}

    for ticker in selected_tickers:
        try:
            extracted = fetch_daily_prices(
                ticker=ticker,
                api_key=settings.alpha_vantage_api_key,
                base_url=settings.alpha_vantage_base_url,
                output_size=selected_output_size,
                raw_data_dir=settings.raw_data_dir,
                max_retries=settings.api_max_retries,
                backoff_seconds=settings.api_backoff_seconds,
                timeout_seconds=settings.api_timeout_seconds,
            )
            insert_raw_response(
                engine,
                provider=extracted.provider,
                ticker=extracted.ticker,
                requested_at=extracted.requested_at,
                status_code=extracted.status_code,
                response_file_path=extracted.raw_file_path,
                response_meta={"output_size": selected_output_size},
            )
            transformed = transform_alpha_vantage_daily(extracted.ticker, extracted.payload, extracted.raw_file_path)
            validated = validate_market_prices(transformed)
            affected_rows = upsert_market_prices(engine, validated)
            loaded_by_ticker[extracted.ticker] = affected_rows
            logger.info("Loaded %s rows for %s", affected_rows, extracted.ticker)
        except Exception as exc:  # noqa: BLE001 - log every ticker and fail after all attempts.
            failures[ticker] = str(exc)
            logger.exception("Failed ETL for %s", ticker)

    if failures:
        raise RuntimeError(f"ETL failed for {len(failures)} ticker(s): {failures}")

    logger.info("Finished market ETL successfully: %s", loaded_by_ticker)
    return loaded_by_ticker


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the financial-market ETL pipeline.")
    parser.add_argument("--tickers", help="Comma-separated ticker list. Defaults to TICKERS in .env.")
    parser.add_argument("--output-size", choices=["compact", "full"], help="Alpha Vantage output size.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tickers = [ticker.strip() for ticker in args.tickers.split(",")] if args.tickers else None
    run_pipeline(tickers=tickers, output_size=args.output_size)


if __name__ == "__main__":
    main()
