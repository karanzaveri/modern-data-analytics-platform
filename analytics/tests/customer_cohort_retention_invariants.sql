{% set observation_end_date = cohort_observation_end_date() %}

-- Cross-column rules complement the YAML null, positivity and integer checks.
select *
from {{ ref('customer_cohort_retention') }}
where retained_customers < 0
   or retained_customers > cohort_size
   or retention_rate < 0
   or retention_rate > 1
   or retention_rate != safe_divide(retained_customers, cohort_size)
   or (months_since_first_purchase = 0 and retention_rate != 1)
   or months_since_first_purchase < 0
   or activity_month != date_trunc(activity_month, month)
   or cohort_month != date_trunc(cohort_month, month)
   or months_since_first_purchase != date_diff(activity_month, cohort_month, month)
   or activity_month > date('{{ observation_end_date }}')
