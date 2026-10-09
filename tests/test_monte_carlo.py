"""Verify reproducible trials, inferential behavior, and saved Monte Carlo plots."""

import math
import subprocess
import sys

import numpy as np
import pandas as pd
from PIL import Image
import pytest

from experimentation.analyze_experiment import analyze_experiment
from experimentation.monte_carlo import (
    format_summary,
    generate_plots,
    main,
    run_monte_carlo,
)
from experimentation.sample_size import calculate_sample_size


@pytest.fixture(scope="module")
def effect_run():
    return run_monte_carlo()


@pytest.fixture(scope="module")
def null_run():
    return run_monte_carlo(treatment_probability=0.12)


def test_reproducibility_and_prefix_stability():
    first = run_monte_carlo(simulations=25, seed=42)
    second = run_monte_carlo(simulations=25, seed=42)
    longer = run_monte_carlo(simulations=50, seed=42)
    pd.testing.assert_frame_equal(first.experiments, second.experiments)
    pd.testing.assert_frame_equal(first.experiments, longer.experiments.iloc[:25])
    assert first.empirical_rejection_rate == second.empirical_rejection_rate


def test_result_schema_counts_rates_and_uplift(effect_run):
    data = effect_run.experiments
    assert list(data.columns) == [
        "simulation_id", "control_conversions", "treatment_conversions",
        "observed_control_rate", "observed_treatment_rate",
        "absolute_uplift_percentage_points", "z_statistic", "p_value",
        "statistically_significant",
    ]
    assert len(data) == 1000
    assert data["simulation_id"].tolist() == list(range(1, 1001))
    n = calculate_sample_size().sample_size_per_group
    assert effect_run.sample_size_per_group == n == 4433
    assert data["control_conversions"].between(0, n).all()
    assert data["treatment_conversions"].between(0, n).all()
    np.testing.assert_allclose(data["observed_control_rate"], data["control_conversions"] / n)
    np.testing.assert_allclose(data["observed_treatment_rate"], data["treatment_conversions"] / n)
    np.testing.assert_allclose(data["absolute_uplift_percentage_points"],
                               100 * (data["observed_treatment_rate"] - data["observed_control_rate"]))
    assert effect_run.mean_uplift_percentage_points == pytest.approx(
        data["absolute_uplift_percentage_points"].mean())
    assert effect_run.std_uplift_percentage_points == pytest.approx(
        data["absolute_uplift_percentage_points"].std(ddof=1))


def test_p_value_ranges_and_significance_classification(effect_run, null_run):
    for result in (effect_run, null_run):
        data = result.experiments
        assert result.undefined_experiments == 0
        assert data["p_value"].between(0, 1).all()
        assert np.isfinite(data["z_statistic"]).all()
        assert (data["statistically_significant"] == (data["p_value"] < result.alpha)).all()
        assert result.significant_experiments == int((data["p_value"] < result.alpha).sum())
        assert result.significant_experiments + result.non_significant_experiments == len(data)
        assert result.empirical_rejection_rate == result.significant_experiments / len(data)


def test_monte_carlo_test_matches_phase_2_user_level_analysis():
    result = run_monte_carlo(sample_size_per_group=100, simulations=5)
    for row in result.experiments.itertuples(index=False):
        outcomes = ([1] * row.control_conversions + [0] * (100 - row.control_conversions)
                    + [1] * row.treatment_conversions + [0] * (100 - row.treatment_conversions))
        data = pd.DataFrame({"user_id": range(200), "variant": ["A"] * 100 + ["B"] * 100,
                             "converted": outcomes})
        analysis = analyze_experiment(data)
        assert row.z_statistic == pytest.approx(analysis.z_statistic)
        assert row.p_value == pytest.approx(analysis.p_value)
        assert bool(row.statistically_significant) == analysis.statistically_significant


