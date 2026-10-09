"""Plan a two-sided conversion experiment with equal group allocation."""

import argparse
from dataclasses import dataclass
import math
from numbers import Real
from typing import Sequence
import warnings

from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize
from statsmodels.tools.sm_exceptions import ConvergenceWarning


@dataclass(frozen=True)
class SampleSizeResult:
    """Group counts and signed uplift, expressed in percentage units."""

    sample_size_per_group: int
    total_sample_size: int
    absolute_uplift_percentage_points: float
    relative_uplift_percent: float


def _validate_probability(name: str, value: float) -> None:
    """Require a finite numeric value strictly between zero and one."""
    if (
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not math.isfinite(value)
        or not 0 < value < 1
    ):
        raise ValueError(f"{name} must be a finite number strictly between 0 and 1.")


def calculate_sample_size(
    baseline: float = 0.12,
    treatment: float = 0.14,
    *,
    power: float = 0.80,
    alpha: float = 0.05,
) -> SampleSizeResult:
    """Return participants needed per arm for two independent proportions.

    Use Cohen's h = 2*asin(sqrt(treatment)) - 2*asin(sqrt(baseline))
    with statsmodels' normal-approximation power solver, a two-sided test,
    and allocation ratio 1. Round each arm up before computing the total.
    Uplifts retain their sign, so treatment decreases are supported too.

    Assumes independent Bernoulli outcomes, fixed rates and a fixed sample
    horizon. This is an approximation, especially for rare conversions or
    small samples; it has no continuity or multiple-testing correction.
    Boundary rates are excluded (zero baseline also has undefined relative
    uplift). Raise ValueError for invalid or numerically unsolvable inputs.
    """
    for name, value in (
        ("baseline", baseline), ("treatment", treatment),
        ("power", power), ("alpha", alpha),
    ):
        _validate_probability(name, value)
    if baseline == treatment:
        raise ValueError("baseline and treatment must differ.")
    if power <= alpha:
        raise ValueError("power must exceed alpha for a positive sample-size solution.")

    effect_size = abs(float(proportion_effectsize(treatment, baseline)))
    if not math.isfinite(effect_size) or effect_size == 0:
        raise ValueError("The rates are too close to resolve a nonzero effect size.")

    solver = NormalIndPower()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", ConvergenceWarning)
            warnings.simplefilter("error", RuntimeWarning)
            required_per_group = float(solver.solve_power(
                effect_size=effect_size,
                alpha=alpha,
                power=power,
                ratio=1.0,
                alternative="two-sided",
            ))
    except (ValueError, OverflowError, ZeroDivisionError, ConvergenceWarning,
            RuntimeWarning) as exc:
        raise ValueError("Unable to solve sample size for these inputs.") from exc
    if not math.isfinite(required_per_group) or required_per_group <= 0:
        raise ValueError("The solver did not return a finite positive sample size.")
    achieved_power = float(solver.power(
        effect_size=effect_size,
        nobs1=required_per_group,
        alpha=alpha,
        ratio=1.0,
        alternative="two-sided",
    ))
    if not math.isclose(achieved_power, power, rel_tol=0, abs_tol=1e-7):
        raise ValueError("The solver could not achieve the requested power reliably.")

    sample_size_per_group = math.ceil(required_per_group)
    difference = treatment - baseline
    return SampleSizeResult(
        sample_size_per_group=sample_size_per_group,
        total_sample_size=2 * sample_size_per_group,
        absolute_uplift_percentage_points=100 * difference,
        relative_uplift_percent=100 * (difference / baseline),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI; probabilities are fractions, not percentage values."""
    parser = argparse.ArgumentParser(
        description="Sample size for a two-sided conversion test with equal groups.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--baseline", type=float, default=0.12,
                        help="Baseline conversion probability (0 < p < 1)")
    parser.add_argument("--treatment", type=float, default=0.14,
                        help="Target treatment conversion probability (0 < p < 1)")
    parser.add_argument("--alpha", type=float, default=0.05,
                        help="Significance level")
    parser.add_argument("--power", type=float, default=0.80,
                        help="Desired statistical power")
    args = parser.parse_args(argv)
    try:
        result = calculate_sample_size(
            args.baseline, args.treatment, alpha=args.alpha, power=args.power,
        )
    except ValueError as exc:
        parser.error(str(exc))

    print(f"Baseline conversion: {args.baseline:.6g}")
    print(f"Treatment conversion: {args.treatment:.6g}")
    print(f"Alpha: {args.alpha:.6g}")
    print(f"Power: {args.power:.6g}")
    print("Test: two-sided; allocation: 1:1")
    print(f"Required sample size per group: {result.sample_size_per_group}")
    print(f"Required total sample size: {result.total_sample_size}")
    print(f"Absolute uplift: {result.absolute_uplift_percentage_points:.6g} percentage points")
    print(f"Relative uplift: {result.relative_uplift_percent:.6g}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
