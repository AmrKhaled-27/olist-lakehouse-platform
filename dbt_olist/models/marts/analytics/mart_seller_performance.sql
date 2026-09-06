with sellers as (
    select * from {{ ref('dim_sellers') }}
    where total_orders_fulfilled > 0
),

ranked_sellers as (
    select 
      seller_id,
      seller_city,
      seller_state,
      total_items_sold,
      total_orders_fulfilled,
      total_sales_volume,
      avg_item_price,
      avg_review_score,
      dense_rank() over (order by total_sales_volume desc) as revenue_rank,
      case 
        when total_sales_volume >= 50000 and avg_review_score >= 4.0 then 'Elite Partner'
        when total_sales_volume >= 10000 and avg_review_score >= 3.5 then 'Top Seller'
        when avg_review_score < 3.0 then 'Action Required (Low Ratings)'
        else 'Standard Seller'
      end as seller_tier
    from sellers
)

select * from ranked_sellers
