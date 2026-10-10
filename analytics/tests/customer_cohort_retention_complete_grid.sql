{% set observation_end_date = cohort_observation_end_date() %}

-- Together with grain/date tests, row count and endpoints detect missing months.
-- Compare denominators with the original members, not just other mart rows.
with expected_cohorts as (
    select cohort_month, count(distinct customer_unique_id) as cohort_size
    from {{ ref('int_customer_cohorts') }}
    where cohort_month <= date('{{ observation_end_date }}')
    group by cohort_month
),
actual_cohorts as (
    select
        cohort_month,
        count(*) as month_count,
        min(activity_month) as first_activity_month,
        max(activity_month) as last_activity_month,
        min(cohort_size) as minimum_cohort_size,
        max(cohort_size) as maximum_cohort_size
    from {{ ref('customer_cohort_retention') }}
    group by cohort_month
)
select
    expected.cohort_month as expected_cohort_month,
    actual.cohort_month as actual_cohort_month
from expected_cohorts as expected
full outer join actual_cohorts as actual
    on expected.cohort_month = actual.cohort_month
where expected.cohort_month is null
   or actual.cohort_month is null
   or expected.cohort_size != actual.minimum_cohort_size
   or expected.cohort_size != actual.maximum_cohort_size
   or actual.first_activity_month != expected.cohort_month
   or actual.last_activity_month != date_trunc(date('{{ observation_end_date }}'), month)
   or actual.month_count != date_diff(
       date_trunc(date('{{ observation_end_date }}'), month), expected.cohort_month, month
   ) + 1
