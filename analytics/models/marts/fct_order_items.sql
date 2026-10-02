with order_items as (

    select *
    from {{ ref('int_order_items_enriched') }}scd ..

)

select
    order_id,
    order_item_id,
    product_id,
    seller_id,
    customer_unique_id,

    order_status,
    order_purchase_timestamp,
    shipping_limit_date,

    price,
    freight_value,
    item_total_value

from order_items