/* ==============================================================================
   MODEL: dim_dates
   LAYER: Core Dimension
   AUTHOR: Assistant Reference Model
   ==============================================================================
   DESCRIPTION:
     Standard calendar date dimension table covering all Olist order activity
     from 2016 to 2018. Provides rich date attributes for analytics.
   ============================================================================== */

with date_spine as (
    -- Generate continuous daily sequence using DuckDB's range function
    select
        cast(range as date) as date_day
    from range(date '2016-01-01', date '2019-01-01', interval 1 day)
),

calculated_attributes as (
    select
        date_day,
        -- Integer date key for efficient star-schema joins (e.g. 20180501)
        cast(strftime(date_day, '%Y%m%d') as integer) as date_key,
        year(date_day) as year,
        month(date_day) as month,
        strftime(date_day, '%B') as month_name,
        strftime(date_day, '%b') as month_name_short,
        quarter(date_day) as quarter,
        'Q' || quarter(date_day) as quarter_name,
        day(date_day) as day_of_month,
        dayofweek(date_day) as day_of_week_num,
        strftime(date_day, '%A') as day_of_week_name,
        case
            when dayofweek(date_day) in (0, 6) then true
            else false
        end as is_weekend,
        strftime(date_day, '%Y-%m') as year_month
    from date_spine
)

select * from calculated_attributes
order by date_day
