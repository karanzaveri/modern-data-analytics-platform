from types import SimpleNamespace

import pytest

from ai.validate_insights import validate_generated_numbers


KPIS = {
    "order_month": "2018-08-01",
    "order_count": 6512,
    "delivered_order_count": 6351,
    "unique_customers": 6460,
    "delivered_revenue": 985414.28,
    "delivered_average_order_value": 155.16,
    "previous_month_revenue": 1027903.86,
    "revenue_growth_pct": -4.13,
    "previous_month_order_count": 6292,
    "order_growth_pct": 3.5,
    "delivered_merchandise_value": 838576.64,
    "delivered_freight_value": 146915.0,
}


def response(text):
    return SimpleNamespace(
        headline=text,
        summary="Monthly performance summary.",
        key_observations=[],
        watchout="Monitor performance.",
    )


@pytest.mark.parametrize(
    "text",
    [
        "Revenue growth was -4.13%.",
        "Revenue declined by 4.13 percent.",
        "August 2018 performance.",
        "Reporting month began August 1, 2018.",
        "Order growth was 3.5%.",
        "Revenue was 985,414.28 and orders were 6,512.",
        "Revenue growth was -4.1%; revenue declined by 4.1%.",
        "Revenue was 985,414.3.",
    ],
)
def test_supported_numbers_pass(text):
    validate_generated_numbers(response(text), KPIS)


@pytest.mark.parametrize(
    "text",
    [
        "Revenue increased by 7.82%.",
        "There were 9999 orders.",
        "Revenue reached $1.5M.",
        "August 2019 performance.",
        "Revenue declined by 4.130001%.",
    ],
)
def test_unsupported_numbers_are_rejected(text):
    with pytest.raises(ValueError, match="unsupported numeric values"):
        validate_generated_numbers(response(text), KPIS)


@pytest.mark.parametrize(
    "kpis, text",
    [
        ({"description": "Campaign 2018"}, "August 2018 performance."),
        ({"growth": "7.82"}, "Growth was 7.82%."),
        ({"order_month": "2018-99-01"}, "August 2018 performance."),
        ({"order_month": "2018-02-30"}, "February 2018 performance."),
        ({"order_month": "2018-08-01 extra 9999"}, "There were 9999 orders."),
        ({"enabled": True}, "Growth was 1%."),
    ],
)
def test_unstructured_or_invalid_string_values_do_not_authorize_numbers(kpis, text):
    with pytest.raises(ValueError, match="unsupported numeric values"):
        validate_generated_numbers(response(text), kpis)


@pytest.mark.parametrize("field", ["headline", "summary", "key_observations", "watchout"])
def test_all_response_fields_are_checked(field):
    insights = response("August 2018 performance.")
    invented = "There were 9999 orders."
    setattr(insights, field, [invented] if field == "key_observations" else invented)
    with pytest.raises(ValueError, match="unsupported numeric values"):
        validate_generated_numbers(insights, KPIS)


def test_combined_grounded_response_passes():
    insights = SimpleNamespace(
        headline="August 2018 revenue declined by 4.13%.",
        summary="Revenue growth was -4.13%, while order growth was 3.5%.",
        key_observations=[
            "August 2018 had 6,512 orders.",
            "There were 6,351 delivered orders and 6,460 customers.",
            "Delivered revenue was 985,414.28 with average order value 155.16.",
        ],
        watchout="Monitor the 4.13 percent revenue decline.",
    )
    validate_generated_numbers(insights, KPIS)
