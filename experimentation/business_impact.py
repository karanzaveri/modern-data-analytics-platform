"""Conditional business projections from conversion effects, not rollout advice."""

import argparse
from dataclasses import dataclass
import math
from numbers import Integral, Real
from pathlib import Path
from typing import Sequence

import pandas as pd

from experimentation.analyze_experiment import (
    ExperimentAnalysis, analyze_experiment, format_summary as format_primary_summary,
)
from experimentation.guardrails import (
    GuardrailResult, format_guardrails, missing_checkout_guardrails,
)
from experimentation.simulate_experiment import DEFAULT_OUTPUT
from experimentation.srm_check import SRMResult, check_srm, count_experiment_participants


DEFAULT_REPORT = Path(__file__).resolve().parent / "outputs" / "business_decision_report.txt"


@dataclass(frozen=True)
class FinancialScenario:
    """Linear projection for one B-minus-A effect in probability units."""

    absolute_conversion_rate_difference: float
    expected_incremental_conversions: float
    expected_incremental_contribution: float
    estimated_net_financial_benefit: float


@dataclass(frozen=True)
class BusinessImpact:
    """Point and optional interval scenarios under fixed period/economic inputs."""

    period: str
    projected_eligible_users: int
    contribution_profit_per_conversion: float
    implementation_cost: float
    ongoing_costs: float
    point: FinancialScenario
    lower: FinancialScenario | None
    upper: FinancialScenario | None
    break_even_uplift_percentage_points: float | None


