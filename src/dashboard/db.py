"""Database connector and query manager for the Streamlit dashboard."""

import os
from pathlib import Path
import duckdb
import pandas as pd
import streamlit as st


def get_duckdb_path() -> str:
    """Resolve the absolute path to gold_lakehouse.duckdb."""
    # 1. Check environment variable
    if os.getenv("DUCKDB_PATH"):
        return os.getenv("DUCKDB_PATH")

    # 2. Check standard local paths relative to repository root
    repo_root = Path(__file__).resolve().parent.parent.parent
    local_path = repo_root / "data" / "gold_lakehouse.duckdb"
    if local_path.exists():
        return str(local_path)

    # 3. Check container path
    container_path = Path("/app/data/gold_lakehouse.duckdb")
    if container_path.exists():
        return str(container_path)

    # 4. Fallback default
    return str(local_path)


def get_connection():
    """Get a read-only DuckDB connection."""
    db_path = get_duckdb_path()
    if not os.path.exists(db_path):
        raise FileNotFoundError(
            f"Gold Lakehouse DuckDB database not found at: {db_path}. "
            "Please run 'make dbt-run' first to materialize the Gold tables."
        )
    return duckdb.connect(db_path, read_only=True)


@st.cache_data(ttl=3600)
def load_executive_kpis() -> dict:
    """Load high-level KPI cards for executive overview."""
    con = get_connection()
    try:
        query = """
        SELECT
            round(sum(total_order_value), 2) as total_gmv,
            count(order_id) as total_orders,
            count(distinct customer_unique_id) as total_customers,
            round(avg(total_order_value), 2) as avg_order_value,
            round(avg(review_score), 2) as avg_review_score,
            round(
                sum(case when is_delivered_on_time then 1 else 0 end) * 100.0 / 
                nullif(sum(case when order_status = 'delivered' then 1 else 0 end), 0), 
                2
            ) as on_time_delivery_rate_pct
        FROM main_core.fct_orders
        WHERE order_status not in ('canceled', 'unavailable')
        """
        df = con.execute(query).df()
        return df.to_dict(orient="records")[0]
    finally:
        con.close()


@st.cache_data(ttl=3600)
def load_monthly_sales() -> pd.DataFrame:
    """Load monthly sales and MoM growth scorecard."""
    con = get_connection()
    try:
        query = """
        SELECT
            year_month,
            purchase_year,
            purchase_month,
            total_orders,
            unique_customers,
            total_gross_revenue,
            total_item_revenue,
            total_freight_revenue,
            average_order_value,
            prior_month_gross_revenue,
            mom_revenue_growth_pct
        FROM main_analytics.mart_monthly_sales
        ORDER BY year_month ASC
        """
        return con.execute(query).df()
    finally:
        con.close()


@st.cache_data(ttl=3600)
def load_top_categories(limit: int = 10) -> pd.DataFrame:
    """Load top product categories by gross merchandise volume."""
    con = get_connection()
    try:
        query = f"""
        SELECT
            coalesce(category_name_english, 'Other / Uncategorized') as category_name,
            count(order_item_id) as items_sold,
            round(sum(total_item_value), 2) as total_revenue
        FROM main_core.fct_order_items
        WHERE order_status not in ('canceled', 'unavailable')
        GROUP BY category_name
        ORDER BY total_revenue DESC
        LIMIT {limit}
        """
        return con.execute(query).df()
    finally:
        con.close()


@st.cache_data(ttl=3600)
def load_payment_distribution() -> pd.DataFrame:
    """Load payment methods breakdown."""
    con = get_connection()
    try:
        query = """
        SELECT
            coalesce(primary_payment_type, 'not_defined') as payment_type,
            count(order_id) as orders_count,
            round(sum(total_payment_value), 2) as total_payment_value,
            round(avg(max_installments), 1) as avg_installments
        FROM main_core.fct_orders
        WHERE primary_payment_type is not null
        GROUP BY primary_payment_type
        ORDER BY total_payment_value DESC
        """
        return con.execute(query).df()
    finally:
        con.close()


@st.cache_data(ttl=3600)
def load_delivery_performance() -> pd.DataFrame:
    """Load logistics delivery performance corridors."""
    con = get_connection()
    try:
        query = """
        SELECT
            origin_seller_state,
            destination_customer_state,
            shipment_type,
            delivered_orders_count,
            avg_actual_delivery_days,
            avg_estimated_delivery_days,
            on_time_delivery_rate_pct,
            avg_freight_cost
        FROM main_analytics.mart_delivery_performance
        ORDER BY delivered_orders_count DESC
        """
        return con.execute(query).df()
    finally:
        con.close()


@st.cache_data(ttl=3600)
def load_customer_rfm_segments() -> pd.DataFrame:
    """Load customer RFM marketing segments summary."""
    con = get_connection()
    try:
        query = """
        SELECT
            rfm_segment,
            count(customer_unique_id) as customer_count,
            round(avg(recency_days), 1) as avg_recency_days,
            round(avg(frequency_orders), 2) as avg_frequency_orders,
            round(sum(monetary_total_spend), 2) as total_segment_spend,
            round(avg(monetary_total_spend), 2) as avg_spend_per_customer
        FROM main_analytics.mart_customer_rfm
        GROUP BY rfm_segment
        ORDER BY total_segment_spend DESC
        """
        return con.execute(query).df()
    finally:
        con.close()


@st.cache_data(ttl=3600)
def load_customer_rfm_sample(limit: int = 1000) -> pd.DataFrame:
    """Load sample customer RFM records for scatter plot & table exploration."""
    con = get_connection()
    try:
        query = f"""
        SELECT
            customer_unique_id,
            customer_city,
            customer_state,
            recency_days,
            frequency_orders,
            monetary_total_spend,
            rfm_segment
        FROM main_analytics.mart_customer_rfm
        ORDER BY monetary_total_spend DESC
        LIMIT {limit}
        """
        return con.execute(query).df()
    finally:
        con.close()


@st.cache_data(ttl=3600)
def load_seller_tiers() -> pd.DataFrame:
    """Load seller tier counts and summary."""
    con = get_connection()
    try:
        query = """
        SELECT
            seller_tier,
            count(seller_id) as seller_count,
            round(sum(total_sales_volume), 2) as total_tier_sales,
            round(avg(total_sales_volume), 2) as avg_sales_per_seller,
            round(avg(avg_review_score), 2) as avg_tier_review_score
        FROM main_analytics.mart_seller_performance
        GROUP BY seller_tier
        ORDER BY total_tier_sales DESC
        """
        return con.execute(query).df()
    finally:
        con.close()


@st.cache_data(ttl=3600)
def load_seller_leaderboard(tier_filter: str = "All", min_orders: int = 0) -> pd.DataFrame:
    """Load detailed seller leaderboard with filtering."""
    con = get_connection()
    try:
        tier_clause = ""
        if tier_filter != "All":
            tier_clause = f"AND seller_tier = '{tier_filter}'"

        query = f"""
        SELECT
            revenue_rank,
            seller_id,
            seller_city,
            seller_state,
            seller_tier,
            total_orders_fulfilled,
            total_items_sold,
            total_sales_volume,
            avg_item_price,
            avg_review_score
        FROM main_analytics.mart_seller_performance
        WHERE total_orders_fulfilled >= {min_orders}
        {tier_clause}
        ORDER BY revenue_rank ASC
        LIMIT 200
        """
        return con.execute(query).df()
    finally:
        con.close()
