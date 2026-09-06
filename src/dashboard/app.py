import sys
from pathlib import Path

# Ensure repository root is in sys.path
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from src.dashboard.db import (
    load_executive_kpis,
    load_monthly_sales,
    load_top_categories,
    get_duckdb_path,
)

# Set page configuration
st.set_page_config(
    page_title="Olist Lakehouse Intelligence",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .metric-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    .metric-title {
        color: #94a3b8;
        font-size: 0.875rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
    }
    .metric-value {
        color: #f8fafc;
        font-size: 2rem;
        font-weight: 700;
        line-height: 1;
    }
    .metric-subtitle {
        color: #38bdf8;
        font-size: 0.8rem;
        margin-top: 8px;
    }
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 6px;
    }
    .badge-lake { background-color: #0369a1; color: #e0f2fe; }
    .badge-spark { background-color: #c2410c; color: #ffedd5; }
    .badge-dbt { background-color: #b45309; color: #fef3c7; }
    .badge-duckdb { background-color: #047857; color: #d1fae5; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Sidebar
with st.sidebar:
    st.image("https://raw.githubusercontent.com/duckdb/duckdb/master/logo/duckdb.png", width=60)
    st.title("Olist Lakehouse")
    st.caption("End-to-End Medallion Lakehouse Platform")
    
    st.markdown("---")
    st.subheader("🏛️ Architecture Stack")
    st.markdown(
        """
        - **Storage:** MinIO S3 (Bronze & Silver)
        - **Engine:** PySpark 3.5 (ETL & Cleansing)
        - **Modeling:** dbt Core (Star-Schema)
        - **Serving:** DuckDB (In-Process Columnar)
        - **UI:** Streamlit & Plotly
        """
    )
    
    st.markdown("---")
    db_path = get_duckdb_path()
    st.success(f"Connected to Gold DB\n\n`{db_path}`")


# Header Section
st.title("🛍️ Olist E-Commerce Executive Overview")
st.markdown(
    """
    <span class="badge badge-lake">Object Storage: MinIO</span>
    <span class="badge badge-spark">Processing: PySpark</span>
    <span class="badge badge-dbt">Transform: dbt Core</span>
    <span class="badge badge-duckdb">Serving: DuckDB</span>
    """,
    unsafe_allow_html=True,
)
st.write("")

# Load KPIs
try:
    kpis = load_executive_kpis()
    sales_df = load_monthly_sales()
    cat_df = load_top_categories(8)
except Exception as e:
    st.error(f"Error connecting to Gold Lakehouse database: {e}")
    st.stop()

# Row 1: KPI Cards
c1, c2, c3, c4, c5, c6 = st.columns(6)

with c1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Gross Revenue (GMV)</div>
            <div class="metric-value">R$ {kpis['total_gmv']/1e6:.2f}M</div>
            <div class="metric-subtitle">Across all valid orders</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Total Orders</div>
            <div class="metric-value">{kpis['total_orders']:,}</div>
            <div class="metric-subtitle">Completed transactions</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Unique Customers</div>
            <div class="metric-value">{kpis['total_customers']:,}</div>
            <div class="metric-subtitle">Distinct human buyers</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Avg Order Value (AOV)</div>
            <div class="metric-value">R$ {kpis['avg_order_value']:.2f}</div>
            <div class="metric-subtitle">Per transaction basket</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c5:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">On-Time Delivery</div>
            <div class="metric-value">{kpis['on_time_delivery_rate_pct']:.1f}%</div>
            <div class="metric-subtitle">Within SLA estimate</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c6:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Avg Review Score</div>
            <div class="metric-value">⭐ {kpis['avg_review_score']:.2f}</div>
            <div class="metric-subtitle">Out of 5.0 rating</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")
st.write("")

# Row 2: Charts (Monthly GMV & Top Categories)
col_left, col_right = st.columns([3, 2])

with col_left:
    st.subheader("📈 Monthly Gross Revenue & Growth Trend")
    # Filter out partial trailing month if negligible
    filtered_sales = sales_df[sales_df["total_orders"] > 10].copy()

    fig_sales = go.Figure()
    
    # Revenue Bars
    fig_sales.add_trace(
        go.Bar(
            x=filtered_sales["year_month"],
            y=filtered_sales["total_gross_revenue"],
            name="Gross Revenue (BRL)",
            marker=dict(color="#38bdf8", opacity=0.85),
            yaxis="y1",
        )
    )
    
    # MoM Growth Line
    fig_sales.add_trace(
        go.Scatter(
            x=filtered_sales["year_month"],
            y=filtered_sales["mom_revenue_growth_pct"],
            name="MoM Growth %",
            mode="lines+markers",
            line=dict(color="#f59e0b", width=3),
            marker=dict(size=6),
            yaxis="y2",
        )
    )

    fig_sales.update_layout(
        template="plotly_dark",
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(title="Revenue (R$)", side="left", showgrid=True, gridcolor="#334155"),
        yaxis2=dict(title="MoM Growth (%)", side="right", overlaying="y", showgrid=False),
        xaxis=dict(title="Year-Month", tickangle=-45),
        height=380,
    )
    st.plotly_chart(fig_sales, use_container_width=True)

with col_right:
    st.subheader("🏆 Top Product Categories by Revenue")
    fig_cat = px.bar(
        cat_df,
        x="total_revenue",
        y="category_name",
        orientation="h",
        color="total_revenue",
        color_continuous_scale="Viridis",
        labels={"total_revenue": "Revenue (R$)", "category_name": "Category"},
    )
    fig_cat.update_layout(
        template="plotly_dark",
        margin=dict(l=20, r=20, t=30, b=20),
        coloraxis_showscale=False,
        yaxis=dict(autorange="reversed"),
        height=380,
    )
    st.plotly_chart(fig_cat, use_container_width=True)

# Row 3: Navigation Cards
st.write("")
st.subheader("🧭 Deep-Dive Analytical Modules")
n1, n2, n3 = st.columns(3)

with n1:
    st.info("### 🚚 Logistics & Fulfillment")
    st.markdown(
        """
        Analyze corridor shipping delays, interstate vs. intrastate transit times, and carrier SLA compliance across Brazil.
        
        👉 **Select '2 Logistics Performance' in the sidebar.**
        """
    )

with n2:
    st.success("### 🎯 Customer RFM Segmentation")
    st.markdown(
        """
        Explore marketing cohorts (Champions, Loyal Customers, Churned) based on Recency, Frequency, and Monetary spend.
        
        👉 **Select '3 Customer RFM' in the sidebar.**
        """
    )

with n3:
    st.warning("### 🏆 Seller Leaderboard")
    st.markdown(
        """
        Inspect merchant partner GMV rankings, review score distributions, and identify underperforming sellers.
        
        👉 **Select '4 Seller Leaderboard' in the sidebar.**
        """
    )
