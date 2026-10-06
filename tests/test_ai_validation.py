from types import SimpleNamespace

import pytest

from ai.validate_insights import (
    extract_numbers,
    get_allowed_numbers,
    validate_generated_numbers,
)


def test_extract_numbers():
    text = "Revenue was 985,414.28 and growth was -4.13%."

    numbers = extract_numbers(text)

    assert 985414.28 in numbers
    assert -4.13 in numbers


def test_allowed_numbers_include_kpi_values():
    kpis = {
        "order_count": 6512,
        "revenue_growth_pct": -4.13,
        "delivered_revenue": 985414.28,
    }

    allowed = get_allowed_numbers(kpis)

    assert 6512.0 in allowed
    assert -4.13 in allowed
    assert 985414.28 in allowed


def test_valid_ai_response_passes():
    kpis = {
        "order_count": 6512,
        "revenue_growth_pct": -4.13,
        "delivered_revenue": 985414.28,
    }

    insights = SimpleNamespace(
        headline="Revenue decreased by 4.13%.",
        summary="Delivered revenue was 985,414.28 across 6,512 orders.",
        key_observations=[
            "Order count was 6,512.",
            "Revenue was 985,414.28.",
            "Growth was -4.13%.",
        ],
        watchout="Revenue declined by 4.13%.",
    )

    validate_generated_numbers(insights, kpis)


def test_fake_number_is_rejected():
    kpis = {
        "order_count": 6512,
        "delivered_revenue": 985414.28,
    }

    insights = SimpleNamespace(
        headline="Revenue reached 999999.",
        summary="Order count was 6,512.",
        key_observations=[
            "Revenue was 985,414.28.",
            "Order count was 6,512.",
            "Performance should be monitored.",
        ],
        watchout="No additional numeric claim.",
    )

    with pytest.raises(ValueError, match="unsupported numeric values"):
        validate_generated_numbers(insights, kpis)

        