def _finite_number(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number.")


def calculate_business_impact(
    control_rate: float,
    treatment_rate: float,
    projected_eligible_users: int,
    contribution_profit_per_conversion: float,
    implementation_cost: float,
    *,
    ongoing_costs: float = 0.0,
    difference_confidence_interval: tuple[float, float] | None = None,
    period: str = "specified business period",
) -> BusinessImpact:
    """Project giving B to all eligible users versus giving A to those users.

    Incremental conversions = users*(B-A); contribution = conversions*profit;
    net benefit = contribution - implementation cost - period ongoing costs.
    Charge the full one-time cost in this period. Break-even uplift in percentage
    points is 100*total_cost/(users*profit), undefined if users or profit is zero.
    Negative effects imply lost conversions and contribution. Fractional counts
    are expected values, not observed purchases.

    Optional bounds describe B-A in probability units and undergo the same
    linear transformation. These scenarios condition on fixed traffic and
    economics; they are not a prediction interval for future profit. Projection
    requires generalisable uplift, stable eligible traffic, and stable margins.
    No discounting, taxes, cost uncertainty, or guardrail costs are modeled.
    """
    for name, rate in (("control_rate", control_rate), ("treatment_rate", treatment_rate)):
        _finite_number(name, rate)
        if not 0 <= rate <= 1:
            raise ValueError(f"{name} must be between 0 and 1 inclusive.")
    if (isinstance(projected_eligible_users, bool)
            or not isinstance(projected_eligible_users, Integral) or projected_eligible_users < 0
            or projected_eligible_users > 2**53):
        raise ValueError("projected_eligible_users must be an integer between 0 and 2**53.")
    for name, value in (("contribution_profit_per_conversion", contribution_profit_per_conversion),
                        ("implementation_cost", implementation_cost), ("ongoing_costs", ongoing_costs)):
        _finite_number(name, value)
        if value < 0:
            raise ValueError(f"{name} must be non-negative.")
    if not isinstance(period, str) or not period.strip():
        raise ValueError("period must be a non-blank label for the projection horizon.")
    if difference_confidence_interval is not None:
        if not isinstance(difference_confidence_interval, (tuple, list)) or len(difference_confidence_interval) != 2:
            raise ValueError("difference_confidence_interval must contain lower and upper bounds.")
        for bound in difference_confidence_interval:
            _finite_number("confidence interval bound", bound)
            if not -1 <= bound <= 1:
                raise ValueError("Confidence interval bounds must be probability differences in [-1, 1].")
        if difference_confidence_interval[0] > difference_confidence_interval[1]:
            raise ValueError("Confidence interval lower bound must not exceed upper bound.")

    total_cost = float(implementation_cost) + float(ongoing_costs)
    exposure = int(projected_eligible_users) * float(contribution_profit_per_conversion)
    if not math.isfinite(total_cost) or not math.isfinite(exposure):
        raise ValueError("Financial assumptions exceed numeric limits.")

    def scenario(difference: float) -> FinancialScenario:
        conversions = int(projected_eligible_users) * float(difference)
        contribution = conversions * float(contribution_profit_per_conversion)
        net = contribution - total_cost
        if not all(math.isfinite(value) for value in (conversions, contribution, net)):
            raise ValueError("Financial projection exceeds numeric limits.")
        return FinancialScenario(float(difference), conversions, contribution, net)

    break_even = 100 * (total_cost / exposure) if exposure > 0 else None
    if break_even is not None and not math.isfinite(break_even):
        raise ValueError("Break-even calculation exceeds numeric limits.")
    lower = upper = None
    if difference_confidence_interval is not None:
        lower, upper = (scenario(bound) for bound in difference_confidence_interval)
    return BusinessImpact(
        period=period, projected_eligible_users=int(projected_eligible_users),
        contribution_profit_per_conversion=float(contribution_profit_per_conversion),
        implementation_cost=float(implementation_cost), ongoing_costs=float(ongoing_costs),
        point=scenario(treatment_rate - control_rate), lower=lower, upper=upper,
        break_even_uplift_percentage_points=break_even,
    )


def format_decision_report(
    analysis: ExperimentAnalysis,
    impact: BusinessImpact,
    allocation: SRMResult,
    guardrails: Sequence[GuardrailResult],
) -> str:
    """Separate inference, conditional economics, missing evidence, and readiness."""
    lines = [format_primary_summary(analysis), "", "HYPOTHETICAL financial assumptions:",
             f"Projected period: {impact.period}",
             f"Eligible users receiving B rather than A: {impact.projected_eligible_users:,}",
             f"Contribution profit per incremental conversion: EUR {impact.contribution_profit_per_conversion:,.2f}",
             f"One-time implementation cost charged in this period: EUR {impact.implementation_cost:,.2f}",
             f"Ongoing costs for this period: EUR {impact.ongoing_costs:,.2f}", "",
             "Financial projections (B minus A):"]
    for label, scenario in (("Point estimate", impact.point), ("Lower effect scenario", impact.lower),
                            ("Upper effect scenario", impact.upper)):
        if scenario is None:
            continue
        lines.extend([
            f"{label}: uplift={100 * scenario.absolute_conversion_rate_difference:.9f} percentage points",
            f"  Expected incremental conversions: {scenario.expected_incremental_conversions:.9f}",
            f"  Expected incremental contribution: EUR {scenario.expected_incremental_contribution:,.2f}",
            f"  Estimated net financial benefit: EUR {scenario.estimated_net_financial_benefit:,.2f}",
        ])
    if impact.break_even_uplift_percentage_points is None:
        lines.append("Break-even uplift: undefined (no eligible users or zero contribution per conversion).")
    else:
        lines.append(f"Break-even uplift: {impact.break_even_uplift_percentage_points:.9f} percentage points")
        if impact.break_even_uplift_percentage_points > 100 * (1 - analysis.control.conversion_rate):
            lines.append("The required break-even uplift exceeds the feasible uplift at this baseline.")
    lines.extend([
        "Financial bounds transform the 95% conversion-effect CI with traffic and economics held fixed; "
        "they are not a future-profit prediction interval.", "",
        "Original-dataset guardrails: payment failures, refunds and checkout latency were NOT observed.",
        "Limits below are illustrative, not an actual prespecified plan for this experiment.",
        format_guardrails(guardrails), "",
        f"Allocation check: SRM p-value={allocation.p_value:.10g}; "
        f"SRM detected={'yes' if allocation.srm_detected else 'no'}.",
        "The original Phase 2 simulator fixes equal arm sizes; its passing SRM result is guaranteed by construction, "
        "not evidence of real-world randomisation quality.",
        "Unresolved checks: real assignment integrity, eligibility and event logging; "
        "guardrail instrumentation and complete refund follow-up; effect generalisability "
        "and stable traffic, margins and costs.", "",
    ])
    economic = impact.point.estimated_net_financial_benefit > 0
    evaluated = sum(result.assessment != "Insufficient data" for result in guardrails)
    breached = sum(result.assessment == "Threshold breached" for result in guardrails)
    lines.extend([
        f"Economically attractive under assumptions (positive point-estimate net benefit): {'yes' if economic else 'no'}",
        f"Guardrails descriptively evaluated: {evaluated}/{len(guardrails)}; "
        f"missing/insufficient: {len(guardrails) - evaluated}; thresholds breached: {breached}",
        "Overall readiness: not ready for a rollout recommendation from this synthetic demonstration.",
        "Statistical significance, conditional profitability and descriptive guardrails are separate "
        "checks; none alone justifies a full rollout.",
    ])
    if impact.upper is not None and impact.upper.estimated_net_financial_benefit < 0:
        lines.append("Even the upper effect scenario has negative net benefit under these assumptions.")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Analyze the existing synthetic CSV and save a hypothetical decision report."""
    parser = argparse.ArgumentParser(
        description="Synthetic checkout business decision report with hypothetical EUR economics.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--period", default="one hypothetical quarter (three months)")
    parser.add_argument("--eligible-users", type=int, default=100_000)
    parser.add_argument("--contribution-profit", type=float, default=12.0)
    parser.add_argument("--implementation-cost", type=float, default=40_000.0)
    parser.add_argument("--ongoing-costs", type=float, default=0.0)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        if args.output.resolve() in (args.input.resolve(), DEFAULT_OUTPUT):
            raise ValueError("Report output must differ from the input and original experiment datasets.")
        data = pd.read_csv(args.input, dtype={"user_id": "string"})
        analysis = analyze_experiment(data)
        impact = calculate_business_impact(
            analysis.control.conversion_rate, analysis.treatment.conversion_rate,
            args.eligible_users, args.contribution_profit, args.implementation_cost,
            ongoing_costs=args.ongoing_costs, period=args.period,
            difference_confidence_interval=analysis.confidence_interval,
        )
        allocation = check_srm(count_experiment_participants(data))
        report = format_decision_report(analysis, impact, allocation, missing_checkout_guardrails())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report + "\n", encoding="utf-8")
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(report)
    print(f"Saved decision report: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
