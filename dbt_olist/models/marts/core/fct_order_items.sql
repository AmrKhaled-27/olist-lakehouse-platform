with items as (
    select * from {{ ref('stg_order_items') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
),

products as (
    select * from {{ ref('dim_products') }}
),

final as (
    select 
      oi.order_id, 
      oi.order_item_id, 
      oi.product_id, 
      oi.seller_id, 
      oi.shipping_limit_date, 
      oi.item_price, 
      oi.item_freight, 
      oi.total_item_value, 
      o.customer_id, 
      o.order_status, 
      o.order_purchase_timestamp, 
      p.category_name_english, 
      cast(strftime(o.order_purchase_timestamp, '%Y%m%d') as integer) as purchase_date_key
    from items oi
    inner join orders o on oi.order_id = o.order_id
    left join products p on oi.product_id = p.product_id
)

-- TEMPORARY PLACEHOLDER: Replace this with `select * from final` once you complete the TODOs above!
select * from final
