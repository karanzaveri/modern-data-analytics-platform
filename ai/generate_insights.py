import json
import os
import argparse

from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from pathlib import Path

from ai.fetch_kpis import fetch_kpis, validate_month
from ai.validate_insights import validate_generated_numbers

class InsightResponse(BaseModel):
    headline: str = Field(
        description="One concise executive headline based only on the supplied KPI values."
    )
    summary: str = Field(
        description="A short business summary of 2 to 3 sentences."
    )
    key_observations: list[str] = Field(
        description="Exactly 3 concise observations grounded in the supplied KPI values."
    )
    watchout: str = Field(
        description="One important caution or issue to monitor."
    )


def generate_insights(kpis: dict) -> InsightResponse:
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are a data analyst writing a concise monthly executive performance summary.

Use ONLY the KPI data supplied below.

Rules:
- Use only the KPI data supplied below.
- Do not invent numbers.
- Do not invent causes or explanations.
- Do not speculate about product mix, pricing, customer behaviour, seasonality,
  promotions, market conditions, or operational causes unless those facts are
  explicitly included in the supplied data.
- Do not claim that merchandise value or freight value are components of
  delivered revenue.
- Treat delivered revenue, merchandise value, and freight value as separate
  reported metrics.
- Never repeat the raw numeric values of previous_month_revenue or
  previous_month_order_count in any headline, summary, key observation, or watchout.
- These prior-period fields are trusted context only; do not quote their values,
  even when using natural-language names for the metrics.
- For prior-period comparisons, use the already supplied revenue_growth_pct and
  order_growth_pct instead of quoting previous-period amounts or counts.
- Current-period numeric values remain allowed: delivered_revenue, order_count,
  delivered_order_count, unique_customers, delivered_average_order_value,
  delivered_merchandise_value, and delivered_freight_value.
- Clearly distinguish observations from explanations.
- If the data does not explain why something happened, say that the cause
  cannot be determined from the supplied KPIs.
- The watchout must describe an observed risk or divergence, not an
  unsupported potential cause.
- Never expose raw field names, database column names, Python variable names,
  snake_case identifiers, or internal metric names in stakeholder-facing narrative.
- This prohibition applies to every headline, summary, key observation, and watchout;
  keep the required JSON response schema unchanged.
- Use the following natural-language equivalents instead of internal identifiers:
  previous_month_revenue -> previous month's revenue
  previous_month_order_count -> previous month's order count
  revenue_growth_pct -> revenue growth
  order_growth_pct -> order growth
  delivered_order_count -> delivered orders
  order_count -> total orders
- Before returning the response, rewrite any raw column name, Python variable name,
  snake_case identifier, or internal metric name into natural business language.
- Mention specific percentages or values when useful.
- Keep the language concise and business-focused.
- Do not introduce outside information.
- When mentioning a numeric value, copy it exactly from the supplied KPI data.
- Never reconstruct, estimate, round, transpose, or recalculate supplied KPI values.
- Before returning the response, verify every numeric value character-for-character
  against the supplied KPI data.
- If a supplied growth metric is unavailable, describe the comparison qualitatively
  without quoting prior-period raw values or calculating a new numeric metric.
- Write for a business stakeholder, not a data engineer.
- Never expose database or Python field names such as order_count,
  revenue_growth_pct, delivered_order_count, or previous_month_revenue.
- Convert the reporting date into natural language such as "July 2018".
- Format large monetary values with commas and 2 decimal places when mentioned.
- Express growth metrics using the % symbol.
- Prefer material business observations over obvious statements.
- The watchout should highlight the most meaningful divergence or risk visible
  in the supplied KPIs.
- The watchout should focus on the most meaningful supplied KPI divergence.
- Prefer comparing supplied growth metrics over calculating differences between counts.
- Do not calculate or introduce new numeric values derived from the supplied KPIs.
- If a difference, ratio, percentage, or other derived metric is not explicitly supplied,
  describe the relationship qualitatively without calculating a new number.


