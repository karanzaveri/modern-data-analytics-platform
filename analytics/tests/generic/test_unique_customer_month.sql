{% test unique_customer_month(model) %}

select
    customer_unique_id,
    activity_month,
    count(*) as record_count

from {{ model }}

group by customer_unique_id, activity_month
having count(*) > 1

{% endtest %}
