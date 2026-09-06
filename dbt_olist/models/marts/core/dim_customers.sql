with customers as (
    select * from {{ ref('stg_customers') }}
),

orders as (
    select * from {{ ref('fct_orders') }}
),

customer_geography as (
    select 
      customer_unique_id,
      any_value(customer_zip_code_prefix) as customer_zip_code_prefix,
      any_value(customer_city) as customer_city,
      any_value(customer_state) as customer_state
    from customers
    group by customer_unique_id
),

customer_orders_summary as (
    select 
      customer_unique_id,
      min(order_purchase_timestamp) as first_order_timestamp,
      max(order_purchase_timestamp) as last_order_timestamp,
      count(order_id) as lifetime_orders_count,
      sum(total_order_value) as lifetime_spend_total
    from orders
    group by customer_unique_id
),

final as (
    select g.customer_unique_id,
      g.customer_zip_code_prefix,
      g.customer_city,
      g.customer_state,
      s.first_order_timestamp,
      s.last_order_timestamp,
      s.lifetime_orders_count,
      s.lifetime_spend_total,
      s.lifetime_orders_count > 1 as is_repeat_buyer
    from customer_geography g
    left join customer_orders_summary s
      on g.customer_unique_id = s.customer_unique_id
)

select * from final
