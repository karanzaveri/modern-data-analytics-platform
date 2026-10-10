{% set observation_end_date = cohort_observation_end_date() %}

with cohorts as (

    -- Assignments already use full history; exclude later cohorts without reassigning them.
    select customer_unique_id, cohort_month
    from {{ ref('int_customer_cohorts') }}
    where cohort_month <= date('{{ observation_end_date }}')

),

cohort_sizes as (

    select
        cohort_month,
        count(distinct customer_unique_id) as cohort_size
    from cohorts
    group by cohort_month

),

observation_grid as (

    select
        cohort_month,
        activity_month,
        cohort_size
    from cohort_sizes
    cross join unnest(generate_date_array(
        cohort_month,
        date_trunc(date('{{ observation_end_date }}'), month),
        interval 1 month
    )) as activity_month

),

retained_counts as (

    select
        cohorts.cohort_month,
        activity.activity_month,
        count(distinct activity.customer_unique_id) as retained_customers
    from {{ ref('int_customer_monthly_activity') }} as activity
    inner join cohorts
        on activity.customer_unique_id = cohorts.customer_unique_id
    -- A month-end cutoff includes every qualifying purchase date in this month.
    where activity.activity_month <= date_trunc(date('{{ observation_end_date }}'), month)
    group by cohorts.cohort_month, activity.activity_month

),

final as (

    select
        grid.cohort_month,
        grid.activity_month,
        date_diff(grid.activity_month, grid.cohort_month, month) as months_since_first_purchase,
        grid.cohort_size,
        coalesce(retained.retained_customers, 0) as retained_customers,
        safe_divide(coalesce(retained.retained_customers, 0), grid.cohort_size) as retention_rate
    from observation_grid as grid
    left join retained_counts as retained
        on grid.cohort_month = retained.cohort_month
       and grid.activity_month = retained.activity_month

)

select *
from final
