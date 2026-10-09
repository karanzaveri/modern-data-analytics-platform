"""Check deterministic simulation and validated B-minus-A statistical analysis."""

import math
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from experimentation.analyze_experiment import (
    analyze_experiment,
    format_summary,
    main as analyze_main,
    validate_experiment_data,
)
from experimentation.sample_size import calculate_sample_size
from experimentation.simulate_experiment import (
    main as simulate_main,
    simulate_experiment,
)


def experiment_from_counts(a_conversions, b_conversions, a_users=100, b_users=100):
    """Build an artificial test fixture with known counts, not product data."""
    return pd.DataFrame({
        "user_id": [f"fixture_{i}" for i in range(a_users + b_users)],
        "variant": ["A"] * a_users + ["B"] * b_users,
        "converted": ([1] * a_conversions + [0] * (a_users - a_conversions)
                      + [1] * b_conversions + [0] * (b_users - b_conversions)),
    })


def test_default_simulation_reproduces_specification_and_observed_counts():
    data = simulate_experiment()
    pd.testing.assert_frame_equal(data, simulate_experiment(seed=42))
    assert list(data.columns) == ["user_id", "variant", "converted"]
    expected_size = calculate_sample_size().sample_size_per_group
    assert data.groupby("variant").size().to_dict() == {"A": expected_size, "B": expected_size}
    assert len(data) == 8866
    assert data["user_id"].is_unique
    assert set(data["converted"]) == {0, 1}
    assert not data.isna().any().any()
    # Regression for the explicit PCG64/binomial draw order, not hardcoded production output.
    assert data.groupby("variant")["converted"].sum().to_dict() == {"A": 527, "B": 603}
    validate_experiment_data(data)


def test_different_seed_changes_outcomes_but_not_assignment():
    first, second = simulate_experiment(seed=42), simulate_experiment(seed=43)
    pd.testing.assert_frame_equal(first[["user_id", "variant"]], second[["user_id", "variant"]])
    assert not first["converted"].equals(second["converted"])


def test_simulation_does_not_change_global_numpy_random_state():
    before = np.random.get_state()
    simulate_experiment(100)
    after = np.random.get_state()
    assert before[0] == after[0]
    np.testing.assert_array_equal(before[1], after[1])
    assert before[2:] == after[2:]


@pytest.mark.parametrize("count", [0, -1, True, 1.5, "100"])
def test_invalid_simulation_counts(count):
    with pytest.raises(ValueError, match="positive integer"):
        simulate_experiment(count)


@pytest.mark.parametrize("seed", [-1, True, 1.5, "42", None])
def test_invalid_seeds(seed):
    with pytest.raises(ValueError, match="non-negative integer"):
        simulate_experiment(100, seed=seed)


def test_group_counts_rates_and_signed_uplift():
    result = analyze_experiment(experiment_from_counts(20, 15, 100, 50))
    assert (result.control.users, result.control.conversions) == (100, 20)
    assert (result.treatment.users, result.treatment.conversions) == (50, 15)
    assert result.control.conversion_rate == pytest.approx(0.20)
    assert result.treatment.conversion_rate == pytest.approx(0.30)
    assert result.absolute_uplift_percentage_points == pytest.approx(10)
    assert result.relative_uplift_percent == pytest.approx(50)


def test_pooled_two_sided_z_test_matches_independent_formula():
    result = analyze_experiment(experiment_from_counts(100, 160, 1000, 1000))
    pooled_rate = 260 / 2000
    expected_z = (0.16 - 0.10) / math.sqrt(pooled_rate * (1 - pooled_rate) * (2 / 1000))
    expected_p = math.erfc(abs(expected_z) / math.sqrt(2))
    assert result.z_statistic == pytest.approx(expected_z)
    assert result.p_value == pytest.approx(expected_p)
    assert result.statistically_significant is True
    assert result.confidence_interval[0] > 0


