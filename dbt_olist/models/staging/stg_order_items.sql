with source as (
    select * from {{ source('silver', 'order_items') }}
),

renamed as (
    select
        order_id,
        order_item_id,
        product_id,
        seller_id,
        shipping_limit_date,
        price as item_price,
        freight_value as item_freight,
        total_item_value
    from source
)

select * from renamed
