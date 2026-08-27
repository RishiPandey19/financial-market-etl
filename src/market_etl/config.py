from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TICKERS = ("AAPL", "MSFT", "NVDA", "AMZN", "GOOGL")


def _split_tickers(value: str | None) -> tuple[str, ...]:
    if not value:
        return DEFAULT_TICKERS
    tickers = tuple(ticker.strip().upper() for ticker in value.split(",") if ticker.strip())
    return tickers or DEFAULT_TICKERS


def _resolve_project_path(value: str | None, default: str) -> Path:
    raw_path = Path(value or default)
    if raw_path.is_absolute():
        return raw_path
    return PROJECT_ROOT / raw_path


@dataclass(frozen=True)
class Settings:
    alpha_vantage_api_key: str
    alpha_vantage_base_url: str
    alpha_vantage_output_size: str
    tickers: tuple[str, ...]
    database_url: str
    raw_data_dir: Path
    log_dir: Path
    api_max_retries: int
    api_backoff_seconds: float
    api_timeout_seconds: float


def load_settings(require_api_key: bool = True) -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")

    api_key = os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()
    if require_api_key and not api_key:
        raise ValueError("ALPHA_VANTAGE_API_KEY is required. Copy .env.example to .env and add your key.")

    settings = Settings(
        alpha_vantage_api_key=api_key,
        alpha_vantage_base_url=os.getenv(
            "ALPHA_VANTAGE_BASE_URL",
            "https://www.alphavantage.co/query",
        ),
        alpha_vantage_output_size=os.getenv("ALPHA_VANTAGE_OUTPUT_SIZE", "compact").strip().lower(),
        tickers=_split_tickers(os.getenv("TICKERS")),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://etl:etl@localhost:5432/market_data",
        ),
        raw_data_dir=_resolve_project_path(os.getenv("RAW_DATA_DIR"), "data/raw"),
        log_dir=_resolve_project_path(os.getenv("LOG_DIR"), "logs"),
        api_max_retries=int(os.getenv("API_MAX_RETRIES", "4")),
        api_backoff_seconds=float(os.getenv("API_BACKOFF_SECONDS", "2")),
        api_timeout_seconds=float(os.getenv("API_TIMEOUT_SECONDS", "30")),
    )

    if settings.alpha_vantage_output_size not in {"compact", "full"}:
        raise ValueError("ALPHA_VANTAGE_OUTPUT_SIZE must be either 'compact' or 'full'.")

    return settings
