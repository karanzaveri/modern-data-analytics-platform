"""Check reporting contracts, reconciliation and deterministic CSV serialization."""

import pandas as pd
import pytest

from experimentation import export_powerbi
from experimentation.analyze_experiment import analyze_experiment
from experimentation.business_impact import calculate_business_impact
from experimentation.sample_size import calculate_sample_size
from experimentation.simulate_experiment import simulate_experiment


@pytest.fixture(scope="module")
def exports():
    return export_powerbi.build_powerbi_exports()


def test_schema_grains_and_native_types(exports):
    assert exports.variants.columns.tolist() == [
        "experiment_id", "variant", "variant_label", "users", "conversions",
        "observed_conversion_rate", "true_generation_probability",
    ]
    assert exports.guardrails.columns.tolist() == [
        "experiment_id", "guardrail_metric", "metric_definition", "unit",
        "availability", "control_value", "treatment_value", "assessment",
    ]
    required_summary = {
        "experiment_id", "experiment_name", "is_synthetic", "random_seed", "alpha",
        "confidence_level", "statistical_test_method", "confidence_interval_method",
        "control_conversion_rate", "treatment_conversion_rate", "conversion_difference",
        "relative_uplift", "z_statistic", "p_value", "ci_lower", "ci_upper",
        "statistically_significant", "planned_sample_size_per_arm", "target_power",
        "planned_mde", "theoretical_power", "srm_statistic", "srm_p_value", "srm_threshold",
        "power_simulation_trials", "power_significant_trials", "empirical_power",
        "null_simulation_trials", "null_false_positive_trials", "empirical_false_positive_rate",
        "financial_period", "projected_eligible_users", "contribution_profit_per_conversion",
        "implementation_cost", "ongoing_costs", "expected_incremental_conversions",
        "expected_incremental_contribution", "estimated_net_financial_benefit",
        "lower_net_financial_scenario", "upper_net_financial_scenario", "break_even_uplift",
        "rollout_readiness", "limitations",
    }
    assert required_summary <= set(exports.summary.columns)
    assert [len(exports.variants), len(exports.summary), len(exports.guardrails)] == [2, 1, 3]
    assert exports.variants["variant"].is_unique
    assert exports.guardrails["guardrail_metric"].is_unique
    for frame in (exports.variants, exports.summary, exports.guardrails):
        assert set(frame["experiment_id"]) == {export_powerbi.EXPERIMENT_ID}
        assert frame.columns.is_unique
    assert pd.api.types.is_integer_dtype(exports.variants["users"])
    assert pd.api.types.is_integer_dtype(exports.variants["conversions"])
    for column in ("is_synthetic", "statistically_significant", "srm_detected"):
        assert pd.api.types.is_bool_dtype(exports.summary[column])


def test_variants_and_inference_reconcile_in_probability_units(exports):
    analysis = analyze_experiment(simulate_experiment(4433, seed=42))
    variants = exports.variants.set_index("variant")
    assert variants["users"].to_dict() == {"A": 4433, "B": 4433}
    assert variants["conversions"].to_dict() == {"A": 527, "B": 603}
    for variant, group in (("A", analysis.control), ("B", analysis.treatment)):
        assert variants.loc[variant, "observed_conversion_rate"] == pytest.approx(
            group.conversions / group.users)
    assert variants["true_generation_probability"].to_dict() == {"A": 0.12, "B": 0.14}
    row = exports.summary.iloc[0]
    assert row["control_conversion_rate"] == variants.loc["A", "observed_conversion_rate"]
    assert row["treatment_conversion_rate"] == variants.loc["B", "observed_conversion_rate"]
    assert row["conversion_difference"] == pytest.approx(analysis.absolute_uplift_percentage_points / 100)
    assert row["relative_uplift"] == pytest.approx(analysis.relative_uplift_percent / 100)
    assert row["ci_lower"] == pytest.approx(analysis.confidence_interval[0])
    assert row["ci_upper"] == pytest.approx(analysis.confidence_interval[1])
    assert row["p_value"] == pytest.approx(analysis.p_value)
    assert row["z_statistic"] == pytest.approx(analysis.z_statistic)
    assert row["statistically_significant"] == (row["p_value"] < row["alpha"])
    assert row["confidence_level"] == pytest.approx(0.95)


