/* ==============================================================================
   MODEL: fct_orders
   LAYER: Core Fact Table
   AUTHOR: Assistant Reference Model
   ==============================================================================
   DESCRIPTION:
     Central fact table representing e-commerce transactions at the order grain
     (1 row per order). 

   BEST PRACTICE DEMONSTRATED:
     Safe Anti-Fan-Out Aggregations.
     Pre-aggregates line items and payments in separate CTEs BEFORE joining,
     preventing Cartesian multiplication when an order has multiple items and
     multiple split payment methods.
   ============================================================================== */

with orders as (
    select * from {{ ref('stg_orders') }}
),

customers as (
    select * from {{ ref('stg_customers') }}
),

-- Pre-aggregate line items by order_id
items_agg as (
    select
        order_id,
        count(order_item_id) as total_items_count,
        count(distinct product_id) as distinct_products_count,
        count(distinct seller_id) as distinct_sellers_count,
        round(sum(item_price), 2) as order_subtotal,
        round(sum(item_freight), 2) as order_freight,
        round(sum(total_item_value), 2) as total_order_value
    from {{ ref('stg_order_items') }}
    group by order_id
),

-- Pre-aggregate payments by order_id
payments_agg as (
    select
        order_id,
        round(sum(payment_value), 2) as total_payment_value,
        max(payment_installments) as max_installments,
        -- Pick the payment method that had the largest dollar amount
        arg_max(payment_type, payment_value) as primary_payment_type
    from {{ ref('stg_order_payments') }}
    group by order_id
),

-- Pre-aggregate reviews by order_id
reviews_agg as (
    select
        order_id,
        round(avg(review_score), 1) as review_score,
        max(has_review_comment) as has_review_comment
    from {{ ref('stg_order_reviews') }}
    group by order_id
),

joined as (
    select
        o.order_id,
        o.customer_id,
        c.customer_unique_id,
        o.order_status,
        -- Foreign key to dim_dates
        cast(strftime(o.order_purchase_timestamp, '%Y%m%d') as integer) as purchase_date_key,
        o.order_purchase_timestamp,
        o.order_approved_at,
        o.order_delivered_carrier_date,
        o.order_delivered_customer_date,
        o.order_estimated_delivery_date,

        -- Order Financial Measures
        coalesce(i.total_items_count, 0) as total_items_count,
        coalesce(i.distinct_products_count, 0) as distinct_products_count,
        coalesce(i.distinct_sellers_count, 0) as distinct_sellers_count,
        coalesce(i.order_subtotal, 0.0) as order_subtotal,
        coalesce(i.order_freight, 0.0) as order_freight,
        coalesce(i.total_order_value, 0.0) as total_order_value,

        -- Payment Measures
        p.primary_payment_type,
        coalesce(p.max_installments, 1) as max_installments,
        coalesce(p.total_payment_value, 0.0) as total_payment_value,

        -- Review Measures
        r.review_score,
        coalesce(r.has_review_comment, false) as has_review_comment,

        -- Delivery Performance Measures
        o.actual_delivery_days,
        o.estimated_delivery_days,
        o.approval_delay_hours,
        o.is_delivered_on_time,

        -- Partition / Cohort helpers
        o.purchase_year,
        o.purchase_month
    from orders o
    left join customers c
        on o.customer_id = c.customer_id
    left join items_agg i
        on o.order_id = i.order_id
    left join payments_agg p
        on o.order_id = p.order_id
    left join reviews_agg r
        on o.order_id = r.order_id
)

select * from joined
