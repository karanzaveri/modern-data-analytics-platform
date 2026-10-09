"""Check sample ratio mismatch (SRM), separately from conversion effects."""

import argparse
from collections.abc import Callable, Mapping
from dataclasses import dataclass
import math
from numbers import Integral, Real
from pathlib import Path
from typing import Sequence, TypeVar

import numpy as np
import pandas as pd
from scipy.stats import chisquare

from experimentation.simulate_experiment import DEFAULT_OUTPUT


DEFAULT_THRESHOLD = 0.001
DEFAULT_DEMO_SEED = 42
T = TypeVar("T")


@dataclass(frozen=True)
class SRMResult:
    """Allocation goodness-of-fit results; probabilities are fractions."""

    observed_counts: dict[str, int]
    expected_counts: dict[str, float]
    observed_proportions: dict[str, float]
    expected_proportions: dict[str, float]
    chi_square_statistic: float
    degrees_of_freedom: int
    p_value: float
    srm_detected: bool
    significance_threshold: float
    warnings: tuple[str, ...]


def check_srm(
    observed_counts: Mapping[str, int],
    expected_proportions: Mapping[str, float] | None = None,
    *,
    significance_threshold: float = DEFAULT_THRESHOLD,
) -> SRMResult:
    """Test prespecified allocation using Pearson's chi-square goodness of fit.

    Expected counts are total participants times intended proportions. SciPy's
    chisquare uses sum((observed - expected)**2 / expected) and k-1 degrees of
    freedom, with no fitted allocation parameters or continuity correction.
    Flag SRM when the unrounded p-value is below significance_threshold.
    This asymptotic test assumes independent assignments; it cannot prove
    randomisation quality or identify why traffic is imbalanced.

    Defaults to A/B 50/50. Explicit proportions support two or more variants.
    Zero observed counts are valid; zero expected probabilities are not.
    Proportions must sum to one (absolute tolerance 1e-12); only floating-point
    rounding within that tolerance is normalized. Tiny cell counts produce a
    warning. Raise ValueError for invalid inputs or unsupported count magnitude.
    """
    if not isinstance(observed_counts, Mapping) or len(observed_counts) < 2:
        raise ValueError("observed_counts must map at least two variants to counts.")
    if any(not isinstance(key, str) or not key.strip() for key in observed_counts):
        raise ValueError("Variant labels must be non-blank strings.")
    for count in observed_counts.values():
        if isinstance(count, bool) or not isinstance(count, Integral) or count < 0:
            raise ValueError("Observed counts must be non-negative integers.")
    total = sum(int(count) for count in observed_counts.values())
    if total == 0:
        raise ValueError("Total observed participants must be positive.")
    if total > 2**53:
        raise ValueError("Total counts exceed exact integer precision for this calculation.")
    if (isinstance(significance_threshold, bool)
            or not isinstance(significance_threshold, Real)
            or not math.isfinite(significance_threshold)
            or not 0 < significance_threshold < 1):
        raise ValueError("significance_threshold must be finite and strictly between 0 and 1.")

    allocation = {"A": 0.5, "B": 0.5} if expected_proportions is None else expected_proportions
    if not isinstance(allocation, Mapping) or set(allocation) != set(observed_counts):
        raise ValueError("Expected proportions must have exactly the observed variant keys.")
    for probability in allocation.values():
        if (isinstance(probability, bool) or not isinstance(probability, Real)
                or not math.isfinite(probability) or not 0 < probability < 1):
            raise ValueError("Expected proportions must be finite and strictly between 0 and 1.")
    allocation_sum = math.fsum(float(value) for value in allocation.values())
    if not math.isclose(allocation_sum, 1.0, rel_tol=0, abs_tol=1e-12):
        raise ValueError("Expected proportions must sum to 1.")

    variants = sorted(observed_counts)
    observed = {variant: int(observed_counts[variant]) for variant in variants}
    intended = {variant: float(allocation[variant]) / allocation_sum for variant in variants}
    expected = {variant: total * intended[variant] for variant in variants}
    try:
        with np.errstate(over="raise", divide="raise", invalid="raise"):
            statistic, p_value = chisquare(
                f_obs=[observed[variant] for variant in variants],
                f_exp=[expected[variant] for variant in variants],
                ddof=0,
            )
    except FloatingPointError as exc:
        raise ValueError("Allocation inputs exceed numerical limits of the chi-square calculation.") from exc
    if not math.isfinite(statistic) or not math.isfinite(p_value):
        raise ValueError("The chi-square calculation did not return finite results.")
    notices = ()
    if any(observed[variant] < 5 or expected[variant] < 5 for variant in variants):
        notices = ("Some observed or expected counts are below five; the chi-square "
                   "approximation may be unreliable.",)
    return SRMResult(
        observed_counts=observed,
        expected_counts=expected,
        observed_proportions={variant: observed[variant] / total for variant in variants},
        expected_proportions=intended,
        chi_square_statistic=float(statistic),
        degrees_of_freedom=len(variants) - 1,
        p_value=float(p_value),
        srm_detected=bool(p_value < significance_threshold),
        significance_threshold=float(significance_threshold),
        warnings=notices,
    )


