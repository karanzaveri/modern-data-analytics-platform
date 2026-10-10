{% set observation_end_date = cohort_observation_end_date() %}

with eligible_cohorts as (

    -- Keep full-history assignments; exclude later cohorts without reassigning them.
    select customer_unique_id, cohort_month
    from {{ ref('int_customer_cohorts') }}
    where cohort_month <= date('{{ observation_end_date }}')

),

activity_through_cutoff as (

    select
        cohorts.customer_unique_id,
        cohorts.cohort_month,
        activity.activity_month,
        activity.delivered_order_count,
        date_diff(activity.activity_month, cohorts.cohort_month, month) as month_age
    from eligible_cohorts as cohorts
    inner join {{ ref('int_customer_monthly_activity') }} as activity
        on cohorts.customer_unique_id = activity.customer_unique_id
    -- The shared macro rejects partial months, so this includes no later purchases.
    where activity.activity_month <= date_trunc(date('{{ observation_end_date }}'), month)

),

customer_activity as (

    select
        customer_unique_id,
        cohort_month,
        sum(delivered_order_count) as total_delivered_orders_through_cutoff,
        count(distinct activity_month) as active_month_count_through_cutoff,
        countif(month_age between 1 and 3) > 0 as observed_return_within_3_months,
        min(if(month_age > 0, month_age, null)) as first_return_month_age,
        last_day(date_add(cohort_month, interval 3 month))
            <= date('{{ observation_end_date }}') as has_complete_3_month_followup
    from activity_through_cutoff
    group by customer_unique_id, cohort_month

)

select
    customer_unique_id,
    cohort_month,
    total_delivered_orders_through_cutoff,
    active_month_count_through_cutoff,
    total_delivered_orders_through_cutoff >= 2 as is_repeat_purchaser,
    active_month_count_through_cutoff >= 2 as has_returned_later_month,
    case
        when has_complete_3_month_followup then observed_return_within_3_months
        else cast(null as bool)
    end as has_returned_within_3_months,
    first_return_month_age,
    has_complete_3_month_followup,
    case
        when total_delivered_orders_through_cutoff = 1 then 'Single-purchase'
        when total_delivered_orders_through_cutoff >= 2
            and active_month_count_through_cutoff = 1 then 'Same-month repeat only'
        when active_month_count_through_cutoff >= 2 then 'Cross-month repeat'
    end as customer_segment
from customer_activity
