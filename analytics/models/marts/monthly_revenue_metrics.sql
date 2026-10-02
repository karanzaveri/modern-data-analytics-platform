with orders as (

    select *
    from {{ ref('fct_orders') }}

),

monthly_metrics as (

    select
        date_trunc(order_purchase_date, month) as order_month,

        count(*) as order_count,

        countif(order_status = 'delivered') as delivered_order_count,

        count(distinct customer_unique_id) as unique_customers,

        sum(
            case
                when order_status = 'delivered'
                then total_payment_value
            end
        ) as delivered_revenue,

        avg(
            case
                when order_status = 'delivered'
                then total_payment_value
            end
        ) as delivered_average_order_value,

        sum(
            case
                when order_status = 'delivered'
                then merchandise_value
            end
        ) as delivered_merchandise_value,

        sum(
            case
                when order_status = 'delivered'
                then freight_value
            end
        ) as delivered_freight_value

    from orders

    group by order_month

),

with_previous_month as (

    select
        *,

        lag(order_month) over (
            order by order_month
        ) as previous_order_month,

        lag(delivered_revenue) over (
            order by order_month
        ) as previous_month_revenue,

        lag(order_count) over (
            order by order_month
        ) as previous_month_order_count

    from monthly_metrics

),

final as (

    select
        *,

        case
            when previous_month_revenue is not null
             and date_diff(
                    order_month,
                    previous_order_month,
                    month
                 ) = 1
            then round(
                safe_divide(
                    delivered_revenue - previous_month_revenue,
                    previous_month_revenue
                ) * 100,
                2
            )
        end as revenue_growth_pct,

        case
            when previous_month_order_count is not null
             and date_diff(
                    order_month,
                    previous_order_month,
                    month
                 ) = 1
            then round(
                safe_divide(
                    order_count - previous_month_order_count,
                    previous_month_order_count
                ) * 100,
                2
            )
        end as order_growth_pct

    from with_previous_month

)

select *
from final
order by order_month