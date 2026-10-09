"""Reproduce fixed-horizon A/B power and false positives with binomial trials."""

import argparse
from dataclasses import dataclass
import math
from numbers import Integral, Real
import os
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize, proportions_ztest

from experimentation.sample_size import calculate_sample_size


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "outputs" / "monte_carlo"


@dataclass(frozen=True)
class MonteCarloResult:
    """Trial rows and a summary; uplift uses B minus A in percentage points."""

    experiments: pd.DataFrame
    control_probability: float
    treatment_probability: float
    sample_size_per_group: int
    alpha: float
    seed: int
    significant_experiments: int
    non_significant_experiments: int
    undefined_experiments: int
    empirical_rejection_rate: float
    theoretical_power: float
    mean_uplift_percentage_points: float
    std_uplift_percentage_points: float | None


def _validate_probability(name: str, value: float) -> None:
    if (isinstance(value, bool) or not isinstance(value, Real)
            or not math.isfinite(value) or not 0 < value < 1):
        raise ValueError(f"{name} must be finite and strictly between 0 and 1.")


def _validate_integer(name: str, value: int, minimum: int = 1) -> None:
    if isinstance(value, bool) or not isinstance(value, Integral) or value < minimum:
        raise ValueError(f"{name} must be an integer at least {minimum}.")


def run_monte_carlo(
    control_probability: float = 0.12,
    treatment_probability: float = 0.14,
    sample_size_per_group: int | None = None,
    *,
    alpha: float = 0.05,
    simulations: int = 1000,
    seed: int = 42,
) -> MonteCarloResult:
    """Draw independent binomial counts and test each trial at its fixed horizon.

    A binomial count is the sum of n independent Bernoulli user outcomes.
    Local PCG64 draws an A/B pair per trial, never reseeding within the run.
    Pass B first to the same pooled two-sided proportions_ztest as Phase 2.
    Undefined zero-variance tests retain missing z, p, and decision values;
    report them separately and count them as no rejection in the unconditional
    rejection frequency. No exact-test fallback or continuity correction is used.

    Default arm size comes from the original Phase 1 12%-to-14% design, also
    when simulating the null. Theoretical power uses Phase 1's Cohen's h and
    NormalIndPower at the actual n and alpha. Uplift SD is sample SD (ddof=1),
    undefined for a single trial. Rates and alpha must be strictly inside (0,1).
    """
    for name, value in (("control_probability", control_probability),
                        ("treatment_probability", treatment_probability), ("alpha", alpha)):
        _validate_probability(name, value)
    if sample_size_per_group is None:
        sample_size_per_group = calculate_sample_size().sample_size_per_group
    _validate_integer("sample_size_per_group", sample_size_per_group)
    _validate_integer("simulations", simulations)
    _validate_integer("seed", seed, minimum=0)
    if sample_size_per_group > 2**52:
        raise ValueError("sample_size_per_group exceeds exact pooled-count floating-point precision.")

    n, trials = int(sample_size_per_group), int(simulations)
    rng = np.random.Generator(np.random.PCG64(int(seed)))
    counts = rng.binomial(n, [control_probability, treatment_probability], size=(trials, 2))
    control_rates, treatment_rates = counts[:, 0] / n, counts[:, 1] / n
    z_statistics = np.full(trials, np.nan)
    p_values = np.full(trials, np.nan)
    decisions: list[bool | None] = []
    for index, (control_count, treatment_count) in enumerate(counts):
        if int(control_count) + int(treatment_count) in (0, 2 * n):
            decisions.append(None)
            continue
        z, p = proportions_ztest(
            count=[treatment_count, control_count], nobs=[n, n],
            value=0, alternative="two-sided", prop_var=False,
        )
        z_statistics[index], p_values[index] = float(z), float(p)
        decisions.append(bool(p < alpha))

    uplift = 100 * (treatment_rates - control_rates)
    experiments = pd.DataFrame({
        "simulation_id": np.arange(1, trials + 1),
        "control_conversions": counts[:, 0],
        "treatment_conversions": counts[:, 1],
        "observed_control_rate": control_rates,
        "observed_treatment_rate": treatment_rates,
        "absolute_uplift_percentage_points": uplift,
        "z_statistic": z_statistics,
        "p_value": p_values,
        "statistically_significant": pd.array(decisions, dtype="boolean"),
    })
    significant = int(experiments["statistically_significant"].sum())
    undefined = int(experiments["p_value"].isna().sum())
    effect_size = abs(float(proportion_effectsize(treatment_probability, control_probability)))
    theoretical = float(NormalIndPower().power(
        effect_size=effect_size, nobs1=n, alpha=alpha, ratio=1.0, alternative="two-sided",
    ))
    return MonteCarloResult(
        experiments=experiments,
        control_probability=float(control_probability), treatment_probability=float(treatment_probability),
        sample_size_per_group=n, alpha=float(alpha), seed=int(seed),
        significant_experiments=significant,
        non_significant_experiments=trials - significant - undefined,
        undefined_experiments=undefined,
        empirical_rejection_rate=significant / trials, theoretical_power=theoretical,
        mean_uplift_percentage_points=float(uplift.mean()),
        std_uplift_percentage_points=float(uplift.std(ddof=1)) if trials > 1 else None,
    )


