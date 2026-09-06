import sys
from pathlib import Path

# Ensure repository root is in sys.path
ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import plotly.express as px
from src.dashboard.db import (
    load_seller_tiers,
    load_seller_leaderboard,
)

st.set_page_config(page_title="Seller Leaderboard", page_icon="🏆", layout="wide")

st.title("🏆 Merchant Seller Performance & Leaderboard")
st.markdown("Track merchant partner gross sales, fulfillment performance, and identify sellers requiring service interventions.")

# Load Data
tier_df = load_seller_tiers()

# Tiers Metric Row
tier_colors = {
    "Elite Partner": "#10b981",
    "Top Seller": "#3b82f6",
    "Standard Seller": "#64748b",
    "Action Required (Low Ratings)": "#ef4444",
}

t_cols = st.columns(len(tier_df))
for i, row in tier_df.iterrows():
    with t_cols[i]:
        st.metric(
            label=row["seller_tier"],
            value=f"{row['seller_count']:,} sellers",
            delta=f"R$ {row['total_tier_sales']/1e6:.2f}M sales",
        )

st.write("---")

# Visualizations Row
c1, c2 = st.columns([1, 1])

with c1:
    st.subheader("Sales Volume Share by Partner Tier")
    fig_share = px.pie(
        tier_df,
        names="seller_tier",
        values="total_tier_sales",
        color="seller_tier",
        color_discrete_map=tier_colors,
        hole=0.45,
    )
    fig_share.update_layout(
        template="plotly_dark",
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2),
        height=380,
    )
    st.plotly_chart(fig_share, use_container_width=True)

with c2:
    st.subheader("Average Review Score by Seller Tier")
    fig_score = px.bar(
        tier_df,
        x="seller_tier",
        y="avg_tier_review_score",
        color="seller_tier",
        color_discrete_map=tier_colors,
        text_auto=".2f",
        labels={"seller_tier": "Tier", "avg_tier_review_score": "Avg Rating ⭐"},
    )
    fig_score.update_layout(
        template="plotly_dark",
        showlegend=False,
        margin=dict(l=20, r=20, t=30, b=20),
        yaxis=dict(range=[0, 5]),
        height=380,
    )
    st.plotly_chart(fig_score, use_container_width=True)

st.write("---")

# Seller Leaderboard with Search and Filters
st.subheader("📋 Top Merchant Leaderboard")

col_filter1, col_filter2, col_filter3 = st.columns([1, 1, 2])
with col_filter1:
    selected_tier = st.selectbox(
        "Filter by Tier:",
        options=["All"] + tier_df["seller_tier"].tolist(),
    )
with col_filter2:
    min_orders = st.slider("Minimum Orders Fulfilled:", min_value=0, max_value=50, value=5)
with col_filter3:
    search_id = st.text_input("Search Seller ID or City:")

leaderboard_df = load_seller_leaderboard(tier_filter=selected_tier, min_orders=min_orders)

if search_id:
    leaderboard_df = leaderboard_df[
        leaderboard_df["seller_id"].str.contains(search_id, case=False, na=False)
        | leaderboard_df["seller_city"].str.contains(search_id, case=False, na=False)
    ]

# Formatting Table
display_cols = [
    "revenue_rank",
    "seller_id",
    "seller_city",
    "seller_state",
    "seller_tier",
    "total_orders_fulfilled",
    "total_items_sold",
    "total_sales_volume",
    "avg_item_price",
    "avg_review_score",
]

st.dataframe(
    leaderboard_df[display_cols].style.format({
        "revenue_rank": "#{:,}",
        "total_orders_fulfilled": "{:,}",
        "total_items_sold": "{:,}",
        "total_sales_volume": "R$ {:,.2f}",
        "avg_item_price": "R$ {:,.2f}",
        "avg_review_score": "⭐ {:.2f}",
    }),
    use_container_width=True,
    hide_index=True,
)
