/* ==============================================================================
   MODEL: mart_delivery_performance
   LAYER: Analytics Data Mart
   AUTHOR: Assistant Reference Model
   ==============================================================================
   DESCRIPTION:
     Logistics delivery performance scorecard by shipping corridor (Origin State
     -> Destination State).

   BUSINESS VALUE:
     Identifies geographic bottlenecks, carrier delay rates, and SLA compliance
     across Brazil's postal logistics corridors.
   ============================================================================== */

with orders as (
    select * from {{ ref('fct_orders') }}
    where order_status = 'delivered'
      and order_delivered_customer_date is not null
),

customers as (
    select customer_id, customer_state from {{ ref('stg_customers') }}
),

items as (
    select distinct order_id, seller_id from {{ ref('stg_order_items') }}
),

sellers as (
    select seller_id, seller_state from {{ ref('stg_sellers') }}
),

corridors as (
    select
        o.order_id,
        coalesce(s.seller_state, 'Unknown') as origin_seller_state,
        coalesce(c.customer_state, 'Unknown') as destination_customer_state,
        case
            when s.seller_state = c.customer_state then 'Intrastate (Same State)'
            else 'Interstate (Cross-Country)'
        end as shipment_type,
        o.actual_delivery_days,
        o.estimated_delivery_days,
        o.approval_delay_hours,
        o.is_delivered_on_time,
        o.order_freight
    from orders o
    inner join customers c
        on o.customer_id = c.customer_id
    left join items i
        on o.order_id = i.order_id
    left join sellers s
        on i.seller_id = s.seller_id
),

route_metrics as (
    select
        origin_seller_state,
        destination_customer_state,
        shipment_type,
        count(distinct order_id) as delivered_orders_count,
        round(avg(actual_delivery_days), 2) as avg_actual_delivery_days,
        round(avg(estimated_delivery_days), 2) as avg_estimated_delivery_days,
        round(
            (
                sum(case when is_delivered_on_time then 1 else 0 end) * 100.0
                / count(distinct order_id)
            ),
            2
        ) as on_time_delivery_rate_pct,
        round(avg(order_freight), 2) as avg_freight_cost
    from corridors
    group by
        origin_seller_state,
        destination_customer_state,
        shipment_type
)

select * from route_metrics
where delivered_orders_count >= 10  -- Filter out rare 1-off routes for meaningful statistics
order by delivered_orders_count desc