def test_effect_power_and_uplift_with_statistical_tolerances(effect_run):
    trials, n = len(effect_run.experiments), effect_run.sample_size_per_group
    theoretical = effect_run.theoretical_power
    # Five binomial SEs plus 1 percentage point for approximation differences.
    power_tolerance = 5 * math.sqrt(theoretical * (1 - theoretical) / trials) + 0.01
    assert abs(effect_run.empirical_rejection_rate - theoretical) < power_tolerance
    uplift_sd = 100 * math.sqrt((0.12 * 0.88 + 0.14 * 0.86) / n)
    assert abs(effect_run.mean_uplift_percentage_points - 2) < 5 * uplift_sd / math.sqrt(trials)
    # Approximate sampling SE of a sample SD for near-normal binomial differences.
    assert abs(effect_run.std_uplift_percentage_points - uplift_sd) < 5 * uplift_sd / math.sqrt(2 * (trials - 1))
    assert 0 < effect_run.empirical_rejection_rate < 1
    assert theoretical == pytest.approx(0.800047535491, abs=1e-10)


def test_zero_effect_false_positives_with_statistical_tolerances(null_run):
    trials, n = len(null_run.experiments), null_run.sample_size_per_group
    tolerance = 5 * math.sqrt(0.05 * 0.95 / trials) + 0.005
    assert abs(null_run.empirical_rejection_rate - 0.05) < tolerance
    assert null_run.theoretical_power == pytest.approx(null_run.alpha)
    expected_uplift_sd = 100 * math.sqrt(2 * 0.12 * 0.88 / n)
    assert abs(null_run.mean_uplift_percentage_points) < 5 * expected_uplift_sd / math.sqrt(trials)
    assert "False positives:" in format_summary(null_run)
    assert "Nominal false-positive rate (alpha): 0.05" in format_summary(null_run)


def test_larger_sample_size_increases_detectable_effect_power():
    small = run_monte_carlo(sample_size_per_group=500, simulations=2000)
    large = run_monte_carlo(sample_size_per_group=4433, simulations=2000)
    combined_se = math.sqrt(sum(r.empirical_rejection_rate * (1 - r.empirical_rejection_rate)
                                / 2000 for r in (small, large)))
    assert large.empirical_rejection_rate - small.empirical_rejection_rate > 5 * combined_se
    assert large.theoretical_power > small.theoretical_power
    assert large.std_uplift_percentage_points < small.std_uplift_percentage_points


def test_changing_alpha_changes_decisions_not_draws():
    strict = run_monte_carlo(alpha=0.01, simulations=100)
    relaxed = run_monte_carlo(alpha=0.10, simulations=100)
    pd.testing.assert_frame_equal(strict.experiments.drop(columns="statistically_significant"),
                                  relaxed.experiments.drop(columns="statistically_significant"))
    assert strict.significant_experiments <= relaxed.significant_experiments


def test_seed_handling_and_independent_trial_draws():
    before = np.random.get_state()
    first = run_monte_carlo(simulations=50, seed=np.int64(42))
    second = run_monte_carlo(simulations=50, seed=43)
    after = np.random.get_state()
    np.testing.assert_array_equal(before[1], after[1])
    assert before[0] == after[0] and before[2:] == after[2:]
    assert not first.experiments.equals(second.experiments)
    assert len(first.experiments[["control_conversions", "treatment_conversions"]].drop_duplicates()) > 1
    expected_rng = np.random.Generator(np.random.PCG64(42))
    expected_counts = expected_rng.binomial(4433, [0.12, 0.14], size=(50, 2))
    np.testing.assert_array_equal(first.experiments[["control_conversions", "treatment_conversions"]],
                                  expected_counts)


@pytest.mark.parametrize("field", ["control_probability", "treatment_probability", "alpha"])
@pytest.mark.parametrize("value", [0, 1, -0.1, 1.1, float("nan"), float("inf"), True, "0.12"])
def test_invalid_probabilities_and_alpha(field, value):
    with pytest.raises(ValueError, match=field):
        run_monte_carlo(**{field: value})


@pytest.mark.parametrize("field", ["sample_size_per_group", "simulations"])
@pytest.mark.parametrize("value", [0, -1, 1.5, True, "10", float("inf")])
def test_invalid_sizes(field, value):
    with pytest.raises(ValueError, match=field):
        run_monte_carlo(**{field: value})