def test_planning_srm_and_monte_carlo_metadata_reconcile(exports):
    row = exports.summary.iloc[0]
    plan = calculate_sample_size()
    assert row["planned_sample_size_per_arm"] == plan.sample_size_per_group
    assert row["actual_sample_size_per_arm"] == 4433
    assert row["planned_mde"] == pytest.approx(0.02)
    assert row["target_power"] == pytest.approx(0.8)
    assert row["theoretical_power"] == pytest.approx(0.8000475354908851)
    assert row["srm_statistic"] == 0
    assert row["srm_p_value"] == 1
    assert row["srm_threshold"] == pytest.approx(0.001)
    assert not row["srm_detected"]
    assert "guaranteed by construction" in row["allocation_note"]
    # Regression for this fixed draw order/seed, not a general probabilistic assertion.
    assert row["power_significant_trials"] == 796
    assert row["null_false_positive_trials"] == 44
    for prefix, numerator, rate in (
        ("power", "power_significant_trials", "empirical_power"),
        ("null", "null_false_positive_trials", "empirical_false_positive_rate"),
    ):
        total = row[f"{prefix}_simulation_trials"]
        assert total == 1000
        assert row[numerator] + row[f"{prefix}_non_significant_trials"] + row[f"{prefix}_undefined_trials"] == total
        assert row[rate] == pytest.approx(row[numerator] / total)
    assert row["random_seed"] == row["monte_carlo_random_seed"] == 42


def test_financial_scenarios_reuse_existing_calculator(exports):
    row = exports.summary.iloc[0]
    impact = calculate_business_impact(
        row["control_conversion_rate"], row["treatment_conversion_rate"],
        100000, 12, 40000, difference_confidence_interval=(row["ci_lower"], row["ci_upper"]),
    )
    assert row["expected_incremental_conversions"] == pytest.approx(impact.point.expected_incremental_conversions)
    assert row["expected_incremental_contribution"] == pytest.approx(impact.point.expected_incremental_contribution)
    assert row["estimated_net_financial_benefit"] == pytest.approx(impact.point.estimated_net_financial_benefit)
    assert row["lower_net_financial_scenario"] == pytest.approx(impact.lower.estimated_net_financial_benefit)
    assert row["upper_net_financial_scenario"] == pytest.approx(impact.upper.estimated_net_financial_benefit)
    assert row["break_even_uplift"] == pytest.approx(impact.break_even_uplift_percentage_points / 100)
    assert row["financial_assumptions_are_hypothetical"]
    assert not row["economically_attractive_under_assumptions"]
    assert "Not ready" in row["rollout_readiness"]


def test_original_guardrails_are_missing_not_illustrative_measurements(exports):
    assert set(exports.guardrails["guardrail_metric"]) == {"Payment failures", "Refunds", "Checkout latency"}
    assert exports.guardrails[["control_value", "treatment_value"]].isna().all().all()
    assert exports.guardrails["availability"].eq("missing").all()
    assert exports.guardrails["assessment"].eq("Insufficient data").all()
    assert exports.guardrails["metric_definition"].str.len().gt(0).all()


def test_csv_regeneration_is_identical_and_preserves_other_files(tmp_path):
    sentinel = tmp_path / "synthetic_checkout_experiment.csv"
    sentinel.write_bytes(b"existing source artifact")
    first = export_powerbi.export_powerbi_csvs(tmp_path)
    contents = {p.name: p.read_bytes() for p in first}
    second = export_powerbi.export_powerbi_csvs(tmp_path)
    assert contents == {p.name: p.read_bytes() for p in second}
    assert set(contents) == {"ab_variants.csv", "ab_summary.csv", "ab_guardrails.csv"}
    assert sentinel.read_bytes() == b"existing source artifact"
    guardrails = pd.read_csv(tmp_path / "ab_guardrails.csv")
    assert guardrails[["control_value", "treatment_value"]].isna().all().all()
    assert ",,,Insufficient data" in contents["ab_guardrails.csv"].decode("utf-8")
    assert pd.read_csv(tmp_path / "ab_summary.csv").iloc[0]["p_value"] == pytest.approx(0.01550513979925524)


def test_cli_resolves_relative_output_against_repository_not_cwd(tmp_path, monkeypatch, capsys):
    root = tmp_path / "repository"
    monkeypatch.setattr(export_powerbi, "REPOSITORY_ROOT", root)
    monkeypatch.chdir(tmp_path)
    assert not export_powerbi.DEFAULT_OUTPUT_DIR.is_absolute()
    assert export_powerbi.main([]) == 0
    output = root / export_powerbi.DEFAULT_OUTPUT_DIR
    assert sorted(p.name for p in output.iterdir()) == ["ab_guardrails.csv", "ab_summary.csv", "ab_variants.csv"]
    assert "SYNTHETIC" in capsys.readouterr().out