def format_summary(result: MonteCarloResult) -> str:
    """Distinguish power under an effect from false positives under the null."""
    null = result.control_probability == result.treatment_probability
    trials = len(result.experiments)
    se = math.sqrt(result.empirical_rejection_rate * (1 - result.empirical_rejection_rate) / trials)
    lines = [
        "SYNTHETIC Monte Carlo fixed-horizon conversion experiments",
        f"True probabilities: A={result.control_probability:.6g}, B={result.treatment_probability:.6g}",
        f"Users per group: {result.sample_size_per_group}; alpha: {result.alpha:.6g}; "
        f"simulations: {trials}; PCG64 seed: {result.seed}",
        f"Statistically significant experiments: {result.significant_experiments}",
        f"Non-significant experiments: {result.non_significant_experiments}",
        f"Undefined tests: {result.undefined_experiments}",
    ]
    if null:
        lines.extend([
            f"False positives: {result.significant_experiments}",
            f"Empirical false-positive rate: {result.empirical_rejection_rate:.12g}",
            f"Nominal false-positive rate (alpha): {result.alpha:.12g}",
        ])
    else:
        lines.extend([
            f"Empirical statistical power: {result.empirical_rejection_rate:.12g}",
            f"Theoretical power (Phase 1 Cohen's h): {result.theoretical_power:.12g}",
        ])
    lines.append(f"Monte Carlo standard error of rejection rate: {se:.12g}")
    lines.append(f"Mean observed uplift (B - A): {result.mean_uplift_percentage_points:.12g} percentage points")
    sd = ("undefined (one simulation)" if result.std_uplift_percentage_points is None
          else f"{result.std_uplift_percentage_points:.12g} percentage points")
    lines.append(f"Sample standard deviation of observed uplift (ddof=1): {sd}")
    n = result.sample_size_per_group
    if min(n * p for p in (result.control_probability, 1 - result.control_probability,
                          result.treatment_probability, 1 - result.treatment_probability)) < 5:
        lines.append("Warning: small expected conversion/non-conversion counts; "
                     "the normal test approximation may be unreliable.")
    if result.undefined_experiments:
        lines.append("Warning: zero pooled variance makes some tests undefined. "
                     "The rejection-rate denominator includes every simulation.")
    lines.append("Finite simulation noise and differences between the pooled z-test "
                 "and arcsine power approximation can change empirical results.")
    return "\n".join(lines)