def count_experiment_participants(data: pd.DataFrame) -> dict[str, int]:
    """Count unique A/B assignments, including zero for a missing arm.

    SRM needs user IDs and variants, not purchase outcomes. Validate those
    columns without applying Phase 2's non-empty-group requirement, so a
    missing arm can be detected rather than hidden or dropped.
    """
    if not isinstance(data, pd.DataFrame) or not data.columns.is_unique:
        raise ValueError("Assignment data must be a DataFrame with unique column names.")
    if not {"user_id", "variant"}.issubset(data.columns):
        raise ValueError("Assignment data requires user_id and variant columns.")
    if data[["user_id", "variant"]].isna().any().any():
        raise ValueError("User IDs and variants must not contain missing values.")
    if data["user_id"].astype(str).str.strip().eq("").any():
        raise ValueError("User IDs must not be blank.")
    if data["user_id"].duplicated().any():
        raise ValueError("Duplicate user IDs: each participant must appear only once.")
    if not data["variant"].isin(["A", "B"]).all():
        raise ValueError("CSV variants must be only A or B.")
    counts = data["variant"].value_counts()
    return {variant: int(counts.get(variant, 0)) for variant in ("A", "B")}


def simulate_random_allocation(seed: int = DEFAULT_DEMO_SEED) -> dict[str, int]:
    """Independently assign 10,000 synthetic users with P(B)=0.5.

    PCG64 draws one Bernoulli assignment per user (0=A, 1=B), without forcing
    balance. No conversions are generated and no experiment CSV is changed.
    """
    if isinstance(seed, bool) or not isinstance(seed, Integral) or seed < 0:
        raise ValueError("seed must be a non-negative integer.")
    rng = np.random.Generator(np.random.PCG64(int(seed)))
    assignments = rng.binomial(1, 0.5, size=10_000)
    treatment = int(assignments.sum())
    return {"A": len(assignments) - treatment, "B": treatment}


def format_summary(result: SRMResult) -> str:
    """Report allocation diagnostics without claiming randomisation is proven."""
    lines = ["Variant   Observed count   Expected count   Observed proportion   Expected proportion"]
    for variant in result.observed_counts:
        lines.append(f"{variant:7s} {result.observed_counts[variant]:16d} "
                     f"{result.expected_counts[variant]:16.10g} "
                     f"{result.observed_proportions[variant]:21.10g} "
                     f"{result.expected_proportions[variant]:21.10g}")
    lines.extend([
        f"Chi-square statistic: {result.chi_square_statistic:.17g}",
        f"Degrees of freedom: {result.degrees_of_freedom}",
        f"SRM p-value: {result.p_value:.17g}",
        f"SRM significance threshold: {result.significance_threshold:.10g}",
        f"SRM detected: {'yes' if result.srm_detected else 'no'}",
    ])
    if result.srm_detected:
        lines.append("Investigate allocation, eligibility, logging, and exclusions "
                     "before trusting treatment-effect estimates.")
    else:
        lines.append("No SRM detected at this threshold; this does not prove randomisation quality.")
    lines.extend(f"Warning: {notice}" for notice in result.warnings)
    return "\n".join(lines)


def _parse_mapping(tokens: Sequence[str], conversion: Callable[[str], T]) -> dict[str, T]:
    """Parse CLI variant=value pairs, rejecting ambiguous duplicate labels."""
    result: dict[str, T] = {}
    for token in tokens:
        variant, separator, value = token.partition("=")
        if not separator or not variant.strip() or variant in result:
            raise ValueError("Use unique variant=value pairs, for example A=5000 B=5000.")
        result[variant] = conversion(value)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    """Check an experiment CSV, explicit counts, or separate educational demos."""
    parser = argparse.ArgumentParser(
        description="Check SRM with a chi-square allocation goodness-of-fit test.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--input", type=Path, default=DEFAULT_OUTPUT,
                        help="Existing A/B user-level CSV; read only")
    source.add_argument("--counts", nargs="+", metavar="VARIANT=COUNT",
                        help="Observed integer participant counts")
    source.add_argument("--demo", choices=["healthy", "mismatch", "all"],
                        help="Run separate synthetic allocation scenarios in memory")
    parser.add_argument("--expected", nargs="+", metavar="VARIANT=PROPORTION",
                        help="Prespecified allocation proportions; defaults to A/B 50/50")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                        help="SRM p-value significance threshold")
    parser.add_argument("--seed", type=int, default=DEFAULT_DEMO_SEED,
                        help="Seed for the healthy randomisation demonstration")
    args = parser.parse_args(argv)
    try:
        expected = _parse_mapping(args.expected, float) if args.expected else None
        if args.demo:
            scenarios = []
            if args.demo in ("healthy", "all"):
                scenarios.append((
                    f"Scenario A: healthy independent 50/50 assignment, 10,000 synthetic users; "
                    f"PCG64 seed={args.seed} (counts are not forced equal).",
                    simulate_random_allocation(args.seed),
                ))
            if args.demo in ("mismatch", "all"):
                scenarios.append((
                    "Scenario B: deliberately mismatched synthetic allocation, "
                    "10,000 participants (6,500 A; 3,500 B).",
                    {"A": 6500, "B": 3500},
                ))
        elif args.counts:
            scenarios = [("Observed participant counts", _parse_mapping(args.counts, int))]
        else:
            data = pd.read_csv(args.input, dtype={"user_id": "string"})
            label = f"SRM check of existing CSV: {args.input}"
            if args.input.resolve() == DEFAULT_OUTPUT:
                label += ("\nPhase 2 fixes equal arm sizes: perfect balance is guaranteed "
                          "by construction. This is a functionality demonstration, "
                          "not evidence of real-world randomisation quality.")
            scenarios = [(label, count_experiment_participants(data))]
        summaries = [
            label + "\n" + format_summary(check_srm(
                counts, expected, significance_threshold=args.threshold,
            ))
            for label, counts in scenarios
        ]
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print("\n\n".join(summaries))
    if args.demo:
        print("\nThese allocation-only demonstrations do not modify the original conversion dataset.")
        print("Correct randomisation can occasionally flag SRM by chance; "
              "0.001 is a convention, not a universal rule.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
