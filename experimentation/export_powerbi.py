"""Export the fixed synthetic checkout case using existing statistical functions."""

import argparse
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Sequence

import pandas as pd

from experimentation.analyze_experiment import ALPHA, analyze_experiment
from experimentation.business_impact import calculate_business_impact
from experimentation.guardrails import missing_checkout_guardrails
from experimentation.monte_carlo import run_monte_carlo
from experimentation.sample_size import calculate_sample_size
from experimentation.simulate_experiment import (
    CONTROL_PROBABILITY, DEFAULT_SEED, TREATMENT_PROBABILITY, simulate_experiment,
)
from experimentation.srm_check import check_srm, count_experiment_participants


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = Path("experimentation/outputs/powerbi")
EXPERIMENT_ID = "synthetic_checkout_redesign_seed42"
USERS_PER_ARM = 4433
TARGET_POWER = 0.80
MONTE_CARLO_TRIALS = 1000


@dataclass(frozen=True)
class PowerBIExports:
    """Three reporting grains: variant, experiment summary and guardrail metric."""

    variants: pd.DataFrame
    summary: pd.DataFrame
    guardrails: pd.DataFrame


def build_powerbi_exports() -> PowerBIExports:
    """Reproduce seed 42 in memory without touching existing experiment outputs.

    Rates, relative uplift, MDE and CI bounds use fractions, not percent units.
    Financial bounds condition on hypothetical fixed traffic, margins and costs.
    Monte Carlo scenarios are diagnostics, not extra observed experiment users.
    """
    data = simulate_experiment(USERS_PER_ARM, seed=DEFAULT_SEED)
    analysis = analyze_experiment(data)
    plan = calculate_sample_size(
        CONTROL_PROBABILITY, TREATMENT_PROBABILITY, power=TARGET_POWER, alpha=ALPHA,
    )
    allocation = check_srm(count_experiment_participants(data))
    effect = run_monte_carlo(
        CONTROL_PROBABILITY, TREATMENT_PROBABILITY, USERS_PER_ARM,
        alpha=ALPHA, simulations=MONTE_CARLO_TRIALS, seed=DEFAULT_SEED,
    )
    null = run_monte_carlo(
        CONTROL_PROBABILITY, CONTROL_PROBABILITY, USERS_PER_ARM,
        alpha=ALPHA, simulations=MONTE_CARLO_TRIALS, seed=DEFAULT_SEED,
    )
    impact = calculate_business_impact(
        analysis.control.conversion_rate, analysis.treatment.conversion_rate,
        projected_eligible_users=100_000, contribution_profit_per_conversion=12,
        implementation_cost=40_000, ongoing_costs=0,
        difference_confidence_interval=analysis.confidence_interval,
        period="one hypothetical quarter (three months)",
    )
    guardrails = missing_checkout_guardrails()
    variants = pd.DataFrame([
        {
            "experiment_id": EXPERIMENT_ID,
            "variant": group.variant,
            "variant_label": label,
            "users": group.users,
            "conversions": group.conversions,
            "observed_conversion_rate": group.conversion_rate,
            "true_generation_probability": probability,
        }
        for group, label, probability in (
            (analysis.control, "Control A", CONTROL_PROBABILITY),
            (analysis.treatment, "Treatment B", TREATMENT_PROBABILITY),
        )
    ])
    summary = {
        "experiment_id": EXPERIMENT_ID,
        "experiment_name": "SYNTHETIC Checkout Redesign A/B Test",
        "is_synthetic": True,
        "random_seed": DEFAULT_SEED,
        "alpha": ALPHA,
        "confidence_level": 1 - ALPHA,
        "statistical_test_method": "Two-sided pooled two-proportion z-test",
        "confidence_interval_method": "Newcombe/Wilson (newcomb)",
        "difference_orientation": "Treatment B minus Control A",
        "control_conversion_rate": analysis.control.conversion_rate,
        "treatment_conversion_rate": analysis.treatment.conversion_rate,
        "conversion_difference": impact.point.absolute_conversion_rate_difference,
        "relative_uplift": analysis.relative_uplift_percent / 100,
        "z_statistic": analysis.z_statistic,
        "p_value": analysis.p_value,
        "ci_lower": analysis.confidence_interval[0],
        "ci_upper": analysis.confidence_interval[1],
        "statistically_significant": analysis.statistically_significant,
        "planned_sample_size_per_arm": plan.sample_size_per_group,
        "actual_sample_size_per_arm": USERS_PER_ARM,
        "target_power": TARGET_POWER,
        "planned_mde": plan.absolute_uplift_percentage_points / 100,
        "planned_relative_mde": plan.relative_uplift_percent / 100,
        "theoretical_power": effect.theoretical_power,
        "srm_statistic": allocation.chi_square_statistic,
        "srm_degrees_of_freedom": allocation.degrees_of_freedom,
        "srm_p_value": allocation.p_value,
        "srm_threshold": allocation.significance_threshold,
        "srm_detected": allocation.srm_detected,
        "allocation_note": "Fixed equal arm sizes; perfect SRM balance is guaranteed by construction.",
        "monte_carlo_random_seed": DEFAULT_SEED,
        "power_simulation_trials": MONTE_CARLO_TRIALS,
        "power_significant_trials": effect.significant_experiments,
        "power_non_significant_trials": effect.non_significant_experiments,
        "power_undefined_trials": effect.undefined_experiments,
        "empirical_power": effect.empirical_rejection_rate,
        "null_simulation_trials": MONTE_CARLO_TRIALS,
        "null_false_positive_trials": null.significant_experiments,
        "null_non_significant_trials": null.non_significant_experiments,
        "null_undefined_trials": null.undefined_experiments,
        "empirical_false_positive_rate": null.empirical_rejection_rate,
        "nominal_false_positive_rate": ALPHA,
        "financial_assumptions_are_hypothetical": True,
        "financial_period": impact.period,
        "currency": "EUR",
        "projected_eligible_users": impact.projected_eligible_users,
        "contribution_profit_per_conversion": impact.contribution_profit_per_conversion,
        "implementation_cost": impact.implementation_cost,
        "ongoing_costs": impact.ongoing_costs,
        "expected_incremental_conversions": impact.point.expected_incremental_conversions,
        "expected_incremental_contribution": impact.point.expected_incremental_contribution,
        "estimated_net_financial_benefit": impact.point.estimated_net_financial_benefit,
        "lower_net_financial_scenario": impact.lower.estimated_net_financial_benefit,
        "upper_net_financial_scenario": impact.upper.estimated_net_financial_benefit,
        "break_even_uplift": impact.break_even_uplift_percentage_points / 100,
        "economically_attractive_under_assumptions": impact.point.estimated_net_financial_benefit > 0,
        "rollout_readiness": "Not ready for a full-rollout recommendation",
        "limitations": (
            "Synthetic evidence only; fixed-horizon testing and fixed allocation; "
            "payment failures, refunds and latency were not measured; "
            "real assignment, eligibility and logging remain unvalidated. "
            "Monte Carlo scenarios restart seed 42 separately. "
            "Financial scenarios hold traffic, effects, margins and costs fixed; "
            "they are not future-profit prediction intervals."
        ),
        "numpy_version": version("numpy"),
        "pandas_version": version("pandas"),
        "statsmodels_version": version("statsmodels"),
        "scipy_version": version("scipy"),
    }
    guardrail_rows = pd.DataFrame([
        {
            "experiment_id": EXPERIMENT_ID,
            "guardrail_metric": guardrail.name,
            "metric_definition": guardrail.definition,
            "unit": guardrail.unit,
            "availability": guardrail.data_availability,
            "control_value": guardrail.control_value,
            "treatment_value": guardrail.treatment_value,
            "assessment": guardrail.assessment,
        }
        for guardrail in guardrails
    ])
    for column in ("control_value", "treatment_value"):
        guardrail_rows[column] = guardrail_rows[column].astype("Float64")
    return PowerBIExports(variants, pd.DataFrame([summary]), guardrail_rows)


def export_powerbi_csvs(output_dir: Path = DEFAULT_OUTPUT_DIR) -> tuple[Path, ...]:
    """Write only the three reporting CSVs, with stable ordering and UTF-8 text.

    Relative directories resolve against the repository, independent of the cwd.
    Missing guardrail numbers serialize as empty fields, never zeros or text None.
    Regeneration replaces these three exports without modifying source artifacts.
    """
    exports = build_powerbi_exports()
    output_dir = Path(output_dir)
    if not output_dir.is_absolute():
        output_dir = REPOSITORY_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for filename, data in (
        ("ab_variants.csv", exports.variants),
        ("ab_summary.csv", exports.summary),
        ("ab_guardrails.csv", exports.guardrails),
    ):
        path = output_dir / filename
        data.to_csv(path, index=False, encoding="utf-8", lineterminator="\n", na_rep="")
        paths.append(path)
    return tuple(paths)


def main(argv: Sequence[str] | None = None) -> int:
    """Regenerate all three fixed seed-42 synthetic reporting exports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)
    for path in export_powerbi_csvs(args.output_dir):
        print(f"Saved SYNTHETIC experiment export: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