def test_equal_observed_rates_are_not_significant():
    result = analyze_experiment(experiment_from_counts(20, 20))
    assert result.z_statistic == pytest.approx(0)
    assert result.p_value == pytest.approx(1)
    assert result.statistically_significant is False
    assert result.absolute_uplift_percentage_points == pytest.approx(0)
    assert result.relative_uplift_percent == pytest.approx(0)
    lower, upper = result.confidence_interval
    assert lower < 0 < upper
    assert "does not establish equality" in format_summary(result)


def test_decrease_reverses_z_and_confidence_interval_but_preserves_p_value():
    data = experiment_from_counts(100, 160, 1000, 1000)
    forward = analyze_experiment(data)
    reversed_data = data.assign(variant=data["variant"].map({"A": "B", "B": "A"}))
    reverse = analyze_experiment(reversed_data)
    assert reverse.z_statistic == pytest.approx(-forward.z_statistic)
    assert reverse.p_value == pytest.approx(forward.p_value)
    assert reverse.confidence_interval == pytest.approx(
        (-forward.confidence_interval[1], -forward.confidence_interval[0]),
    )
    assert reverse.absolute_uplift_percentage_points == pytest.approx(-6)
    assert reverse.relative_uplift_percent == pytest.approx(-37.5)
    assert reverse.statistically_significant is True
    assert "observed B is lower than A" in format_summary(reverse)


def test_newcombe_interval_matches_independent_wilson_construction():
    result = analyze_experiment(experiment_from_counts(20, 35))
    z = 1.959963984540054  # Standard normal 97.5th percentile.

    def wilson_bounds(rate, count):
        denominator = 1 + z * z / count
        center = (rate + z * z / (2 * count)) / denominator
        half_width = z * math.sqrt(rate * (1 - rate) / count + z * z / (4 * count**2)) / denominator
        return center - half_width, center + half_width

    a_lower, a_upper = wilson_bounds(0.20, 100)
    b_lower, b_upper = wilson_bounds(0.35, 100)
    lower = 0.15 - math.sqrt((0.35 - b_lower)**2 + (a_upper - 0.20)**2)
    upper = 0.15 + math.sqrt((b_upper - 0.35)**2 + (0.20 - a_lower)**2)
    assert result.confidence_interval == pytest.approx((lower, upper))


@pytest.mark.parametrize("column", ["user_id", "variant", "converted"])
def test_missing_columns_are_rejected(column):
    with pytest.raises(ValueError, match="Missing required columns"):
        analyze_experiment(experiment_from_counts(20, 30).drop(columns=column))


@pytest.mark.parametrize("column", ["user_id", "variant", "converted"])
def test_missing_values_are_rejected(column):
    data = experiment_from_counts(20, 30)
    data[column] = data[column].astype(object)
    data.loc[0, column] = None
    with pytest.raises(ValueError, match="missing values"):
        analyze_experiment(data)


@pytest.mark.parametrize("row", [1, 100])
def test_duplicate_users_in_same_or_both_groups_are_rejected(row):
    data = experiment_from_counts(20, 30)
    data.loc[row, "user_id"] = data.loc[0, "user_id"]
    with pytest.raises(ValueError, match="Duplicate user IDs"):
        analyze_experiment(data)


@pytest.mark.parametrize("variant", ["C", "a", "", 1])
def test_invalid_variants(variant):
    data = experiment_from_counts(20, 30)
    data["variant"] = data["variant"].astype(object)
    data.loc[0, "variant"] = variant
    with pytest.raises(ValueError, match="only A or B"):
        analyze_experiment(data)


@pytest.mark.parametrize("outcome", [-1, 2, 0.5, "1", float("inf")])
def test_nonbinary_outcomes(outcome):
    data = experiment_from_counts(20, 30)
    data["converted"] = data["converted"].astype(object)
    data.loc[0, "converted"] = outcome
    with pytest.raises(ValueError, match="binary"):
        analyze_experiment(data)


@pytest.mark.parametrize("variants", [[], ["A"], ["B"]])
def test_empty_groups_are_rejected(variants):
    data = pd.DataFrame({"user_id": range(len(variants)), "variant": variants,
                         "converted": [0] * len(variants)})
    with pytest.raises(ValueError, match="non-empty"):
        analyze_experiment(data)


