/* ==============================================================================
   MODEL: mart_monthly_sales
   LAYER: Analytics Data Mart
   AUTHOR: Assistant Reference Model
   ==============================================================================
   DESCRIPTION:
     Executive monthly sales scorecard. Aggregates delivered/placed orders
     into monthly Gross Merchandise Value (GMV), Average Order Value (AOV),
     customer count, and Month-over-Month (MoM) revenue growth %.

   TECHNIQUE DEMONSTRATED:
     Window functions (LAG) over ordered time-series periods.
   ============================================================================== */

with orders as (
    select * from {{ ref('fct_orders') }}
    -- Exclude canceled or invalid orders from revenue reporting
    where order_status not in ('canceled', 'unavailable')
      and purchase_year is not null
),

monthly_aggregation as (
    select
        purchase_year,
        purchase_month,
        strftime(order_purchase_timestamp, '%Y-%m') as year_month,
        count(order_id) as total_orders,
        count(distinct customer_unique_id) as unique_customers,
        round(sum(total_order_value), 2) as total_gross_revenue,
        round(sum(order_subtotal), 2) as total_item_revenue,
        round(sum(order_freight), 2) as total_freight_revenue,
        round(avg(total_order_value), 2) as average_order_value,
        round(avg(total_items_count), 2) as avg_items_per_order
    from orders
    group by
        purchase_year,
        purchase_month,
        strftime(order_purchase_timestamp, '%Y-%m')
),

with_mom_growth as (
    select
        year_month,
        purchase_year,
        purchase_month,
        total_orders,
        unique_customers,
        total_gross_revenue,
        total_item_revenue,
        total_freight_revenue,
        average_order_value,
        avg_items_per_order,
        -- Prior month revenue via window lag
        lag(total_gross_revenue) over (order by year_month) as prior_month_gross_revenue,
        -- Month-over-month growth percentage
        round(
            (
                (total_gross_revenue - lag(total_gross_revenue) over (order by year_month))
                / nullif(lag(total_gross_revenue) over (order by year_month), 0)
            ) * 100.0,
            2
        ) as mom_revenue_growth_pct
    from monthly_aggregation
)

select * from with_mom_growth
order by year_month
