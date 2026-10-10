{% set observation_end_date = cohort_observation_end_date() %}

-- Independently reconcile monthly-derived results against exact qualifying purchase dates.
-- Full outer comparison also catches missing/extra customers and altered cohort assignments.
with eligible_cohorts as (

    select customer_unique_id, cohort_month
    from {{ ref('int_customer_cohorts') }}
    where cohort_month <= date('{{ observation_end_date }}')

),

qualifying_orders as (

    select customer_unique_id, order_id, order_purchase_date
    from {{ ref('fct_orders') }}
    where order_status = 'delivered'
      and customer_unique_id is not null
      and trim(customer_unique_id) != ''
      and order_purchase_date <= date('{{ observation_end_date }}')

),

expected as (

    select
        cohorts.customer_unique_id,
        cohorts.cohort_month,
        count(distinct orders.order_id) as delivered_orders,
        count(distinct date_trunc(orders.order_purchase_date, month)) as active_months,
        min(if(
            date_trunc(orders.order_purchase_date, month) > cohorts.cohort_month,
            date_diff(orders.order_purchase_date, cohorts.cohort_month, month),
            null
        )) as first_return_month_age,
        case
            when last_day(date_add(cohorts.cohort_month, interval 3 month))
                <= date('{{ observation_end_date }}') then
                countif(date_diff(orders.order_purchase_date, cohorts.cohort_month, month)
                    between 1 and 3) > 0
            else cast(null as bool)
        end as returned_within_3_months
    from eligible_cohorts as cohorts
    left join qualifying_orders as orders
        on cohorts.customer_unique_id = orders.customer_unique_id
    group by cohorts.customer_unique_id, cohorts.cohort_month

)

select
    expected.customer_unique_id as expected_customer_unique_id,
    actual.customer_unique_id as actual_customer_unique_id
from expected
full outer join {{ ref('customer_repeat_behavior') }} as actual
    on expected.customer_unique_id = actual.customer_unique_id
where expected.customer_unique_id is null
   or actual.customer_unique_id is null
   or actual.cohort_month is distinct from expected.cohort_month
   or actual.total_delivered_orders_through_cutoff is distinct from expected.delivered_orders
   or actual.active_month_count_through_cutoff is distinct from expected.active_months
   or actual.first_return_month_age is distinct from expected.first_return_month_age
   or actual.has_returned_within_3_months is distinct from expected.returned_within_3_months
