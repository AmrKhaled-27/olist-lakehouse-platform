import sys
from pathlib import Path

# Ensure repository root is in sys.path
ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from src.dashboard.db import (
    load_monthly_sales,
    load_payment_distribution,
    load_top_categories,
)

st.set_page_config(page_title="Executive Sales Overview", page_icon="📊", layout="wide")

st.title("📊 Executive Sales & Financial Performance")
st.markdown("Detailed monthly financial breakdowns, payment financing patterns, and category revenue drivers.")

# Load Data
sales_df = load_monthly_sales()
pay_df = load_payment_distribution()
cat_df = load_top_categories(15)

# Date Filter
years = sorted(sales_df["purchase_year"].dropna().unique().tolist())
selected_years = st.multiselect("Filter by Year:", options=years, default=years)

filtered_sales = sales_df[sales_df["purchase_year"].isin(selected_years)].copy()

st.write("")

# Section 1: Revenue & Order Volume Breakdown
col1, col2 = st.columns([3, 2])

with col1:
    st.subheader("Monthly Revenue Breakdown: Items vs. Freight")
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=filtered_sales["year_month"],
        y=filtered_sales["total_item_revenue"],
        name="Item Revenue (R$)",
        marker_color="#38bdf8"
    ))
    fig.add_trace(go.Bar(
        x=filtered_sales["year_month"],
        y=filtered_sales["total_freight_revenue"],
        name="Freight Revenue (R$)",
        marker_color="#818cf8"
    ))
    fig.update_layout(
        barmode="stack",
        template="plotly_dark",
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(title="Year-Month", tickangle=-45),
        yaxis=dict(title="Revenue (R$)"),
        height=380,
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Average Order Value (AOV) Trend")
    fig_aov = px.line(
        filtered_sales,
        x="year_month",
        y="average_order_value",
        markers=True,
        labels={"year_month": "Year-Month", "average_order_value": "AOV (R$)"},
    )
    fig_aov.update_traces(line_color="#10b981", line_width=3, marker_size=6)
    fig_aov.update_layout(
        template="plotly_dark",
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis=dict(tickangle=-45),
        height=380,
    )
    st.plotly_chart(fig_aov, use_container_width=True)

st.write("---")

# Section 2: Payments & Financing Methods
st.subheader("💳 Payment Methods & Financing Behavior")
p1, p2 = st.columns([1, 1])

with p1:
    fig_pay = px.pie(
        pay_df,
        values="total_payment_value",
        names="payment_type",
        hole=0.45,
        color_discrete_sequence=px.colors.qualitative.Pastel,
        title="Revenue Share by Payment Method",
    )
    fig_pay.update_layout(
        template="plotly_dark",
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2),
        height=360,
    )
    st.plotly_chart(fig_pay, use_container_width=True)

with p2:
    fig_inst = px.bar(
        pay_df,
        x="payment_type",
        y="avg_installments",
        text_auto=True,
        color="payment_type",
        title="Average Financing Installments by Payment Method",
        labels={"payment_type": "Payment Method", "avg_installments": "Avg Installments"},
    )
    fig_inst.update_layout(
        template="plotly_dark",
        showlegend=False,
        margin=dict(l=20, r=20, t=40, b=20),
        height=360,
    )
    st.plotly_chart(fig_inst, use_container_width=True)

st.write("---")

# Section 3: Monthly Scorecard Table
st.subheader("📋 Monthly Performance Scorecard Table")
display_sales = filtered_sales[[
    "year_month",
    "total_orders",
    "unique_customers",
    "total_gross_revenue",
    "total_item_revenue",
    "total_freight_revenue",
    "average_order_value",
    "mom_revenue_growth_pct"
]].copy()

display_sales.columns = [
    "Year-Month",
    "Orders",
    "Unique Buyers",
    "Gross GMV (R$)",
    "Item Revenue (R$)",
    "Freight (R$)",
    "AOV (R$)",
    "MoM Growth (%)"
]

st.dataframe(
    display_sales.style.format({
        "Orders": "{:,}",
        "Unique Buyers": "{:,}",
        "Gross GMV (R$)": "R$ {:,.2f}",
        "Item Revenue (R$)": "R$ {:,.2f}",
        "Freight (R$)": "R$ {:,.2f}",
        "AOV (R$)": "R$ {:,.2f}",
        "MoM Growth (%)": "{:+.2f}%"
    }),
    use_container_width=True,
    hide_index=True,
)
