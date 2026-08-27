from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    MetaData,
    Numeric,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.engine import Engine


metadata = MetaData()

raw_api_responses = Table(
    "raw_api_responses",
    metadata,
    # SQLAlchemy creates the autoincrementing primary key for PostgreSQL.
    # This table keeps searchable metadata for the raw JSON files retained on disk.
    Column("id", BigInteger, primary_key=True),
    Column("provider", Text, nullable=False),
    Column("ticker", Text, nullable=False),
    Column("requested_at", DateTime(timezone=True), nullable=False),
    Column("status_code", Integer),
    Column("response_file_path", Text, nullable=False),
    Column("response_meta", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Index("idx_raw_api_responses_ticker_requested_at", "ticker", "requested_at"),
)

market_prices = Table(
    "market_prices",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("ticker", Text, nullable=False),
    Column("trading_date", Date, nullable=False),
    Column("open", Numeric(18, 6), nullable=False),
    Column("high", Numeric(18, 6), nullable=False),
    Column("low", Numeric(18, 6), nullable=False),
    Column("close", Numeric(18, 6), nullable=False),
    Column("adjusted_close", Numeric(18, 6)),
    Column("volume", BigInteger, nullable=False),
    Column("daily_return", Numeric(18, 10)),
    Column("moving_average_7d", Numeric(18, 6)),
    Column("moving_average_30d", Numeric(18, 6)),
    Column("source", Text, nullable=False),
    Column("raw_file_path", Text),
    Column("ingested_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    UniqueConstraint("ticker", "trading_date", name="uq_market_prices_ticker_trading_date"),
    CheckConstraint("high >= low", name="chk_market_prices_high_low"),
    CheckConstraint("volume >= 0", name="chk_market_prices_nonnegative_volume"),
    Index("idx_market_prices_ticker_date", "ticker", "trading_date"),
)


def get_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True, future=True)


def create_tables(engine: Engine) -> None:
    metadata.create_all(engine)


def insert_raw_response(
    engine: Engine,
    *,
    provider: str,
    ticker: str,
    requested_at: datetime,
    status_code: int,
    response_file_path: Path,
    response_meta: dict[str, Any] | None = None,
) -> None:
    row = {
        "provider": provider,
        "ticker": ticker.upper(),
        "requested_at": requested_at,
        "status_code": status_code,
        "response_file_path": str(response_file_path),
        "response_meta": response_meta or {},
    }
    with engine.begin() as connection:
        connection.execute(raw_api_responses.insert().values(row))


def upsert_market_prices(engine: Engine, frame: pd.DataFrame) -> int:
    if frame.empty:
        return 0

    records = _records_for_database(frame)
    statement = insert(market_prices).values(records)
    updatable_columns = {
        column.name: getattr(statement.excluded, column.name)
        for column in market_prices.columns
        if column.name not in {"id", "ticker", "trading_date"}
    }
    updatable_columns["ingested_at"] = func.now()

    statement = statement.on_conflict_do_update(
        constraint="uq_market_prices_ticker_trading_date",
        set_=updatable_columns,
    )

    with engine.begin() as connection:
        result = connection.execute(statement)
    return int(result.rowcount or 0)


def _records_for_database(frame: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for record in frame.to_dict(orient="records"):
        trading_date = record["trading_date"]
        if hasattr(trading_date, "date"):
            record["trading_date"] = trading_date.date()

        for optional_column in ("daily_return", "moving_average_7d", "moving_average_30d"):
            value = record.get(optional_column)
            if pd.isna(value):
                record[optional_column] = None

        records.append(record)
    return records
