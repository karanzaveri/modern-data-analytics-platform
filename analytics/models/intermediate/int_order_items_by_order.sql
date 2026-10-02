with order_items as (

    select *
    from {{ ref('int_order_items_enriched') }}

),

aggregated as (

    select
        order_id,

        count(*) as item_count,
        count(distinct product_id) as distinct_product_count,
        count(distinct seller_id) as distinct_seller_count,

        sum(price) as merchandise_value,
        sum(freight_value) as freight_value,
        sum(item_total_value) as total_item_value

    from order_items

    group by order_id

)

select *
from aggregated