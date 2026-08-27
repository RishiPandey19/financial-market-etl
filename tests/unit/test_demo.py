from __future__ import annotations

from market_etl.demo import DEFAULT_FIXTURE, load_demo_payload
from market_etl.transform import transform_alpha_vantage_daily
from market_etl.validate import validate_market_prices


def test_demo_fixture_transforms_and_validates() -> None:
    payload = load_demo_payload(DEFAULT_FIXTURE)
    frame = transform_alpha_vantage_daily("AAPL", payload)
    validated = validate_market_prices(frame)

    assert len(validated) == 5
    assert validated["ticker"].unique().tolist() == ["AAPL"]
