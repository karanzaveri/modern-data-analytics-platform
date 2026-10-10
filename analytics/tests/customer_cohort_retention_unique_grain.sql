-- No cohort may have more than one row at the same calendar-month age.
select
    cohort_month,
    months_since_first_purchase,
    count(*) as record_count
from {{ ref('customer_cohort_retention') }}
group by cohort_month, months_since_first_purchase
having count(*) > 1
