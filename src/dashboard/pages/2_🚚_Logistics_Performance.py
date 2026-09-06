import sys
from pathlib import Path

# Ensure repository root is in sys.path
ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import plotly.express as px
from src.dashboard.db import load_delivery_performance

st.set_page_config(page_title="Logistics Performance", page_icon="🚚", layout="wide")

st.title("🚚 Logistics & Fulfillment SLA Performance")
st.markdown("Analyze shipping routes, carrier delays, and on-time SLA compliance across Brazilian postal corridors.")

# Load Data
df = load_delivery_performance()

# Sidebar Filters
st.sidebar.subheader("Route Filters")
shipment_types = ["All"] + sorted(df["shipment_type"].unique().tolist())
selected_type = st.sidebar.selectbox("Shipment Type:", options=shipment_types)

origins = ["All"] + sorted(df["origin_seller_state"].unique().tolist())
selected_origin = st.sidebar.selectbox("Origin Seller State:", options=origins)

# Apply Filters
filtered_df = df.copy()
if selected_type != "All":
    filtered_df = filtered_df[filtered_df["shipment_type"] == selected_type]
if selected_origin != "All":
    filtered_df = filtered_df[filtered_df["origin_seller_state"] == selected_origin]

# KPIs
avg_days = filtered_df["avg_actual_delivery_days"].mean()
avg_est_days = filtered_df["avg_estimated_delivery_days"].mean()
avg_sla = filtered_df["on_time_delivery_rate_pct"].mean()
avg_freight = filtered_df["avg_freight_cost"].mean()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Avg Actual Transit Time", f"{avg_days:.1f} days")
k2.metric("Avg Carrier Estimate", f"{avg_est_days:.1f} days", delta=f"{avg_est_days - avg_days:+.1f} days early")
k3.metric("On-Time Delivery Rate", f"{avg_sla:.1f}%")
k4.metric("Avg Shipping Freight", f"R$ {avg_freight:.2f}")

st.write("---")

# Visualizations Row 1
c1, c2 = st.columns([3, 2])

with c1:
    st.subheader("Top Shipping Corridors by Order Volume & Delays")
    top_routes = filtered_df.head(15).copy()
    top_routes["corridor"] = top_routes["origin_seller_state"] + " ➔ " + top_routes["destination_customer_state"]
    
    fig_routes = px.bar(
        top_routes,
        x="corridor",
        y="avg_actual_delivery_days",
        color="on_time_delivery_rate_pct",
        color_continuous_scale="RdYlGn",
        text_auto=".1f",
        labels={
            "corridor": "Shipping Corridor",
            "avg_actual_delivery_days": "Actual Transit (Days)",
            "on_time_delivery_rate_pct": "On-Time %",
        },
    )
    fig_routes.update_layout(
        template="plotly_dark",
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis=dict(tickangle=-45),
        height=400,
    )
    st.plotly_chart(fig_routes, use_container_width=True)

with c2:
    st.subheader("Intrastate vs. Interstate SLA")
    fig_type = px.box(
        df,
        x="shipment_type",
        y="avg_actual_delivery_days",
        color="shipment_type",
        points="all",
        labels={
            "shipment_type": "Shipment Type",
            "avg_actual_delivery_days": "Transit Days",
        },
    )
    fig_type.update_layout(
        template="plotly_dark",
        showlegend=False,
        margin=dict(l=20, r=20, t=30, b=20),
        height=400,
    )
    st.plotly_chart(fig_type, use_container_width=True)

st.write("---")

# Visualizations Row 2: Heatmap Matrix
st.subheader("🗺️ Origin to Destination Delivery Days Matrix")
# Pivot table for origin vs destination
pivot_df = df.pivot_table(
    index="origin_seller_state",
    columns="destination_customer_state",
    values="avg_actual_delivery_days",
    aggfunc="mean",
)

# Filter top states for clear display
top_states = df.groupby("destination_customer_state")["delivered_orders_count"].sum().nlargest(12).index.tolist()
pivot_subset = pivot_df.loc[pivot_df.index.isin(top_states), pivot_df.columns.isin(top_states)]

fig_heat = px.imshow(
    pivot_subset,
    text_auto=".1f",
    color_continuous_scale="Reds",
    labels=dict(x="Destination State (Customer)", y="Origin State (Seller)", color="Avg Days"),
)
fig_heat.update_layout(
    template="plotly_dark",
    margin=dict(l=20, r=20, t=30, b=20),
    height=450,
)
st.plotly_chart(fig_heat, use_container_width=True)

# Table
st.subheader("📋 Route Logistics Detail")
st.dataframe(
    filtered_df.style.format({
        "delivered_orders_count": "{:,}",
        "avg_actual_delivery_days": "{:.2f} days",
        "avg_estimated_delivery_days": "{:.2f} days",
        "on_time_delivery_rate_pct": "{:.2f}%",
        "avg_freight_cost": "R$ {:.2f}",
    }),
    use_container_width=True,
    hide_index=True,
)
