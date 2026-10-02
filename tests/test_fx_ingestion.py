import pytest
import argparse
from ingestion.fx_api.load_bigquery import transform_fx_for_bigquery

from ingestion.fx_api.fetch_fx_rates import (
    build_url,
    validate_fx_data,
    validate_date,
)


def test_build_url_latest():
    assert build_url() == "https://api.frankfurter.app/latest"


def test_build_url_historical():
    assert (
        build_url("2025-01-15")
        == "https://api.frankfurter.app/2025-01-15"
    )


def test_validate_fx_data():
    data = {
        "amount": 1.0,
        "base": "EUR",
        "date": "2025-01-15",
        "rates": {"USD": 1.03},
    }

    validate_fx_data(data)


def test_validate_fx_data_missing_field():
    data = {
        "amount": 1.0,
        "base": "EUR",
        "date": "2025-01-15",
    }

    with pytest.raises(ValueError):
        validate_fx_data(data)


def test_validate_date():
    assert validate_date("2025-01-15") == "2025-01-15"


def test_validate_invalid_date():
    with pytest.raises(argparse.ArgumentTypeError):
        validate_date("not-a-date")


def test_transform_fx_for_bigquery():
    data = {
        "amount": 1.0,
        "base": "EUR",
        "date": "2025-01-15",
        "rates": {
            "USD": 1.03,
            "GBP": 0.84,
        },
    }

    rows = transform_fx_for_bigquery(data)

    assert len(rows) == 2
    assert rows[0]["rate_date"] == "2025-01-15"
    assert rows[0]["base_currency"] == "EUR"
    assert rows[0]["source"] == "frankfurter"


def test_transform_fx_contains_target_currency():
    data = {
        "amount": 1.0,
        "base": "EUR",
        "date": "2025-01-15",
        "rates": {
            "USD": 1.03,
        },
    }

    rows = transform_fx_for_bigquery(data)

    assert rows[0]["target_currency"] == "USD"
    assert rows[0]["rate"] == 1.03