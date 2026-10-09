"""Verify allocation goodness of fit independently of conversion effects."""

import math
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from experimentation.simulate_experiment import simulate_experiment
from experimentation.srm_check import (
    check_srm,
    count_experiment_participants,
    format_summary,
    main,
    simulate_random_allocation,
)


def test_exactly_balanced_allocation():
    result = check_srm({"A": 4433, "B": 4433})
    assert result.observed_counts == {"A": 4433, "B": 4433}
    assert result.expected_counts == {"A": 4433.0, "B": 4433.0}
    assert result.observed_proportions == result.expected_proportions == {"A": 0.5, "B": 0.5}
    assert result.chi_square_statistic == 0
    assert result.degrees_of_freedom == 1
    assert result.p_value == 1
    assert result.srm_detected is False
    assert result.significance_threshold == 0.001
    assert result.warnings == ()


def test_deliberate_mismatch_matches_chi_square_and_independent_tail_formula():
    result = check_srm({"A": 6500, "B": 3500})
    assert result.expected_counts == {"A": 5000.0, "B": 5000.0}
    assert result.observed_proportions == {"A": 0.65, "B": 0.35}
    assert result.chi_square_statistic == pytest.approx(2 * 1500**2 / 5000)
    # For df=1, the chi-square survival function is erfc(sqrt(statistic/2)).
    assert result.p_value == pytest.approx(math.erfc(math.sqrt(900 / 2)), rel=1e-12, abs=0)
    assert 0 < result.p_value < 1e-190
    assert result.srm_detected is True


def test_unequal_but_plausible_allocation():
    result = check_srm({"A": 5050, "B": 4950})
    assert result.chi_square_statistic == pytest.approx(1)
    assert result.p_value == pytest.approx(math.erfc(math.sqrt(0.5)))
    assert result.srm_detected is False


def test_p_value_decreases_with_more_extreme_imbalance():
    values = [check_srm({"A": a, "B": 10000 - a}).p_value for a in (5000, 5050, 5200, 6500)]
    assert all(first > second for first, second in zip(values, values[1:]))


def test_configurable_threshold_and_strict_comparison():
    default = check_srm({"A": 5100, "B": 4900})
    relaxed = check_srm({"A": 5100, "B": 4900}, significance_threshold=0.05)
    boundary = check_srm({"A": 5100, "B": 4900}, significance_threshold=default.p_value)
    assert default.p_value == pytest.approx(0.04550026389635857)
    assert default.srm_detected is False
    assert relaxed.srm_detected is True
    assert boundary.srm_detected is False
    assert default.p_value == relaxed.p_value


def test_intended_unequal_allocation_is_not_50_50_mismatch():
    result = check_srm({"A": 6500, "B": 3500}, {"A": 0.65, "B": 0.35})
    assert result.expected_counts == {"A": 6500, "B": 3500}
    assert result.expected_proportions == {"A": 0.65, "B": 0.35}
    assert result.chi_square_statistic == 0
    assert result.p_value == 1
    assert result.srm_detected is False


def test_three_variants_use_correct_degrees_of_freedom_and_order():
    result = check_srm({"C": 5000, "B": 3200, "A": 1800},
                       {"B": 0.3, "A": 0.2, "C": 0.5})
    assert result.degrees_of_freedom == 2
    assert result.expected_counts == {"A": 2000, "B": 3000, "C": 5000}
    expected_statistic = 200**2 / 2000 + 200**2 / 3000
    assert result.chi_square_statistic == pytest.approx(expected_statistic)
    assert result.p_value == pytest.approx(math.exp(-expected_statistic / 2))


@pytest.mark.parametrize("counts", [
    None, [], {}, {"A": 1}, {"A": 0, "B": 0},
    {"A": -1, "B": 100}, {"A": True, "B": 100},
    {"A": 1.5, "B": 100}, {"A": 100.0, "B": 100},
    {"A": "100", "B": 100}, {"A": float("nan"), "B": 100},
    {"A": float("inf"), "B": 100}, {"": 100, "B": 100},
    {1: 100, "B": 100}, {"A": 2**53, "B": 1},
])
def test_invalid_counts(counts):
    with pytest.raises(ValueError):
        check_srm(counts)


@pytest.mark.parametrize("allocation", [
    [], {}, {"A": 0.5}, {"A": 0.5, "C": 0.5},
    {"A": 0.5, "B": 0.5, "C": 0.1}, {"A": 0.4, "B": 0.4},
    {"A": 0, "B": 1}, {"A": -0.1, "B": 1.1},
    {"A": True, "B": 0.5}, {"A": "0.5", "B": 0.5},
    {"A": float("nan"), "B": 0.5}, {"A": float("inf"), "B": 0.5},
])
def test_invalid_expected_proportions(allocation):
    with pytest.raises(ValueError):
        check_srm({"A": 500, "B": 500}, allocation)


@pytest.mark.parametrize("threshold", [0, 1, -0.1, float("nan"), float("inf"), True, "0.001"])
def test_invalid_threshold(threshold):
    with pytest.raises(ValueError, match="significance_threshold"):
        check_srm({"A": 500, "B": 500}, significance_threshold=threshold)


def test_numpy_integer_counts_and_roundoff_in_expected_sum():
    result = check_srm({"A": np.int64(500), "B": np.int64(500)},
                       {"A": 0.5, "B": 0.5 + 1e-14})
    assert sum(result.expected_proportions.values()) == pytest.approx(1)
    assert sum(result.expected_counts.values()) == pytest.approx(1000)
    assert result.p_value == pytest.approx(1)


