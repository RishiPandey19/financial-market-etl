from __future__ import annotations

from datetime import datetime

import pendulum
from airflow.decorators import dag, task

from market_etl.pipeline import run_pipeline


LOCAL_TZ = pendulum.timezone("America/Los_Angeles")


@dag(
    dag_id="financial_market_daily_etl",
    description="Fetch, validate, and load daily Alpha Vantage market prices after U.S. market close.",
    start_date=datetime(2024, 1, 1, tzinfo=LOCAL_TZ),
    schedule="0 17 * * 1-5",
    catchup=False,
    max_active_runs=1,
    tags=["finance", "etl", "alpha-vantage"],
)
def financial_market_daily_etl():
    @task
    def extract_transform_load() -> dict[str, int]:
        return run_pipeline()

    extract_transform_load()


financial_market_daily_etl()
