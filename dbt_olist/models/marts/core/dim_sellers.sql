with sellers as (
    select * from {{ ref('stg_sellers') }}
),

order_items as (
    select * from {{ ref('stg_order_items') }}
),

reviews as (
    select * from {{ ref('stg_order_reviews') }}
),

seller_metrics as (
    select
      oi.seller_id,
      count(*) as total_items_sold,
      count(distinct oi.order_id) as total_orders_fulfilled,
      sum(oi.item_price) as total_sales_volume,
      round(avg(oi.item_price),2) as avg_item_price,
      round(avg(r.review_score),2) as avg_review_score
    from order_items oi
    left join reviews r on oi.order_id = r.order_id
    group by oi.seller_id
),

final as (
    select 
      s.seller_id,
      s.seller_zip_code_prefix,
      s.seller_city,
      s.seller_state,
      coalesce(m.total_items_sold, 0) as total_items_sold,
      coalesce(m.total_orders_fulfilled, 0) as total_orders_fulfilled,
      coalesce(m.total_sales_volume, 0.0) as total_sales_volume,
      coalesce(m.avg_item_price, 0.0) as avg_item_price,
      m.avg_review_score as avg_review_score
    from sellers s
    left join seller_metrics m on s.seller_id = m.seller_id
)

select * from final
