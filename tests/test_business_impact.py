"""Verify period-specific projections, interval transforms, and decision reporting."""

import subprocess
import sys

import pandas as pd
import pytest

from experimentation.analyze_experiment import analyze_experiment
from experimentation.business_impact import calculate_business_impact, main
from experimentation.simulate_experiment import simulate_experiment


def test_profit_and_period_costs():
    result = calculate_business_impact(0.10, 0.12, 10000, 15, 1000,
                                       ongoing_costs=500, period="one quarter")
    assert result.period == "one quarter"
    assert result.point.absolute_conversion_rate_difference == pytest.approx(0.02)
    assert result.point.expected_incremental_conversions == pytest.approx(200)
    assert result.point.expected_incremental_contribution == pytest.approx(3000)
    assert result.point.estimated_net_financial_benefit == pytest.approx(1500)
    assert result.break_even_uplift_percentage_points == pytest.approx(1)
    assert result.lower is result.upper is None


def test_break_even_uplift_covers_both_costs():
    result = calculate_business_impact(0.10, 0.11, 10000, 15, 1000, ongoing_costs=500)
    assert result.point.estimated_net_financial_benefit == pytest.approx(0, abs=1e-9)
    assert result.break_even_uplift_percentage_points == pytest.approx(1)


def test_negative_uplift_produces_lost_conversions_and_contribution():
    result = calculate_business_impact(0.12, 0.10, 10000, 15, 1000)
    assert result.point.expected_incremental_conversions == pytest.approx(-200)
    assert result.point.expected_incremental_contribution == pytest.approx(-3000)
    assert result.point.estimated_net_financial_benefit == pytest.approx(-4000)


def test_zero_uplift_still_includes_costs():
    result = calculate_business_impact(0.12, 0.12, 10000, 15, 1000, ongoing_costs=500)
    assert result.point.expected_incremental_conversions == 0
    assert result.point.estimated_net_financial_benefit == -1500


@pytest.mark.parametrize("users,profit", [(0, 12), (10000, 0), (0, 0)])
def test_zero_exposure_has_undefined_break_even(users, profit):
    result = calculate_business_impact(0.12, 0.14, users, profit, 1000)
    assert result.point.expected_incremental_contribution == 0
    assert result.point.estimated_net_financial_benefit == -1000
    assert result.break_even_uplift_percentage_points is None


def test_free_implementation_and_boundary_rates():
    result = calculate_business_impact(0, 1, 100, 12, 0)
    assert result.point.expected_incremental_conversions == 100
    assert result.point.estimated_net_financial_benefit == 1200
    assert result.break_even_uplift_percentage_points == 0


def test_confidence_interval_transformation_crossing_zero():
    result = calculate_business_impact(0.1, 0.12, 10000, 15, 1000, ongoing_costs=500,
                                       difference_confidence_interval=(-0.01, 0.05))
    assert result.lower.expected_incremental_conversions == pytest.approx(-100)
    assert result.lower.expected_incremental_contribution == pytest.approx(-1500)
    assert result.lower.estimated_net_financial_benefit == pytest.approx(-3000)
    assert result.upper.expected_incremental_conversions == pytest.approx(500)
    assert result.upper.expected_incremental_contribution == pytest.approx(7500)
    assert result.upper.estimated_net_financial_benefit == pytest.approx(6000)


@pytest.mark.parametrize("field,value", [
    ("control_rate", -0.1), ("treatment_rate", 1.1), ("control_rate", float("nan")),
    ("treatment_rate", True), ("control_rate", "0.12"),
    ("projected_eligible_users", -1), ("projected_eligible_users", 1.5),
    ("projected_eligible_users", True), ("projected_eligible_users", 2**53 + 1),
    ("contribution_profit_per_conversion", -1), ("implementation_cost", -1),
    ("ongoing_costs", -1), ("contribution_profit_per_conversion", float("inf")),
    ("implementation_cost", None), ("period", " "),
])
def test_invalid_business_inputs(field, value):
    arguments = dict(control_rate=0.12, treatment_rate=0.14, projected_eligible_users=10000,
                     contribution_profit_per_conversion=12, implementation_cost=1000)
    arguments[field] = value
    with pytest.raises(ValueError):
        calculate_business_impact(**arguments)


