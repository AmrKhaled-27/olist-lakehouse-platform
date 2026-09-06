import sys
from pathlib import Path

# Ensure repository root is in sys.path
ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import plotly.express as px
from src.dashboard.db import (
    load_customer_rfm_segments,
    load_customer_rfm_sample,
)

st.set_page_config(page_title="Customer RFM Segmentation", page_icon="🎯", layout="wide")

st.title("🎯 Customer Insights & RFM Marketing Segments")
st.markdown("Marketing segmentation based on **Recency** (days since last order), **Frequency** (total orders), and **Monetary** (lifetime spend).")

# Load Data
segments_df = load_customer_rfm_segments()
sample_df = load_customer_rfm_sample(1500)

# Color Map for Segments
color_map = {
    "Champions": "#10b981",
    "Loyal Customers": "#3b82f6",
    "Recent One-Time Buyers": "#f59e0b",
    "Lost / Churned Customers": "#ef4444",
}

# Segment Cards
cols = st.columns(len(segments_df))
for i, row in segments_df.iterrows():
    with cols[i]:
        st.metric(
            label=row["rfm_segment"],
            value=f"{row['customer_count']:,} users",
            delta=f"R$ {row['total_segment_spend']/1e6:.2f}M spend",
        )

st.write("---")

# Visualizations Row 1
c1, c2 = st.columns([1, 1])

with c1:
    st.subheader("Customer Distribution by Marketing Segment")
    fig_pie = px.pie(
        segments_df,
        names="rfm_segment",
        values="customer_count",
        color="rfm_segment",
        color_discrete_map=color_map,
        hole=0.45,
    )
    fig_pie.update_layout(
        template="plotly_dark",
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2),
        height=380,
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with c2:
    st.subheader("Total Revenue Generated per Segment")
    fig_rev = px.bar(
        segments_df,
        x="rfm_segment",
        y="total_segment_spend",
        color="rfm_segment",
        color_discrete_map=color_map,
        text_auto=".2s",
        labels={"rfm_segment": "Segment", "total_segment_spend": "Total Spend (R$)"},
    )
    fig_rev.update_layout(
        template="plotly_dark",
        showlegend=False,
        margin=dict(l=20, r=20, t=30, b=20),
        height=380,
    )
    st.plotly_chart(fig_rev, use_container_width=True)

st.write("---")

# Visualizations Row 2: Scatter Plot
st.subheader("🔬 Recency vs. Total Spend Cluster (Sample)")
fig_scatter = px.scatter(
    sample_df,
    x="recency_days",
    y="monetary_total_spend",
    color="rfm_segment",
    color_discrete_map=color_map,
    size="frequency_orders",
    hover_data=["customer_unique_id", "customer_city", "customer_state"],
    labels={
        "recency_days": "Recency (Days Since Last Order)",
        "monetary_total_spend": "Lifetime Spend (R$)",
        "frequency_orders": "Orders Count",
        "rfm_segment": "Segment",
    },
)
fig_scatter.update_layout(
    template="plotly_dark",
    margin=dict(l=20, r=20, t=30, b=20),
    height=450,
)
st.plotly_chart(fig_scatter, use_container_width=True)

# Table Exploration
st.write("---")
st.subheader("📋 Customer Explorer")
selected_segment = st.selectbox(
    "Filter sample by segment:",
    options=["All"] + segments_df["rfm_segment"].tolist(),
)

filtered_sample = sample_df
if selected_segment != "All":
    filtered_sample = sample_df[sample_df["rfm_segment"] == selected_segment]

st.dataframe(
    filtered_sample.style.format({
        "recency_days": "{:,} days",
        "frequency_orders": "{:,}",
        "monetary_total_spend": "R$ {:,.2f}",
    }),
    use_container_width=True,
    hide_index=True,
)
