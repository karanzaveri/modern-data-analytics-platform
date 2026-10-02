with orders as (

    select *
    from {{ ref('fct_orders') }}

),

customer_metrics as (

    select
        customer_unique_id,

        min(order_purchase_date) as first_order_date,
        max(order_purchase_date) as last_order_date,

        count(*) as order_count,

        countif(order_status = 'delivered') as delivered_order_count,
        countif(total_payment_value is null) as orders_missing_payment,

        sum(total_payment_value) as total_spend,

        avg(total_payment_value) as average_order_value,

        sum(merchandise_value) as total_merchandise_value,

        sum(freight_value) as total_freight_value

    from orders

    group by customer_unique_id

)

select *
from customer_metrics