@pytest.mark.parametrize("bounds", [
    (), (0.01,), (0.01, 0.02, 0.03), (0.05, 0.01), (-1.1, 0.02),
    (0.01, 1.1), (float("nan"), 0.02), (0.01, float("inf")), (True, 0.1), "0.01,0.02",
])
def test_invalid_confidence_bounds(bounds):
    with pytest.raises(ValueError):
        calculate_business_impact(0.12, 0.14, 10000, 12, 1000,
                                  difference_confidence_interval=bounds)


def test_financial_overflow_is_rejected():
    with pytest.raises(ValueError, match="numeric limits"):
        calculate_business_impact(0.12, 0.14, 10000, 1e308, 1000)


def test_real_phase_2_results_feed_financial_scenarios_without_hardcoding():
    analysis = analyze_experiment(simulate_experiment())
    result = calculate_business_impact(analysis.control.conversion_rate, analysis.treatment.conversion_rate,
                                       100000, 12, 40000,
                                       difference_confidence_interval=analysis.confidence_interval)
    assert result.point.expected_incremental_conversions == pytest.approx(100000 * (603 - 527) / 4433)
    assert result.point.estimated_net_financial_benefit == pytest.approx(
        result.point.expected_incremental_conversions * 12 - 40000)
    assert result.upper.estimated_net_financial_benefit < 0
    assert result.lower.absolute_conversion_rate_difference == analysis.confidence_interval[0]
    assert result.upper.absolute_conversion_rate_difference == analysis.confidence_interval[1]


def test_decision_cli_preserves_input_and_separates_evidence(tmp_path):
    input_path = tmp_path / "experiment.csv"
    report_path = tmp_path / "report.txt"
    simulate_experiment().to_csv(input_path, index=False)
    original_bytes = input_path.read_bytes()
    process = subprocess.run(
        [sys.executable, "-m", "experimentation.business_impact", "--input", str(input_path),
         "--output", str(report_path)], capture_output=True, text=True, check=True,
    )
    assert input_path.read_bytes() == original_bytes
    report = report_path.read_text(encoding="utf-8")
    assert "Statistically significant at alpha=0.05: yes" in report
    assert "HYPOTHETICAL financial assumptions" in report
    assert "EUR -19,427.02" in report
    assert "Break-even uplift: 3.333333333 percentage points" in report
    assert "Guardrails descriptively evaluated: 0/3; missing/insufficient: 3" in report
    assert "Overall readiness: not ready" in report
    assert "were NOT observed" in report
    assert report.strip() in process.stdout
    assert process.stderr == ""


def test_positive_finances_do_not_automatically_recommend_rollout(tmp_path, capsys):
    input_path = tmp_path / "experiment.csv"
    simulate_experiment().to_csv(input_path, index=False)
    assert main(["--input", str(input_path), "--output", str(tmp_path / "report.txt"),
                 "--implementation-cost", "0", "--ongoing-costs", "100", "--period", "one month"]) == 0
    output = capsys.readouterr().out
    assert "Projected period: one month" in output
    assert "Economically attractive under assumptions (positive point-estimate net benefit): yes" in output
    assert "Overall readiness: not ready" in output


def test_report_cannot_overwrite_its_input(tmp_path, capsys):
    input_path = tmp_path / "experiment.csv"
    simulate_experiment().to_csv(input_path, index=False)
    original_bytes = input_path.read_bytes()
    with pytest.raises(SystemExit) as exc:
        main(["--input", str(input_path), "--output", str(input_path)])
    assert exc.value.code == 2
    assert input_path.read_bytes() == original_bytes
    assert "must differ" in capsys.readouterr().err


def test_invalid_financial_cli_does_not_create_report(tmp_path, capsys):
    input_path = tmp_path / "experiment.csv"
    report_path = tmp_path / "report.txt"
    simulate_experiment().to_csv(input_path, index=False)
    with pytest.raises(SystemExit) as exc:
        main(["--input", str(input_path), "--output", str(report_path), "--eligible-users", "-1"])
    assert exc.value.code == 2
    assert not report_path.exists()
    assert "projected_eligible_users" in capsys.readouterr().err
