with customers as (
    select * from {{ ref('dim_customers') }}
    where last_order_timestamp is not null
),

benchmark_date as (
    select max(last_order_timestamp) as max_date
    from customers
),

segmented as (
  select 
    c.customer_unique_id,
    c.customer_city,
    c.customer_state,
    datediff('day', c.last_order_timestamp, b.max_date) as recency_days,
    c.lifetime_orders_count  as frequency_orders,
    c.lifetime_spend_total as monetary_total_spend,
    case 
        when c.lifetime_orders_count > 1 and recency_days <= 90  then 'Champions'
        when c.lifetime_orders_count > 1 and recency_days > 90   then 'Loyal Customers'
        when c.lifetime_orders_count = 1 and recency_days <= 180 then 'Recent One-Time Buyers'
        else 'Lost / Churned Customers'
    end as rfm_segment
  from customers c
  cross join benchmark_date b
)

select * from segmented
