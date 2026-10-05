# Olist dbt analytics

The `analytics` project transforms six Olist BigQuery raw tables into order, customer, and monthly reporting datasets. It uses the BigQuery adapter and an external profile named `analytics`. FX rates are not referenced by these models.

## Model layers and materializations

The project inventory is **19 models and 95 dbt data tests**. Normal orchestration and validation intentionally exclude `fct_orders_incremental` and its four tests, leaving **18 models and 91 tests**.

| Layer | Contents | Materialization |
| --- | --- | --- |
| Staging | Six models for customers, orders, items, payments, products, sellers | Views |
| Intermediate | Customer-enriched orders, enriched items, order-level item/payment summaries | Views |
| Marts | Facts, dimensions, customer metrics, monthly metrics/reporting | Tables |
| Demonstration | `fct_orders_incremental` | Incremental override |

Staging primarily projects source fields; products also standardizes misspelled column names. It is not a comprehensive cleansing layer.

## Major model grains

| Model | Grain / key |
| --- | --- |
| `int_orders_with_customers` | One row per `order_id` |
| `int_order_items_enriched` | One row per `(order_id, order_item_id)` |
| `int_order_items_by_order` | One item summary per `order_id` |
| `int_payments_by_order` | One payment summary per `order_id` |
| `fct_orders` | One row per `order_id`, including delivery and payment/item metrics |
| `fct_order_items` | One row per `(order_id, order_item_id)` |
| `dim_customers` | One row per `customer_unique_id`, using the latest order's attributes |
| `dim_products` / `dim_sellers` | One row per product / seller identifier |
| `customer_metrics` | One row per `customer_unique_id` |
| `monthly_revenue_metrics` | One row per purchase month present in the data |
| `monthly_revenue_reporting` | One row per purchase month, January 2017 through August 2018 |

## Relationships and metric definitions

Orders join customers on `customer_id`; repeat-customer analysis uses `customer_unique_id`. Items reference orders, products, and sellers. Payments and items are aggregated independently before joining into `fct_orders`, avoiding many-to-many multiplication of monetary totals.

`dim_customers` chooses the latest purchase timestamp, with order ID as a tie-breaker. It is a latest-record dimension, not a historical slowly changing dimension.

Monthly metrics group by **purchase month**. Delivered counts, revenue, average order value, merchandise, and freight describe orders purchased in that month whose current status is delivered. They are not grouped by delivery date. Customer spend and average order value include **all order statuses**; missing payments can remain null.

The reporting mart restricts the broader monthly mart to January 2017 through August 2018, chosen for stable reporting coverage. Growth is recalculated within that window, so its first month has no preceding in-window comparison.

## Tests

Model YAML defines generic `not_null`, `unique`, `accepted_values`, and `relationships` tests. Relationships include orders-to-customers, payments/items-to-orders, and item facts-to-dimensions. The item fact's composite grain is documented but does not currently have a composite-uniqueness test.

The validated non-incremental path has passed against BigQuery for **18 models and 91 data tests**, out of the project totals of **19 models and 95 data tests**. `fct_order_items` has also been built against BigQuery and passed all **9 selected tests**. CI runs the **11 Python tests** with pytest and runs **dbt parse**; it does not connect to BigQuery or execute these warehouse tests.

## Macro and Jinja usage

`ref()` and `source()` declare dependencies. `calculate_growth_pct` uses safe division, rounding, and a consecutive-calendar-month check. `monthly_revenue_reporting` calls it through a Jinja loop for revenue and order growth. The broader monthly metrics model currently implements equivalent growth logic inline.

## Incremental demonstration

`fct_orders_incremental` illustrates incremental materialization with `order_id` as the unique key. Its filter accepts purchase timestamps strictly later than the target maximum. It does not reliably capture updates to existing orders, late arrivals, or records sharing that maximum timestamp; an empty target also needs special handling.

The demonstration is excluded from normal Airflow orchestration and full non-incremental validation. Downstream reporting uses `fct_orders`, not this model.

## Example dbt commands

From `analytics/`, with a configured external profile and BigQuery access:

```bash
dbt parse
dbt run --exclude fct_orders_incremental
dbt test --exclude fct_orders_incremental
dbt run --select fct_order_items
dbt test --select fct_order_items
```

The selected item build assumes its upstream relations already exist. For Compose equivalents, see the [root README](../README.md). Rebuild the image after model edits because SQL is copied at build time.

`dbt parse` needs a valid profile but does not execute warehouse queries or guarantee executable BigQuery SQL. Sources currently point to `mda-platform-2026.raw`; another project requires updating source and ingestion configuration as well as the profile. No credentials belong in this directory.