def generate_plots(result: MonteCarloResult, output_dir: Path) -> list[Path]:
    """Save two default-style Matplotlib figures for this effect or null run."""
    # Keep Matplotlib's font/config cache writable and within ignored outputs.
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(output_dir.resolve() / ".matplotlib"))
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    null = result.control_probability == result.treatment_probability
    paths = []
    context = (f"{len(result.experiments):,} synthetic experiments; "
               f"{result.sample_size_per_group:,}/arm; seed {result.seed}")

    def figure():
        fig = Figure(figsize=(7, 4.5), layout="constrained")
        FigureCanvasAgg(fig)
        return fig, fig.subplots()

    fig, ax = figure()
    if null:
        p_values = result.experiments["p_value"].dropna()
        ax.hist(p_values, bins=np.linspace(0, 1, 21))
        ax.axvline(result.alpha, linestyle="--", label=f"Alpha = {result.alpha:g}")
        ax.axhline(len(p_values) / 20, linestyle=":", label="Uniform-null reference per bin")
        ax.set(xlabel="Two-sided pooled z-test p-value", ylabel="Number of experiments",
               title=f"P-values under equal true conversion rates\n{context}", xlim=(0, 1))
        path = output_dir / "null_p_value_distribution.png"
    else:
        ax.hist(result.experiments["absolute_uplift_percentage_points"], bins=30)
        ax.axvline(0, linestyle=":", label="No effect")
        true_uplift = 100 * (result.treatment_probability - result.control_probability)
        ax.axvline(true_uplift, linestyle="--", label=f"True uplift = {true_uplift:g} pp")
        ax.set(xlabel="Observed uplift B - A (percentage points)", ylabel="Number of experiments",
               title=f"Distribution of observed conversion uplift\n{context}")
        path = output_dir / "observed_uplift_distribution.png"
    ax.legend()
    fig.savefig(path, dpi=150)
    paths.append(path)

    fig, ax = figure()
    reference = result.alpha if null else result.theoretical_power
    ax.bar(["Empirical", "Nominal alpha" if null else "Theoretical"],
           [result.empirical_rejection_rate, reference])
    ax.axhline(reference, linestyle="--", label=f"Reference = {reference:.4f}")
    upper_limit = max(0.1, 1.4 * max(result.empirical_rejection_rate, reference)) if null else 1.05
    ax.set(ylim=(0, upper_limit), ylabel="False-positive rate" if null else "Statistical power",
           title=("False-positive rate versus nominal alpha" if null
                  else "Empirical versus theoretical statistical power") + f"\n{context}")
    for index, value in enumerate([result.empirical_rejection_rate, reference]):
        ax.annotate(f"{value:.4f}", (index, value), xytext=(0, 5),
                    textcoords="offset points", ha="center")
    ax.legend()
    path = output_dir / ("false_positive_comparison.png" if null else "power_comparison.png")
    fig.savefig(path, dpi=150)
    paths.append(path)
    return paths


def main(argv: Sequence[str] | None = None) -> int:
    """Run one scenario, save trial rows, and optionally generate its plots."""
    parser = argparse.ArgumentParser(
        description="Monte Carlo power or false positives for a two-sided conversion test.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--control-probability", type=float, default=0.12)
    parser.add_argument("--treatment-probability", type=float, default=0.14)
    parser.add_argument("--sample-size", type=int, default=None,
                        help="Users per group; default is the Phase 1 example size (4433)")
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--simulations", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--no-plots", action="store_true", help="Save results without PNG figures")
    args = parser.parse_args(argv)
    try:
        result = run_monte_carlo(
            args.control_probability, args.treatment_probability, args.sample_size,
            alpha=args.alpha, simulations=args.simulations, seed=args.seed,
        )
        args.output_dir.mkdir(parents=True, exist_ok=True)
        null = args.control_probability == args.treatment_probability
        csv_path = args.output_dir / ("null_simulations.csv" if null else "power_simulations.csv")
        result.experiments.to_csv(csv_path, index=False, encoding="utf-8", lineterminator="\n")
        plots = [] if args.no_plots else generate_plots(result, args.output_dir)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(format_summary(result))
    print(f"Saved trial results: {csv_path.resolve()}")
    for plot in plots:
        print(f"Saved plot: {plot.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
