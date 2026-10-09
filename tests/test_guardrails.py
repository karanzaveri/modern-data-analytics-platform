"""Verify directional, inclusive, descriptive thresholds and missing evidence."""

import pytest

from experimentation.guardrails import (
    evaluate_guardrail, illustrative_guardrail_scenarios, main, missing_checkout_guardrails,
)


def evaluate(**overrides):
    arguments = dict(name="Fixture metric", direction="lower-is-better", control_value=10,
                     treatment_value=11, max_tolerable_deterioration=1,
                     unit="milliseconds", definition="Fixture mean duration.", data_availability="available")
    arguments.update(overrides)
    return evaluate_guardrail(**arguments)


@pytest.mark.parametrize("direction,treatment,expected,deterioration", [
    ("lower-is-better", 9, "Within specified threshold", -1),
    ("lower-is-better", 11, "Within specified threshold", 1),
    ("lower-is-better", 12, "Threshold breached", 2),
    ("higher-is-better", 11, "Within specified threshold", -1),
    ("higher-is-better", 9, "Within specified threshold", 1),
    ("higher-is-better", 8, "Threshold breached", 2),
])
def test_direction_and_boundary(direction, treatment, expected, deterioration):
    result = evaluate(direction=direction, treatment_value=treatment)
    assert result.assessment == expected
    assert result.signed_deterioration == deterioration
    assert result.treatment_minus_control == treatment - 10


def test_decimal_boundary_is_not_a_false_breach():
    result = evaluate(control_value=0.1, treatment_value=0.2, max_tolerable_deterioration=0.1)
    assert result.assessment == "Within specified threshold"
    result = evaluate(control_value=1.1, treatment_value=1.3, max_tolerable_deterioration=0.2)
    assert result.assessment == "Within specified threshold"


def test_zero_tolerance_does_not_accept_deterioration():
    assert evaluate(control_value=0, treatment_value=0, max_tolerable_deterioration=0).assessment == "Within specified threshold"
    assert evaluate(control_value=0, treatment_value=1e-15, max_tolerable_deterioration=0).assessment == "Threshold breached"


@pytest.mark.parametrize("overrides", [
    {"data_availability": "missing"}, {"data_availability": "incomplete"},
    {"control_value": None}, {"treatment_value": None},
    {"control_value": None, "treatment_value": None},
])
def test_missing_and_incomplete_data_are_not_passed(overrides):
    result = evaluate(**overrides)
    assert result.assessment == "Insufficient data"
    assert result.signed_deterioration is None
    assert result.treatment_minus_control is None


@pytest.mark.parametrize("overrides", [
    {"name": " "}, {"unit": ""}, {"definition": None}, {"direction": "unknown"},
    {"data_availability": "unknown"}, {"max_tolerable_deterioration": -1},
    {"max_tolerable_deterioration": True}, {"max_tolerable_deterioration": float("inf")},
    {"control_value": float("nan")}, {"treatment_value": float("inf")},
    {"control_value": "10"}, {"treatment_value": True},
])
def test_invalid_guardrail_inputs(overrides):
    with pytest.raises(ValueError):
        evaluate(**overrides)


def test_original_guardrails_all_missing_and_examples_separate():
    original = missing_checkout_guardrails()
    assert len(original) == 3
    assert all(result.assessment == "Insufficient data" for result in original)
    assert all(result.control_value is result.treatment_value is None for result in original)
    examples = illustrative_guardrail_scenarios()
    assert [result.assessment for result in examples] == [
        "Within specified threshold", "Threshold breached", "Insufficient data",
    ]
    assert all(result.control_value is None for result in original)


def test_guardrail_cli_labels_illustrations_and_avoids_safety_claim(capsys):
    assert main([]) == 0
    report = capsys.readouterr().out
    assert "HYPOTHETICAL EXAMPLES ONLY" in report
    assert "were NOT observed in the original conversion dataset" in report
    assert "does not establish statistical safety" in report