def test_extreme_allocation_reports_numerical_limit_cleanly():
    with pytest.raises(ValueError, match="numerical limits"):
        check_srm({"A": 100, "B": 0}, {"A": 1e-310, "B": 1 - 1e-15})


def test_zero_observed_arm_is_included_and_detected():
    data = pd.DataFrame({"user_id": range(100), "variant": ["A"] * 100})
    counts = count_experiment_participants(data)
    assert counts == {"A": 100, "B": 0}
    result = check_srm(counts)
    assert result.chi_square_statistic == pytest.approx(100)
    assert result.srm_detected is True
    assert result.warnings


def test_small_counts_warn_about_asymptotic_approximation():
    result = check_srm({"A": 1, "B": 1})
    assert result.p_value == 1
    assert "below five" in result.warnings[0]
    assert "Warning:" in format_summary(result)


def test_phase_2_allocation_counts_do_not_modify_conversion_data():
    data = simulate_experiment()
    before = data.copy(deep=True)
    counts = count_experiment_participants(data)
    assert counts == {"A": 4433, "B": 4433}
    assert check_srm(counts).p_value == 1
    pd.testing.assert_frame_equal(data, before)
    assert data.groupby("variant")["converted"].sum().to_dict() == {"A": 527, "B": 603}


@pytest.mark.parametrize("data", [
    pd.DataFrame({"variant": ["A"]}),
    pd.DataFrame({"user_id": [None], "variant": ["A"]}),
    pd.DataFrame({"user_id": [" "], "variant": ["A"]}),
    pd.DataFrame({"user_id": [1, 1], "variant": ["A", "B"]}),
    pd.DataFrame({"user_id": [1], "variant": ["C"]}),
])
def test_invalid_user_level_assignments(data):
    with pytest.raises(ValueError):
        count_experiment_participants(data)


def test_empty_assignment_data_cannot_be_tested():
    counts = count_experiment_participants(pd.DataFrame(columns=["user_id", "variant"]))
    with pytest.raises(ValueError, match="positive"):
        check_srm(counts)


def test_random_allocation_is_reproducible_without_forcing_counts():
    before = np.random.get_state()
    counts = simulate_random_allocation(seed=42)
    assert counts == simulate_random_allocation(seed=42)
    assert sum(counts.values()) == 10000
    assert counts["A"] != counts["B"]  # This seed's realization, not a rule for every seed.
    rng = np.random.Generator(np.random.PCG64(42))
    assert counts["B"] == int(rng.binomial(1, 0.5, size=10000).sum())
    after = np.random.get_state()
    np.testing.assert_array_equal(before[1], after[1])
    assert before[0] == after[0] and before[2:] == after[2:]


@pytest.mark.parametrize("seed", [0, 1, 42, 1234])
def test_randomised_srm_decision_follows_p_value_not_an_assumption_of_passing(seed):
    result = check_srm(simulate_random_allocation(seed))
    assert result.srm_detected == (result.p_value < result.significance_threshold)


@pytest.mark.parametrize("seed", [-1, True, "42", 1.5])
def test_invalid_randomisation_seed(seed):
    with pytest.raises(ValueError, match="seed"):
        simulate_random_allocation(seed)


def test_csv_cli_is_read_only_and_explains_allocation(tmp_path):
    csv_path = tmp_path / "experiment.csv"
    simulate_experiment().to_csv(csv_path, index=False)
    original_bytes = csv_path.read_bytes()
    process = subprocess.run(
        [sys.executable, "-m", "experimentation.srm_check", "--input", str(csv_path)],
        capture_output=True, text=True, check=True,
    )
    assert csv_path.read_bytes() == original_bytes
    assert "SRM p-value: 1" in process.stdout
    assert "SRM detected: no" in process.stdout
    assert "does not prove randomisation quality" in process.stdout
    assert process.stderr == ""


def test_demo_cli_runs_both_separate_scenarios():
    process = subprocess.run(
        [sys.executable, "-m", "experimentation.srm_check", "--demo", "all"],
        capture_output=True, text=True, check=True,
    )
    assert "Scenario A:" in process.stdout
    assert "Scenario B:" in process.stdout
    assert "SRM detected: yes" in process.stdout
    assert "do not modify the original conversion dataset" in process.stdout
    assert "can occasionally flag SRM by chance" in process.stdout
    assert process.stderr == ""


def test_counts_cli_supports_expected_allocation_and_threshold(capsys):
    assert main(["--counts", "A=6500", "B=3500", "--expected", "A=0.65", "B=0.35",
                 "--threshold", "0.01"]) == 0
    output = capsys.readouterr().out
    assert "SRM p-value: 1" in output
    assert "SRM significance threshold: 0.01" in output


@pytest.mark.parametrize("arguments", [
    ["--counts", "A=1", "A=2"], ["--counts", "A=1.5", "B=2"],
    ["--counts", "A=1", "B=2", "--expected", "A=0.4", "B=0.4"],
    ["--demo", "healthy", "--seed", "-1"],
    ["--demo", "mismatch", "--threshold", "0"],
])
def test_invalid_cli_inputs_exit_cleanly(arguments, capsys):
    with pytest.raises(SystemExit) as exc:
        main(arguments)
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "error:" in captured.err
