with source as (
    select * from {{ source('silver', 'orders') }}
),

renamed as (
    select
        order_id,
        customer_id,
        order_status,
        order_purchase_timestamp,
        order_approved_at,
        order_delivered_carrier_date,
        order_delivered_customer_date,
        order_estimated_delivery_date,
        -- Analytical metrics already computed in Silver
        actual_delivery_days,
        estimated_delivery_days,
        approval_delay_hours,
        case when is_delivered_on_time = 1 then true else false end as is_delivered_on_time,
        purchase_year,
        purchase_month
    from source
)

select * from renamed
