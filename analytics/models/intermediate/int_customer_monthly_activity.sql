with qualifying_orders as (

    select
        customer_unique_id,
        order_id,
        date_trunc(order_purchase_date, month) as activity_month

    from {{ ref('fct_orders') }}

    where order_status = 'delivered'
      and customer_unique_id is not null
      and trim(customer_unique_id) != ''
      and order_purchase_date is not null

),

monthly_activity as (

    select
        customer_unique_id,
        activity_month,
        count(distinct order_id) as delivered_order_count

    from qualifying_orders

    group by customer_unique_id, activity_month

)

select *
from monthly_activity
