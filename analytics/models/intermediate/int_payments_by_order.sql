with payments as (

    select *
    from {{ ref('stg_payments') }}

),

aggregated as (

    select
        order_id,

        sum(payment_value) as total_payment_value,

        count(*) as payment_record_count,

        max(payment_installments) as max_payment_installments,

        count(distinct payment_type) as payment_type_count,

        array_agg(
            payment_type
            order by payment_value desc
            limit 1
        )[offset(0)] as primary_payment_type

    from payments

    group by order_id

)

select *
from aggregated