KPI data:
{json.dumps(kpis, indent=2)}
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=InsightResponse,
            temperature=0,
        ),
    )

    return InsightResponse.model_validate_json(response.text)


def generate_validated_insights(
    kpis: dict,
    max_attempts: int = 2,
) -> InsightResponse:
    """Retry numeric validation failures within a fixed generation limit."""
    if (
        not isinstance(max_attempts, int)
        or isinstance(max_attempts, bool)
        or max_attempts < 1
    ):
        raise ValueError("max_attempts must be a positive integer.")

    for attempt in range(1, max_attempts + 1):
        insights = generate_insights(kpis)
        try:
            validate_generated_numbers(insights, kpis)
        except ValueError as exc:
            print(f"Numeric validation failed ({attempt}/{max_attempts}): {exc}")
            if attempt == max_attempts:
                raise ValueError(
                    "Unable to generate numerically grounded insights "
                    f"after {max_attempts} attempts."
                ) from exc
        else:
            return insights


def save_insights(insights: InsightResponse, kpis: dict) -> Path:
    output_dir = Path(__file__).parent / "outputs"
    output_dir.mkdir(exist_ok=True)

    month = kpis["order_month"][:7]

    output_path = output_dir / f"monthly_insights_{month}.json"

    payload = {
        "kpis": kpis,
        "insights": insights.model_dump(),
    }

    output_path.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    return output_path

def render_markdown_report(
    insights: InsightResponse,
    kpis: dict,
) -> str:
    month_label = kpis["order_month"][:7]
    observations = "\n".join(f"- {item}" for item in insights.key_observations)

    return f"""# Monthly Business Insights — {month_label}

## Headline

{insights.headline}

## Executive Summary

{insights.summary}

## Key Observations

{observations}

## Watchout

{insights.watchout}

## KPI Snapshot

| Metric | Value |
|---|---:|
| Delivered Revenue | {kpis["delivered_revenue"]:,.2f} |
| Revenue Growth | {kpis["revenue_growth_pct"]:.2f}% |
| Total Orders | {kpis["order_count"]:,} |
| Delivered Orders | {kpis["delivered_order_count"]:,} |
| Order Growth | {kpis["order_growth_pct"]:.2f}% |
| Unique Customers | {kpis["unique_customers"]:,} |
| Delivered AOV | {kpis["delivered_average_order_value"]:,.2f} |
| Merchandise Value | {kpis["delivered_merchandise_value"]:,.2f} |
| Freight Value | {kpis["delivered_freight_value"]:,.2f} |

---
Generated from validated warehouse KPIs.
"""

def save_markdown_report(
    insights: InsightResponse,
    kpis: dict,
) -> Path:
    output_dir = Path(__file__).parent / "outputs"
    output_dir.mkdir(exist_ok=True)

    month = kpis["order_month"][:7]

    output_path = output_dir / f"monthly_insights_{month}.md"

    report = render_markdown_report(insights, kpis)

    output_path.write_text(
        report,
        encoding="utf-8",
    )

    return output_path

def parse_reporting_month(value: str) -> str:
    """Reject invalid CLI months before fetching KPIs or generating insights."""
    try:
        return validate_month(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate validated AI insights from monthly warehouse KPIs."
    )

    parser.add_argument(
        "--month",
        type=parse_reporting_month,
        help="Reporting month in YYYY-MM format. Defaults to latest available month.",
    )

    return parser.parse_args()

def main() -> None:
    args = parse_args()

    kpis = fetch_kpis(args.month)
    print(f"Reporting month: {kpis['order_month'][:7]}")
    insights = generate_validated_insights(kpis)

    json_path = save_insights(insights, kpis)
    markdown_path = save_markdown_report(insights, kpis)

    print("AI response validation passed.")
    print(f"Saved JSON report to: {json_path}")
    print(f"Saved Markdown report to: {markdown_path}")


if __name__ == "__main__":
    main()
