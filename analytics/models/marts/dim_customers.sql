with customer_orders as (

    select
        customer_unique_id,
        customer_id,
        customer_city,
        customer_state,
        order_purchase_timestamp,

        row_number() over (
            partition by customer_unique_id
            order by order_purchase_timestamp desc, order_id desc
        ) as customer_recency_rank

    from {{ ref('int_orders_with_customers') }}

),

latest_customer_record as (

    select
        customer_unique_id,
        customer_id as latest_customer_id,
        customer_city,
        customer_state

    from customer_orders

    where customer_recency_rank = 1

)

select *
from latest_customer_record