@pytest.mark.parametrize("seed", [-1, 1.5, True, "42", None])
def test_invalid_seed(seed):
    with pytest.raises(ValueError, match="seed"):
        run_monte_carlo(seed=seed)


def test_unsupported_sample_magnitude():
    with pytest.raises(ValueError, match="precision"):
        run_monte_carlo(sample_size_per_group=2**53)


def test_single_simulation_std_is_undefined():
    result = run_monte_carlo(simulations=1, seed=0)
    assert len(result.experiments) == 1
    assert result.std_uplift_percentage_points is None
    assert "undefined (one simulation)" in format_summary(result)


def test_zero_variance_trials_preserve_phase_2_undefined_semantics():
    result = run_monte_carlo(0.01, 0.01, 1, simulations=100, seed=42)
    data = result.experiments
    undefined = data["p_value"].isna()
    assert undefined.any()
    assert data.loc[undefined, "z_statistic"].isna().all()
    assert data.loc[undefined, "statistically_significant"].isna().all()
    assert data.loc[~undefined, "p_value"].between(0, 1).all()
    assert result.significant_experiments + result.non_significant_experiments + result.undefined_experiments == 100
    assert result.empirical_rejection_rate == result.significant_experiments / 100
    assert "zero pooled variance" in format_summary(result)


def test_negative_effect_has_negative_mean_and_nonzero_power():
    result = run_monte_carlo(0.14, 0.12, simulations=1000)
    expected_sd = 100 * math.sqrt((0.14 * 0.86 + 0.12 * 0.88) / 4433)
    assert abs(result.mean_uplift_percentage_points + 2) < 5 * expected_sd / math.sqrt(1000)
    tolerance = 5 * math.sqrt(result.theoretical_power * (1 - result.theoretical_power) / 1000) + 0.01
    assert abs(result.empirical_rejection_rate - result.theoretical_power) < tolerance


def test_plots_are_readable_png_artifacts(effect_run, null_run, tmp_path):
    paths = generate_plots(effect_run, tmp_path) + generate_plots(null_run, tmp_path)
    assert {path.name for path in paths} == {
        "observed_uplift_distribution.png", "null_p_value_distribution.png",
        "power_comparison.png", "false_positive_comparison.png",
    }
    for path in paths:
        with Image.open(path) as image:
            assert image.format == "PNG"
            assert image.width >= 1000 and image.height >= 600
            assert np.asarray(image).std() > 0


def test_cli_csv_reproducibility_and_no_plots_option(tmp_path):
    command = [sys.executable, "-m", "experimentation.monte_carlo", "--simulations", "25",
               "--sample-size", "500", "--seed", "17", "--no-plots", "--output-dir", str(tmp_path)]
    process = subprocess.run(command, capture_output=True, text=True, check=True)
    csv_path = tmp_path / "power_simulations.csv"
    original_bytes = csv_path.read_bytes()
    subprocess.run(command, capture_output=True, text=True, check=True)
    assert csv_path.read_bytes() == original_bytes
    data = pd.read_csv(csv_path)
    assert len(data) == 25
    assert not list(tmp_path.glob("*.png"))
    assert "Empirical statistical power:" in process.stdout
    assert process.stderr == ""


def test_cli_null_saves_false_positive_artifacts(tmp_path, capsys):
    assert main(["--treatment-probability", "0.12", "--simulations", "25",
                 "--output-dir", str(tmp_path)]) == 0
    assert (tmp_path / "null_simulations.csv").exists()
    assert (tmp_path / "null_p_value_distribution.png").exists()
    assert (tmp_path / "false_positive_comparison.png").exists()
    assert "Empirical false-positive rate:" in capsys.readouterr().out


def test_invalid_cli_input_does_not_write(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--simulations", "0", "--output-dir", str(tmp_path / "unused")])
    assert exc.value.code == 2
    assert not (tmp_path / "unused").exists()
    assert "simulations" in capsys.readouterr().err
