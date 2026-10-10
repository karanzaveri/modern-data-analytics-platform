{% set observation_end_date = cohort_observation_end_date() %}

-- YAML covers identity, nullability and positive integer counts; test their meaning here.
select *
from {{ ref('customer_repeat_behavior') }}
where trim(customer_unique_id) = ''
   or cohort_month != date_trunc(cohort_month, month)
   or cohort_month > date('{{ observation_end_date }}')
   or active_month_count_through_cutoff > total_delivered_orders_through_cutoff
   or active_month_count_through_cutoff > date_diff(
       date_trunc(date('{{ observation_end_date }}'), month), cohort_month, month
   ) + 1
   or is_repeat_purchaser != (total_delivered_orders_through_cutoff >= 2)
   or has_returned_later_month != (active_month_count_through_cutoff >= 2)
   or has_returned_later_month != (first_return_month_age is not null)
   or (customer_segment = 'Single-purchase'
       and total_delivered_orders_through_cutoff != 1)
   or (customer_segment = 'Same-month repeat only'
       and (total_delivered_orders_through_cutoff < 2
           or active_month_count_through_cutoff != 1))
   or (customer_segment = 'Cross-month repeat'
       and active_month_count_through_cutoff < 2)
   or first_return_month_age > date_diff(
       date_trunc(date('{{ observation_end_date }}'), month), cohort_month, month
   )
   or has_complete_3_month_followup != (
       last_day(date_add(cohort_month, interval 3 month)) <= date('{{ observation_end_date }}')
   )
   or has_returned_within_3_months is distinct from (
       case
           when has_complete_3_month_followup then
               coalesce(first_return_month_age between 1 and 3, false)
           else cast(null as bool)
       end
   )
