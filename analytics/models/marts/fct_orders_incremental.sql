{{ config(
    materialized='incremental',
    unique_key='order_id'
) }}

with orders as (

    select *
    from {{ ref('int_orders_with_customers') }}

    {% if is_incremental() %}

    where order_purchase_timestamp > (
        select max(order_purchase_timestamp)
        from {{ this }}
    )

    {% endif %}

),

payments as (

    select *
    from {{ ref('int_payments_by_order') }}

),

order_items as (

    select *
    from {{ ref('int_order_items_by_order') }}

),

joined as (

    select
        orders.order_id,
        orders.customer_id,
        orders.customer_unique_id,
        orders.customer_city,
        orders.customer_state,
        orders.order_status,

        orders.order_purchase_timestamp,
        orders.order_approved_at,
        orders.order_delivered_carrier_date,
        orders.order_delivered_customer_date,
        orders.order_estimated_delivery_date,

        date(orders.order_purchase_timestamp) as order_purchase_date,

        timestamp_diff(
            orders.order_delivered_customer_date,
            orders.order_purchase_timestamp,
            day
        ) as delivery_days,

        timestamp_diff(
            orders.order_delivered_customer_date,
            orders.order_estimated_delivery_date,
            day
        ) as delivery_delay_days,

        order_items.item_count,
        order_items.distinct_product_count,
        order_items.distinct_seller_count,
        order_items.merchandise_value,
        order_items.freight_value,
        order_items.total_item_value,

        payments.total_payment_value,
        payments.payment_record_count,
        payments.max_payment_installments,
        payments.payment_type_count,
        payments.primary_payment_type,

        payments.total_payment_value
            - order_items.total_item_value
            as payment_item_difference

    from orders

    left join order_items
        on orders.order_id = order_items.order_id

    left join payments
        on orders.order_id = payments.order_id

)

select *
from joined