"""Render the synthetic case study from existing calculation functions."""

import argparse
import os
from pathlib import Path
from typing import TYPE_CHECKING, Sequence

from experimentation.analyze_experiment import ExperimentAnalysis, analyze_experiment
from experimentation.business_impact import BusinessImpact, calculate_business_impact
from experimentation.simulate_experiment import DEFAULT_OUTPUT, simulate_experiment

if TYPE_CHECKING:
    from matplotlib.figure import Figure


DEFAULT_IMAGE = (
    Path(__file__).resolve().parents[1] / "docs" / "images" / "checkout-ab-test-executive-summary.png"
)


def _money(value: float, decimals: int = 0) -> str:
    return f"{'-' if value < 0 else ''}€{abs(value):,.{decimals}f}"


def create_summary_figure(analysis: ExperimentAnalysis, impact: BusinessImpact) -> "Figure":
    """Display supplied results with zero-baseline bars and complete CI bounds.

    All rates, counts, effect estimates and finances come from the existing
    analysis objects. Confidence bounds and economic break-even share explicit
    percentage-point units; the financial scenarios hold economics fixed.
    """
    os.environ.setdefault("MPLCONFIGDIR", str(DEFAULT_OUTPUT.parent / ".matplotlib"))
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    from matplotlib.ticker import FuncFormatter
    from matplotlib.patches import FancyBboxPatch

    if impact.lower is None or impact.upper is None or impact.break_even_uplift_percentage_points is None:
        raise ValueError("The executive figure requires interval scenarios and a defined break-even uplift.")
    navy, teal, rust, grey = "#18334C", "#187C83", "#A64D34", "#536170"
    fig = Figure(figsize=(14, 9), facecolor="white")
    FigureCanvasAgg(fig)
    fig.text(0.065, 0.95, "CHECKOUT REDESIGN  /  EXECUTIVE SUMMARY", fontsize=23,
             weight="bold", color=navy)
    fig.text(0.065, 0.916, "Synthetic experiment • Hypothetical quarterly economics • No production deployment",
             fontsize=12, color=grey)

    def card(x: float, heading: str, value: str, detail: str, color: str) -> None:
        fig.add_artist(FancyBboxPatch((x, 0.79), 0.267, 0.096,
                                     boxstyle="round,pad=0.008", transform=fig.transFigure,
                                     facecolor="#F2F5F7", edgecolor="none", zorder=0))
        fig.text(x + 0.012, 0.86, heading, fontsize=10, weight="bold", color=grey)
        fig.text(x + 0.012, 0.824, value, fontsize=20, weight="bold", color=color)
        fig.text(x + 0.012, 0.802, detail, fontsize=9.5, color=grey)

    status = ("Undefined" if analysis.statistically_significant is None
              else "Significant" if analysis.statistically_significant else "Not significant")
    p_text = "undefined" if analysis.p_value is None else f"{analysis.p_value:.5f}"
    card(0.065, "CONVERSION INFERENCE", status, f"Two-sided p = {p_text}; alpha = 0.05", teal)
    card(0.365, "QUARTERLY NET BENEFIT", _money(impact.point.estimated_net_financial_benefit),
         "Point estimate after implementation costs", rust)
    card(0.665, "ROLLOUT READINESS", "Not ready", "Missing guardrails; synthetic evidence only", rust)

    rates = fig.add_axes([0.09, 0.475, 0.35, 0.235])
    groups = [analysis.control, analysis.treatment]
    values = [100 * group.conversion_rate for group in groups]
    rates.bar(["Control A", "Treatment B"], values, color=[navy, teal], width=0.55)
    rates.set_ylim(0, max(1, max(values) * 1.32))
    rates.set_ylabel("Observed purchase conversion (%)", fontsize=10)
    rates.set_title("Observed conversion rates", loc="left", fontsize=14, weight="bold", pad=20)
    for index, (value, group) in enumerate(zip(values, groups)):
        rates.annotate(f"{value:.3f}%\n{group.conversions:,} / {group.users:,} users",
                       (index, value), xytext=(0, 7), textcoords="offset points",
                       ha="center", va="bottom", fontsize=11, color=navy)

    effect = fig.add_axes([0.565, 0.475, 0.36, 0.235])
    lower, upper = (100 * bound for bound in analysis.confidence_interval)
    point, hurdle = analysis.absolute_uplift_percentage_points, impact.break_even_uplift_percentage_points
    effect.errorbar(point, 0.5, xerr=[[point - lower], [upper - point]], fmt="o",
                    color=teal, capsize=7, linewidth=3, markersize=9)
    effect.axvline(0, color=grey, linestyle=":", label="No conversion effect")
    effect.axvline(hurdle, color=rust, linestyle="--", label=f"Break-even {hurdle:.3f} pp")
    minimum, maximum = min(0, lower, hurdle), max(0, upper, hurdle)
    padding = max(0.2, (maximum - minimum) * 0.12)
    effect.set(xlim=(minimum - padding, maximum + padding), ylim=(0, 1), yticks=[],
               xlabel="Uplift B - A (percentage points)")
    effect.set_title("Conversion effect and economic hurdle", loc="left", fontsize=14,
                     weight="bold", pad=20)
    effect.text(0.03, 0.88, f"Observed uplift: {point:+.3f} pp", transform=effect.transAxes,
                fontsize=12, weight="bold", color=teal)
    effect.text(0.03, 0.08, f"95% Newcombe CI: [{lower:.3f}, {upper:.3f}] pp",
                transform=effect.transAxes, fontsize=10, color=grey)
    effect.legend(loc="upper right", bbox_to_anchor=(1, 0.81), fontsize=9,
                  facecolor="white", edgecolor="none", framealpha=1)

    finances = fig.add_axes([0.09, 0.16, 0.35, 0.22])
    scenarios = [impact.lower, impact.point, impact.upper]
    net_values = [scenario.estimated_net_financial_benefit for scenario in scenarios]
    finances.bar(["Lower effect", "Point estimate", "Upper effect"], net_values,
                 color=["#B9C2CA", rust, "#B9C2CA"], width=0.55)
    finances.axhline(0, color=grey, linewidth=1)
    low, high = min(0, min(net_values)), max(0, max(net_values))
    margin = max(1, (high - low) * 0.18)
    finances.set_ylim(low - margin, high + margin)
    finances.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value / 1000:g}k"))
    finances.set_ylabel("Net financial benefit (EUR)", fontsize=10)
    finances.set_title("Hypothetical quarterly financial impact", loc="left", fontsize=14,
                       weight="bold", pad=20)
    for index, value in enumerate(net_values):
        finances.annotate(_money(value), (index, value), xytext=(0, -13 if value < 0 else 7),
                          textcoords="offset points", ha="center", fontsize=10, color=navy)

    assumptions = fig.add_axes([0.565, 0.16, 0.36, 0.22])
    assumptions.axis("off")
    assumptions.text(0, 1.10, "What this decision still assumes", fontsize=14, weight="bold", color=navy)
    assumptions.text(0, 0.92,
                     f"{impact.projected_eligible_users:,} eligible users receive B rather than A\n"
                     f"{_money(impact.contribution_profit_per_conversion, 2)} contribution per incremental conversion\n"
                     f"{_money(impact.implementation_cost)} one-time cost; {_money(impact.ongoing_costs)} ongoing\n"
                     f"Period: {impact.period}", fontsize=10.5, linespacing=1.7, color=grey, va="top")
    assumptions.text(0, 0.35, "GUARDRAILS NOT OBSERVED", fontsize=10.5, weight="bold", color=rust)
    assumptions.text(0, 0.24, "Payment failures • refunds • checkout latency\n"
                     "Fixed balanced allocation does not validate randomisation.",
                     fontsize=10, linespacing=1.6, color=grey, va="top")
    for ax in (rates, effect, finances):
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=10)

    fig.text(0.065, 0.105, "Financial bounds transform the conversion-effect CI with fixed traffic and economics; "
             "they are not a future-profit prediction interval.", fontsize=9.5, color=grey)
    fig.text(0.065, 0.063, "STAKEHOLDER RECOMMENDATION: Do not proceed to full rollout on this evidence.",
             fontsize=12, weight="bold", color=navy)
    fig.text(0.065, 0.039, "Validate real assignment and instrumentation, collect guardrails, and revisit economics "
             "before a real experiment or rollout decision.", fontsize=10, color=grey)
    return fig


def main(argv: Sequence[str] | None = None) -> int:
    """Regenerate the seed-42 figure in memory without writing experiment CSVs."""
    parser = argparse.ArgumentParser(description="Reproduce the synthetic checkout executive summary image.")
    parser.add_argument("--output", type=Path, default=DEFAULT_IMAGE)
    args = parser.parse_args(argv)
    try:
        if args.output.suffix.lower() != ".png":
            raise ValueError("Executive image output must be a .png file.")
        analysis = analyze_experiment(simulate_experiment())
        impact = calculate_business_impact(
            analysis.control.conversion_rate, analysis.treatment.conversion_rate,
            100_000, 12.0, 40_000.0, difference_confidence_interval=analysis.confidence_interval,
            period="one hypothetical quarter (three months)",
        )
        figure = create_summary_figure(analysis, impact)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(args.output, dpi=160, metadata={"Description": "Synthetic checkout A/B case study; hypothetical economics."})
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(f"Saved reproducible executive summary: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
