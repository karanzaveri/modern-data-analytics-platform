{% set growth_metrics = [
    {
        "current": "delivered_revenue",
        "previous": "previous_month_revenue",
        "alias": "revenue_growth_pct"
    },
    {
        "current": "order_count",
        "previous": "previous_month_order_count",
        "alias": "order_growth_pct"
    }
] %}



with reporting_window as (

    select
        order_month,
        order_count,
        delivered_order_count,
        unique_customers,
        delivered_revenue,
        delivered_average_order_value,
        delivered_merchandise_value,
        delivered_freight_value

    from {{ ref('monthly_revenue_metrics') }}

    where order_month between date('2017-01-01')
                          and date('2018-08-01')

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

    from reporting_window

),

final as (

    select
        *,

        {% for metric in growth_metrics %}

        {{ calculate_growth_pct(
            metric["current"],
            metric["previous"],
            "order_month",
            "previous_order_month"
        ) }} as {{ metric["alias"] }}

        {% if not loop.last %},{% endif %}

        {% endfor %}

    from with_previous_month

)

select *
from final
order by order_month