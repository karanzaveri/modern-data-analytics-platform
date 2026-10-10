with monthly_activity as (

    select *
    from {{ ref('int_customer_monthly_activity') }}

),

customer_cohorts as (

    select
        customer_unique_id,
        min(activity_month) as cohort_month,
        sum(delivered_order_count) as total_delivered_orders,
        count(distinct activity_month) as active_month_count

    from monthly_activity

    group by customer_unique_id

)

select *
from customer_cohorts
