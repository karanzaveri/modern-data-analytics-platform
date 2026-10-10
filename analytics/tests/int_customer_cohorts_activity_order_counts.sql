-- Every active month must contain at least one qualifying delivered order.
select *
from {{ ref('int_customer_cohorts') }}
where active_month_count > total_delivered_orders
