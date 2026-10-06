"""Verify reporting-month selection without connecting to BigQuery."""

from datetime import date
import importlib
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


kpi_source = importlib.import_module("ai.fetch_kpis")


@pytest.fixture
def warehouse(monkeypatch):
    row = SimpleNamespace(
        order_month=date(2018, 8, 1),
        order_count=10,
        delivered_order_count=9,
        unique_customers=10,
        delivered_revenue=100.25,
        delivered_average_order_value=11.14,
        previous_month_revenue=None,
        revenue_growth_pct=None,
        previous_month_order_count=None,
        order_growth_pct=None,
        delivered_merchandise_value=80.25,
        delivered_freight_value=20.0,
    )
    client = Mock()
    client.query.return_value.result.return_value = [row]
    monkeypatch.setattr(kpi_source.bigquery, "Client", Mock(return_value=client))
    return client, row


def test_no_month_selects_latest_reporting_row(warehouse):
    client, _ = warehouse
    kpis = kpi_source.fetch_kpis()

    query = " ".join(client.query.call_args.args[0].split())
    assert "FROM `mda-platform-2026.analytics_dev.monthly_revenue_reporting`" in query
    assert "WHERE" not in query
    assert query.endswith("ORDER BY order_month DESC LIMIT 1")
    assert kpis["order_month"] == "2018-08-01"


def test_explicit_month_filters_reporting_rows(warehouse):
    client, row = warehouse
    row.order_month = date(2018, 7, 1)

    assert kpi_source.fetch_kpis("2018-07")["order_month"] == "2018-07-01"
    query = " ".join(client.query.call_args.args[0].split())
    assert "WHERE FORMAT_DATE('%Y-%m', order_month) = '2018-07'" in query
    assert query.endswith("ORDER BY order_month DESC LIMIT 1")


@pytest.mark.parametrize("month, message", [
    (None, "No KPI rows returned from BigQuery."),
    ("2026-10", "No KPI row found for month 2026-10."),
])
def test_no_rows_raises_clear_error(warehouse, month, message):
    client, _ = warehouse
    client.query.return_value.result.return_value = []

    with pytest.raises(ValueError) as error:
        kpi_source.fetch_kpis(month)
    assert str(error.value) == message


@pytest.mark.parametrize("month", ["2018-99", "2018/08", "August 2018"])
def test_invalid_month_never_queries_bigquery(warehouse, month):
    client, _ = warehouse
    with pytest.raises(ValueError, match="Month must use YYYY-MM format"):
        kpi_source.fetch_kpis(month)
    client.query.assert_not_called()