def test_blank_ids_and_duplicate_columns_are_rejected():
    data = experiment_from_counts(20, 30)
    data.loc[0, "user_id"] = "   "
    with pytest.raises(ValueError, match="blank"):
        analyze_experiment(data)
    data = experiment_from_counts(20, 30)
    data.columns = ["user_id", "variant", "variant"]
    with pytest.raises(ValueError, match="unique column"):
        analyze_experiment(data)


def test_invalid_data_type_is_rejected():
    with pytest.raises(ValueError, match="DataFrame"):
        analyze_experiment([])


def test_analysis_is_row_order_independent_and_does_not_mutate_input():
    data = simulate_experiment()
    before = data.copy(deep=True)
    assert analyze_experiment(data) == analyze_experiment(data.sample(frac=1, random_state=17))
    pd.testing.assert_frame_equal(data, before)


def test_zero_control_rate_reports_undefined_relative_uplift():
    result = analyze_experiment(experiment_from_counts(0, 20))
    assert result.relative_uplift_percent is None
    assert result.absolute_uplift_percentage_points == pytest.approx(20)
    assert result.p_value is not None
    assert result.confidence_interval[0] > 0
    assert any("Relative uplift is undefined" in notice for notice in result.warnings)
    assert any("approximation may be unreliable" in notice for notice in result.warnings)


@pytest.mark.parametrize("conversions", [0, 100])
def test_zero_pooled_variance_is_reported_without_nan_or_runtime_warning(conversions):
    with np.errstate(all="raise"):
        result = analyze_experiment(experiment_from_counts(conversions, conversions))
    assert result.z_statistic is None
    assert result.p_value is None
    assert result.statistically_significant is None
    assert result.confidence_interval[0] < 0 < result.confidence_interval[1]
    summary = format_summary(result)
    assert "Statistically significant at alpha=0.05: undefined" in summary
    assert "pooled variance is zero" in summary


def test_cli_round_trip_and_csv_byte_reproducibility(tmp_path):
    csv_path = tmp_path / "nested" / "synthetic.csv"
    generate = [sys.executable, "-m", "experimentation.simulate_experiment",
                "--output", str(csv_path)]
    first = subprocess.run(generate, capture_output=True, text=True, check=True)
    original_bytes = csv_path.read_bytes()
    subprocess.run(generate, capture_output=True, text=True, check=True)
    assert original_bytes == csv_path.read_bytes()
    assert "True generation probabilities: A=0.12, B=0.14" in first.stdout
    assert "SYNTHETIC DATA" in first.stdout
    data = pd.read_csv(csv_path)
    pd.testing.assert_frame_equal(data, simulate_experiment(), check_dtype=False)
    result = analyze_experiment(data)
    analyzed = subprocess.run(
        [sys.executable, "-m", "experimentation.analyze_experiment", "--input", str(csv_path)],
        capture_output=True, text=True, check=True,
    )
    assert analyzed.stdout.strip() == format_summary(result)
    assert "not a product-launch recommendation" in analyzed.stdout
    assert "95% Newcombe/Wilson CI for B - A" in analyzed.stdout
    assert first.stderr == analyzed.stderr == ""


def test_analysis_cli_reports_missing_file_cleanly(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        analyze_main(["--input", str(tmp_path / "missing.csv")])
    assert exc.value.code == 2
    assert "error:" in capsys.readouterr().err


def test_analysis_cli_rejects_invalid_csv(tmp_path, capsys):
    csv_path = tmp_path / "invalid.csv"
    data = experiment_from_counts(20, 30)
    data.loc[0, "converted"] = 2
    data.to_csv(csv_path, index=False)
    with pytest.raises(SystemExit) as exc:
        analyze_main(["--input", str(csv_path)])
    assert exc.value.code == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "binary" in output.err


def test_simulation_cli_invalid_count_does_not_write(tmp_path, capsys):
    csv_path = tmp_path / "invalid.csv"
    with pytest.raises(SystemExit) as exc:
        simulate_main(["--users-per-group", "0", "--output", str(csv_path)])
    assert exc.value.code == 2
    assert not csv_path.exists()
    assert "positive integer" in capsys.readouterr().err
