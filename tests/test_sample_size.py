"""Verify planning results, achieved power, input validation, and the CLI."""

import math
import subprocess
import sys
import warnings

import pytest
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize
from statsmodels.tools.sm_exceptions import ConvergenceWarning

from experimentation.sample_size import calculate_sample_size, main


def test_default_example():
    result = calculate_sample_size()

    assert result.sample_size_per_group == 4433
    assert result.total_sample_size == 8866
    assert result.absolute_uplift_percentage_points == pytest.approx(2.0)
    assert result.relative_uplift_percent == pytest.approx(100 / 6)
    assert isinstance(result.sample_size_per_group, int)
    assert result == calculate_sample_size()  # Deterministic, no simulation.


@pytest.mark.parametrize("baseline,treatment,power,alpha", [
    (0.12, 0.14, 0.80, 0.05),
    (0.50, 0.55, 0.90, 0.01),
    (0.03, 0.02, 0.85, 0.05),
])
def test_rounded_count_reaches_power_and_previous_integer_does_not(
    baseline, treatment, power, alpha,
):
    result = calculate_sample_size(baseline, treatment, power=power, alpha=alpha)
    solver = NormalIndPower()
    effect_size = abs(proportion_effectsize(treatment, baseline))

    def achieved_power(count):
        return solver.power(effect_size, count, alpha, ratio=1.0,
                            alternative="two-sided")

    assert achieved_power(result.sample_size_per_group) >= power
    assert achieved_power(result.sample_size_per_group - 1) < power
    assert result.total_sample_size == 2 * result.sample_size_per_group


def test_treatment_decrease_has_same_sample_size_and_signed_uplift():
    increase = calculate_sample_size(0.12, 0.14)
    decrease = calculate_sample_size(0.14, 0.12)

    assert decrease.sample_size_per_group == increase.sample_size_per_group
    assert decrease.absolute_uplift_percentage_points == pytest.approx(-2)
    assert decrease.relative_uplift_percent == pytest.approx(-100 / 7)


def test_more_demanding_designs_require_more_participants():
    default = calculate_sample_size().sample_size_per_group

    assert calculate_sample_size(treatment=0.13).sample_size_per_group > default
    assert calculate_sample_size(power=0.90).sample_size_per_group > default
    assert calculate_sample_size(alpha=0.01).sample_size_per_group > default


@pytest.mark.parametrize("field", ["baseline", "treatment", "power", "alpha"])
@pytest.mark.parametrize("value", [
    -0.1, 0.0, 1.0, 1.1, float("nan"), float("inf"),
    float("-inf"), True, "0.12", None,
])
def test_invalid_probabilities_are_rejected(field, value):
    with pytest.raises(ValueError, match=field):
        calculate_sample_size(**{field: value})


def test_identical_rates_are_rejected():
    with pytest.raises(ValueError, match="must differ"):
        calculate_sample_size(0.12, 0.12)


@pytest.mark.parametrize("power", [0.04, 0.05])
def test_power_at_or_below_alpha_is_rejected(power):
    with pytest.raises(ValueError, match="power must exceed alpha"):
        calculate_sample_size(power=power, alpha=0.05)


def test_numerically_indistinguishable_rates_are_rejected():
    with pytest.raises(ValueError, match="too close"):
        calculate_sample_size(0.5, math.nextafter(0.5, 1.0))


@pytest.mark.parametrize("solver_result", [float("nan"), float("inf"), 0, -1])
def test_invalid_solver_results_are_rejected(monkeypatch, solver_result):
    monkeypatch.setattr(NormalIndPower, "solve_power",
                        lambda *args, **kwargs: solver_result)
    with pytest.raises(ValueError, match="finite positive"):
        calculate_sample_size()


def test_nonconvergence_becomes_a_clear_validation_error(monkeypatch):
    def fail_to_converge(*args, **kwargs):
        warnings.warn("Failed to converge", ConvergenceWarning)
        return 10

    monkeypatch.setattr(NormalIndPower, "solve_power", fail_to_converge)
    with pytest.raises(ValueError, match="Unable to solve"):
        calculate_sample_size()


def test_incorrect_solver_root_is_rejected(monkeypatch):
    monkeypatch.setattr(NormalIndPower, "solve_power", lambda *args, **kwargs: 10)
    with pytest.raises(ValueError, match="requested power reliably"):
        calculate_sample_size()


@pytest.mark.parametrize("arguments", [
    [],
    ["--baseline", "0.12", "--treatment", "0.14", "--alpha", "0.05",
     "--power", "0.80"],
])
def test_module_cli_default_example(arguments):
    process = subprocess.run(
        [sys.executable, "-m", "experimentation.sample_size", *arguments],
        capture_output=True, text=True, check=True,
    )
    assert "Required sample size per group: 4433" in process.stdout
    assert "Required total sample size: 8866" in process.stdout
    assert "Absolute uplift: 2 percentage points" in process.stdout
    assert "Relative uplift: 16.6667%" in process.stdout
    assert process.stderr == ""


def test_cli_custom_arguments(capsys):
    result = calculate_sample_size(0.20, 0.18, alpha=0.01, power=0.90)
    assert main(["--baseline", "0.20", "--treatment", "0.18",
                 "--alpha", "0.01", "--power", "0.90"]) == 0
    output = capsys.readouterr().out
    assert f"Required sample size per group: {result.sample_size_per_group}" in output
    assert "Absolute uplift: -2 percentage points" in output
    assert "Relative uplift: -10%" in output


@pytest.mark.parametrize("arguments", [
    ["--baseline", "12"], ["--treatment", "0.12"],
    ["--power", "nan"], ["--alpha", "not-a-number"],
])
def test_cli_invalid_arguments_exit_cleanly(arguments, capsys):
    with pytest.raises(SystemExit) as exc:
        main(arguments)
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "error:" in captured.err
    assert "Traceback" not in captured.err
