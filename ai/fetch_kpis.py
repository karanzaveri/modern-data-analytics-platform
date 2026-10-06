import json
from google.cloud import bigquery

PROJECT_ID = "mda-platform-2026"
DATASET = "analytics_dev"
TABLE = "monthly_revenue_reporting"


from datetime import datetime
import json

from google.cloud import bigquery


PROJECT_ID = "mda-platform-2026"
DATASET = "analytics_dev"
TABLE = "monthly_revenue_reporting"


def validate_month(month: str) -> str:
    """Validate YYYY-MM input and return the normalized month string."""
    try:
        parsed = datetime.strptime(month, "%Y-%m")
    except ValueError as exc:
        raise ValueError("Month must use YYYY-MM format, for example 2018-07.") from exc

    return parsed.strftime("%Y-%m")


def fetch_kpis(month: str | None = None):
    """Fetch the requested month, or the latest KPI row when month is omitted."""
    client = bigquery.Client(project=PROJECT_ID)

    where_clause = ""

    if month:
        month = validate_month(month)
        where_clause = f"""
        WHERE FORMAT_DATE('%Y-%m', order_month) = '{month}'
        """

    query = f"""
    SELECT
        order_month,
        order_count,
        delivered_order_count,
        unique_customers,
        delivered_revenue,
        delivered_average_order_value,
        previous_month_revenue,
        revenue_growth_pct,
        previous_month_order_count,
        order_growth_pct,
        delivered_merchandise_value,
        delivered_freight_value
    FROM `{PROJECT_ID}.{DATASET}.{TABLE}`
    {where_clause}
    ORDER BY order_month DESC
    LIMIT 1
    """

    rows = list(client.query(query).result())

    if not rows:
        if month:
            raise ValueError(f"No KPI row found for month {month}.")
        raise ValueError("No KPI rows returned from BigQuery.")

    row = rows[0]

    return {
        "order_month": row.order_month.isoformat(),
        "order_count": row.order_count,
        "delivered_order_count": row.delivered_order_count,
        "unique_customers": row.unique_customers,
        "delivered_revenue": round(row.delivered_revenue, 2),
        "delivered_average_order_value": round(
            row.delivered_average_order_value, 2
        ),
        "previous_month_revenue": round(row.previous_month_revenue, 2)
        if row.previous_month_revenue is not None
        else None,
        "revenue_growth_pct": round(row.revenue_growth_pct, 2)
        if row.revenue_growth_pct is not None
        else None,
        "previous_month_order_count": row.previous_month_order_count,
        "order_growth_pct": round(row.order_growth_pct, 2)
        if row.order_growth_pct is not None
        else None,
        "delivered_merchandise_value": round(
            row.delivered_merchandise_value, 2
        ),
        "delivered_freight_value": round(
            row.delivered_freight_value, 2
        ),
    }


if __name__ == "__main__":
    kpis = fetch_kpis()
    print(json.dumps(kpis, indent=2, default=str))
