"""Validate and analyze synthetic independent user-level conversion outcomes."""

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pandas as pd
from statsmodels.stats.proportion import (
    confint_proportions_2indep,
    proportions_ztest,
)

from experimentation.simulate_experiment import DEFAULT_OUTPUT


ALPHA = 0.05


@dataclass(frozen=True)
class GroupSummary:
    """Observed counts and conversion rate for one experiment arm."""

    variant: str
    users: int
    conversions: int
    conversion_rate: float


@dataclass(frozen=True)
class ExperimentAnalysis:
    """Observed B-minus-A results; None denotes an undefined quantity.

    Confidence bounds are probability differences, not percentage points.
    The interval is always 95% Newcombe; significance uses alpha=0.05.
    """

    control: GroupSummary
    treatment: GroupSummary
    absolute_uplift_percentage_points: float
    relative_uplift_percent: float | None
    z_statistic: float | None
    p_value: float | None
    confidence_interval: tuple[float, float]
    statistically_significant: bool | None
    warnings: tuple[str, ...]


def validate_experiment_data(data: pd.DataFrame) -> None:
    """Require one complete binary outcome per unique user in A or B.

    Global user-ID uniqueness also prevents users appearing in both groups.
    Unequal non-empty arm sizes are allowed for analysis; simulation is equal.
    """
    if not isinstance(data, pd.DataFrame):
        raise ValueError("Experiment data must be a pandas DataFrame.")
    if not data.columns.is_unique:
        raise ValueError("Experiment data must have unique column names.")
    required = {"user_id", "variant", "converted"}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}.")
    if data.isna().any().any():
        raise ValueError("Experiment data must not contain missing values.")
    if data["user_id"].astype(str).str.strip().eq("").any():
        raise ValueError("User IDs must not be blank.")
    if data["user_id"].duplicated().any():
        raise ValueError("Duplicate user IDs: each user must appear once in only one group.")
    if not data["variant"].isin(["A", "B"]).all():
        raise ValueError("Variants must be only A or B.")
    if not data["converted"].isin([0, 1]).all():
        raise ValueError("Conversion outcomes must be binary numeric 0 or 1.")
    if set(data["variant"]) != {"A", "B"}:
        raise ValueError("Both groups A and B must be non-empty.")


def _summarize_group(data: pd.DataFrame, variant: str) -> GroupSummary:
    outcomes = data.loc[data["variant"] == variant, "converted"]
    users = len(outcomes)
    conversions = int(outcomes.sum())
    return GroupSummary(variant, users, conversions, conversions / users)


def analyze_experiment(data: pd.DataFrame) -> ExperimentAnalysis:
    """Test equal rates with a two-sided pooled two-proportion z-test.

    Pass treatment B first to Statsmodels so z and the 95% interval describe
    B minus A. The Newcombe interval combines separate Wilson score bounds;
    it avoids the poor boundary behavior of a simple Wald interval. It is
    not the inversion of the pooled z-test, so decisions can differ near .05.
    No continuity, repeated-look, or multiple-testing correction is applied.
    """
    validate_experiment_data(data)
    control = _summarize_group(data, "A")
    treatment = _summarize_group(data, "B")
    difference = treatment.conversion_rate - control.conversion_rate
    notices = []
    if control.conversion_rate == 0:
        relative_uplift = None
        notices.append("Relative uplift is undefined because the observed A rate is zero.")
    else:
        relative_uplift = 100 * difference / control.conversion_rate

    for group in (control, treatment):
        if min(group.conversions, group.users - group.conversions) < 5:
            notices.append(f"Group {group.variant} has fewer than five conversions or "
                           "non-conversions; the z-test approximation may be unreliable.")

    total_conversions = control.conversions + treatment.conversions
    total_users = control.users + treatment.users
    if total_conversions in (0, total_users):
        z_statistic = p_value = significant = None
        notices.append("The pooled z-test is undefined: all outcomes are identical "
                       "and pooled variance is zero.")
    else:
        z, p = proportions_ztest(
            count=[treatment.conversions, control.conversions],
            nobs=[treatment.users, control.users],
            value=0,
            alternative="two-sided",
            prop_var=False,
        )
        z_statistic, p_value = float(z), float(p)
        significant = p_value < ALPHA

    lower, upper = confint_proportions_2indep(
        count1=treatment.conversions, nobs1=treatment.users,
        count2=control.conversions, nobs2=control.users,
        method="newcomb", compare="diff", alpha=ALPHA,
    )
    return ExperimentAnalysis(
        control=control,
        treatment=treatment,
        absolute_uplift_percentage_points=100 * difference,
        relative_uplift_percent=relative_uplift,
        z_statistic=z_statistic,
        p_value=p_value,
        confidence_interval=(float(lower), float(upper)),
        statistically_significant=significant,
        warnings=tuple(notices),
    )


def format_summary(result: ExperimentAnalysis) -> str:
    """Explain observed results without making a product-launch decision."""
    lines = [
        "SYNTHETIC checkout redesign experiment (educational demonstration)",
        "Rates below are observed in the CSV, not true generation probabilities.",
        "Variant   Users   Conversions   Observed conversion rate",
    ]
    for group in (result.control, result.treatment):
        lines.append(f"{group.variant:7s} {group.users:7d} {group.conversions:13d} "
                     f"{100 * group.conversion_rate:24.6f}%")
    lower, upper = result.confidence_interval
    lines.append(f"Absolute uplift (B - A): {result.absolute_uplift_percentage_points:.6f} "
                 "percentage points")
    relative = ("undefined (observed A rate is zero)"
                if result.relative_uplift_percent is None
                else f"{result.relative_uplift_percent:.6f}%")
    lines.append(f"Relative uplift versus observed A: {relative}")
    if result.p_value is None:
        lines.append("Two-sided pooled z-test: undefined (zero pooled variance)")
    else:
        lines.append(f"Two-sided pooled z-test (B - A): z={result.z_statistic:.8f}; "
                     f"p-value={result.p_value:.10g}")
    lines.append(f"95% Newcombe/Wilson CI for B - A: [{lower:.8f}, {upper:.8f}] "
                 f"in probability units; [{100 * lower:.6f}, {100 * upper:.6f}] "
                 "percentage points")
    decision = ("undefined" if result.statistically_significant is None
                else "yes" if result.statistically_significant else "no")
    lines.append(f"Statistically significant at alpha={ALPHA:.2f}: {decision}")
    if result.statistically_significant:
        direction = "higher" if result.absolute_uplift_percentage_points > 0 else "lower"
        lines.append(f"Reject equal conversion rates; observed B is {direction} than A.")
    elif result.statistically_significant is False:
        lines.append("Do not reject equal conversion rates; this does not establish equality.")
    lines.extend(f"Warning: {notice}" for notice in result.warnings)
    lines.append("Synthetic evidence is not a product-launch recommendation. "
                 "Practical impact and real-world validation require separate judgment.")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Read and validate a synthetic experiment CSV and print its analysis."""
    parser = argparse.ArgumentParser(
        description="Analyze synthetic checkout conversion data (B minus A).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_OUTPUT,
                        help="Synthetic user-level CSV to analyze")
    args = parser.parse_args(argv)
    try:
        data = pd.read_csv(args.input, dtype={"user_id": "string"})
        result = analyze_experiment(data)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(format_summary(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
