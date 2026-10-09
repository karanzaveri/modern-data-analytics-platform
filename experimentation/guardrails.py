"""Descriptive guardrail thresholds, without claims of statistical safety."""

import argparse
from dataclasses import dataclass
import math
from numbers import Real
from typing import Literal, Sequence


Direction = Literal["lower-is-better", "higher-is-better"]
Availability = Literal["available", "missing", "incomplete"]
Assessment = Literal["Within specified threshold", "Threshold breached", "Insufficient data"]


@dataclass(frozen=True)
class GuardrailResult:
    """Metric context and a descriptive assessment in the supplied unit."""

    name: str
    direction: Direction
    control_value: float | None
    treatment_value: float | None
    max_tolerable_deterioration: float
    unit: str
    definition: str
    data_availability: Availability
    assessment: Assessment
    treatment_minus_control: float | None
    signed_deterioration: float | None


def evaluate_guardrail(
    name: str,
    direction: Direction,
    control_value: float | None,
    treatment_value: float | None,
    max_tolerable_deterioration: float,
    *,
    unit: str,
    definition: str,
    data_availability: Availability = "available",
) -> GuardrailResult:
    """Compare observed deterioration against an inclusive prespecified limit.

    All values and the limit use the same absolute unit, not relative percent.
    For lower-is-better, deterioration is B-A; for higher-is-better it is A-B.
    Negative deterioration represents improvement. A boundary equals 'within'
    (relative roundoff tolerance 1e-12). Missing values, missing data, or
    incomplete data yield 'Insufficient data', never an inferred pass.
    This is not a non-inferiority test and does not establish statistical safety.
    """
    for label, text in (("name", name), ("unit", unit), ("definition", definition)):
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"{label} must be a non-blank string.")
    if direction not in ("lower-is-better", "higher-is-better"):
        raise ValueError("direction must be lower-is-better or higher-is-better.")
    if data_availability not in ("available", "missing", "incomplete"):
        raise ValueError("data_availability must be available, missing, or incomplete.")
    if (isinstance(max_tolerable_deterioration, bool)
            or not isinstance(max_tolerable_deterioration, Real)
            or not math.isfinite(max_tolerable_deterioration)
            or max_tolerable_deterioration < 0):
        raise ValueError("max_tolerable_deterioration must be a finite non-negative number.")
    for label, value in (("control_value", control_value), ("treatment_value", treatment_value)):
        if value is not None and (isinstance(value, bool) or not isinstance(value, Real)
                                  or not math.isfinite(value)):
            raise ValueError(f"{label} must be finite numeric data or None.")

    difference = deterioration = None
    assessment: Assessment = "Insufficient data"
    if data_availability == "available" and control_value is not None and treatment_value is not None:
        difference = float(treatment_value - control_value)
        if not math.isfinite(difference):
            raise ValueError("Metric difference exceeds numeric limits.")
        deterioration = difference if direction == "lower-is-better" else -difference
        within = (deterioration <= max_tolerable_deterioration
                  or math.isclose(deterioration, max_tolerable_deterioration,
                                  rel_tol=1e-12, abs_tol=0))
        assessment = "Within specified threshold" if within else "Threshold breached"
    return GuardrailResult(
        name=name, direction=direction,
        control_value=float(control_value) if control_value is not None else None,
        treatment_value=float(treatment_value) if treatment_value is not None else None,
        max_tolerable_deterioration=float(max_tolerable_deterioration),
        unit=unit, definition=definition, data_availability=data_availability,
        assessment=assessment, treatment_minus_control=difference,
        signed_deterioration=deterioration,
    )


def missing_checkout_guardrails() -> list[GuardrailResult]:
    """Declare unobserved metrics; limits are illustrative, not an original plan."""
    specs = [
        ("Payment failures", 0.2, "percentage points",
         "Failed payment attempts as a percentage of all payment attempts."),
        ("Refunds", 0.5, "percentage points",
         "Purchases refunded within 30 days as a percentage of mature purchases."),
        ("Checkout latency", 50.0, "milliseconds",
         "Mean time from checkout initiation to checkout response."),
    ]
    return [evaluate_guardrail(name, "lower-is-better", None, None, threshold,
                               unit=unit, definition=definition, data_availability="missing")
            for name, threshold, unit, definition in specs]


def illustrative_guardrail_scenarios() -> list[GuardrailResult]:
    """Hypothetical examples separate from all original conversion records."""
    specs = missing_checkout_guardrails()
    values = [(1.0, 1.1, "available"), (2.0, 2.6, "available"), (None, None, "missing")]
    return [evaluate_guardrail(spec.name, spec.direction, control, treatment,
                               spec.max_tolerable_deterioration, unit=spec.unit,
                               definition=spec.definition, data_availability=availability)
            for spec, (control, treatment, availability) in zip(specs, values)]


def format_guardrails(results: Sequence[GuardrailResult]) -> str:
    """Keep availability, units, definitions and descriptive categories explicit."""
    lines = ["Descriptive guardrail assessment (not a non-inferiority test):"]
    for result in results:
        observed = ("not evaluated" if result.signed_deterioration is None
                    else f"signed deterioration={result.signed_deterioration:.10g} {result.unit}")
        lines.extend([
            f"- {result.name}: {result.assessment}; data={result.data_availability}; {observed}",
            f"  A={result.control_value}, B={result.treatment_value}; {result.direction}; "
            f"maximum deterioration={result.max_tolerable_deterioration:g} {result.unit}",
            f"  Definition: {result.definition}",
        ])
    lines.append("Within threshold describes an observed comparison; it does not establish statistical safety.")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Show illustrative examples without writing or reading experiment data."""
    parser = argparse.ArgumentParser(description="Illustrative descriptive checkout guardrail examples.")
    parser.parse_args(argv)
    print("HYPOTHETICAL EXAMPLES ONLY: payment failures, refunds and checkout latency "
          "were NOT observed in the original conversion dataset.")
    print("These example limits are not an actual prespecified plan for the original experiment.")
    print(format_guardrails(illustrative_guardrail_scenarios()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
