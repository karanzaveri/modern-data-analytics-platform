import pytest

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
        "rates": {"USD": 1.03},
    }

    with pytest.raises(ValueError):
        validate_fx_data(data)


def test_validate_date():
    assert validate_date("2025-01-15") == "2025-01-15"


def test_validate_invalid_date():
    with pytest.raises(Exception):
        validate_date("not-a-date")