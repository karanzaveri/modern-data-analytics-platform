with order_items as (

    select *
    from {{ ref('stg_order_items') }}

),

orders as (

    select *
    from {{ ref('int_orders_with_customers') }}

),

products as (

    select *
    from {{ ref('stg_products') }}

),

sellers as (

    select *
    from {{ ref('stg_sellers') }}

),

joined as (

    select
        order_items.order_id,
        order_items.order_item_id,
        order_items.product_id,
        order_items.seller_id,

        products.product_category_name,
        products.product_weight_g,
        products.product_length_cm,
        products.product_height_cm,
        products.product_width_cm,

        orders.customer_id,
        orders.customer_unique_id,
        orders.customer_city,
        orders.customer_state,

        orders.order_status,
        orders.order_purchase_timestamp,

        order_items.shipping_limit_date,
        order_items.price,
        order_items.freight_value,

        order_items.price + order_items.freight_value
            as item_total_value

    from order_items

    left join orders
        on order_items.order_id = orders.order_id

    left join products
        on order_items.product_id = products.product_id

    left join sellers
        on order_items.seller_id = sellers.seller_id

)

select *
from joined