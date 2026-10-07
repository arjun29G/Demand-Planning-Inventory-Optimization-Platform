import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd
import numpy as np

from core.data_manager import ensure_dataset_loaded
from core.powerbi_theme import pbi_header, render_kpi_card
from core.analytics_engine import (
    generate_replenishment_recommendation,
    build_planning_summary,
    DATA_UNAVAILABLE,
    FORECAST_UNAVAILABLE,
    format_metric,
)

st.set_page_config(
    page_title="Replenishment Planning | Planning Platform",
    page_icon="🚚",
    layout="wide"
)

df, m = ensure_dataset_loaded()

pbi_header(
    title="Replenishment Planning & Order Recommendation Engine",
    subtitle="SKU + Warehouse Workbench • Target Inventory Position • Recommended Order Quantity"
)

col_date = m.get("date", "Date")
col_wh = m.get("warehouse", "Warehouse")
col_sup = m.get("supplier", "Supplier")
col_cat = m.get("category", "Product_Category")

st.sidebar.header("🎯 Replenishment Filters")
filter_status = st.sidebar.radio("Filter Orders", ["Action Required Only", "All Locations"], index=0)

warehouses = ["All"] + sorted(df[col_wh].dropna().unique().tolist()) if col_wh in df.columns else ["All"]
sel_wh = st.sidebar.selectbox("Warehouse", warehouses)
suppliers = ["All"] + sorted(df[col_sup].dropna().unique().tolist()) if col_sup in df.columns else ["All"]
sel_sup = st.sidebar.selectbox("Supplier", suppliers)
categories = ["All"] + sorted(df[col_cat].dropna().unique().tolist()) if col_cat in df.columns else ["All"]
sel_cat = st.sidebar.selectbox("Category", categories)

work = df.copy()
if sel_wh != "All" and col_wh in work.columns:
    work = work[work[col_wh] == sel_wh]
if sel_sup != "All" and col_sup in work.columns:
    work = work[work[col_sup] == sel_sup]
if sel_cat != "All" and col_cat in work.columns:
    work = work[work[col_cat] == sel_cat]

if work.empty:
    st.warning("No data available for the selected filters.")
    st.stop()

summary = build_planning_summary(work, m, date_col=col_date if col_date in work.columns else None)

reconciled = []
for _, r in summary.iterrows():
    rec = generate_replenishment_recommendation(
        sku=r.get("SKU"),
        inventory_on_hand=r.get("Inventory_On_Hand"),
        inventory_position=r.get("Inventory_Position"),
        reorder_point=r.get("Reorder_Point"),
        lead_time_days=r.get("Lead_Time_Days"),
        forecast_daily_demand=r.get("Mean_Forecast_Daily_Demand"),
        safety_stock=r.get("Safety_Stock"),
        warehouse=r.get("Warehouse"),
        supplier=r.get("Supplier"),
        unit_cost=r.get("Unit_Cost"),
    )
    rec["Category"] = r.get("Product_Category")
    reconciled.append(rec)

rec_df = pd.DataFrame(reconciled)

orders_needed = rec_df[rec_df["Needs_Order"] == True]
total_orders = len(orders_needed)
total_units = int(orders_needed["Recommended_Order_Qty"].fillna(0).sum()) if not orders_needed.empty else 0
total_capital = float(orders_needed["Estimated_Order_Value"].fillna(0).sum()) if not orders_needed.empty else 0.0

# Avg lead time from actual data only
lead_series = rec_df["Lead_Time_Days"].dropna() if "Lead_Time_Days" in rec_df.columns else pd.Series(dtype=float)
avg_lt = float(lead_series.mean()) if not lead_series.empty else None

k1, k2, k3, k4 = st.columns(4)
with k1:
    render_kpi_card(
        "Replenishment Signals",
        f"{total_orders:,}",
        "SKU + Warehouse locations requiring PO",
        "warning" if total_orders > 0 else "positive",
    )
with k2:
    render_kpi_card("Total Recommended Units", f"{total_units:,}", "Units to Order", "neutral")
with k3:
    render_kpi_card("Procurement Capital Needed", f"${total_capital:,.0f}", "Estimated Order Value", "neutral")
with k4:
    render_kpi_card(
        "Avg Lead Time",
        format_metric(avg_lt, " Days", decimals=1) if avg_lt is not None else DATA_UNAVAILABLE,
        "From dataset Lead_Time_Days",
        "positive" if avg_lt is not None else "neutral",
    )

st.caption(
    "Target Inventory Position = Forecast Daily Demand × Lead Time + Safety Stock. "
    "Recommended Order Quantity = MAX(0, Target Inventory Position − Inventory Position). "
    f"Locations without Forecast_Demand are marked **{FORECAST_UNAVAILABLE}** (Historical Demand is never used as a substitute)."
)

st.markdown("---")

display_df = rec_df.copy()
if filter_status == "Action Required Only":
    display_df = display_df[display_df["Needs_Order"] == True]

if display_df.empty:
    st.warning("No data available for the selected filters.")
else:
    show_cols = [
        "SKU", "Warehouse", "Supplier", "Category",
        "Inventory_On_Hand", "Inventory_Position", "Forecast_Daily_Demand",
        "Safety_Stock", "Reorder_Point", "Lead_Time_Days", "Days_Of_Supply",
        "Recommended_Order_Qty", "Estimated_Order_Value",
        "Recommended_Order_Date", "Expected_Stockout_Date", "Status_Note",
    ]
    show_cols = [c for c in show_cols if c in display_df.columns]

    st.subheader("📋 Replenishment Recommendation Workbench")
    st.dataframe(display_df[show_cols], use_container_width=True)

    st.download_button(
        "Export Purchase Orders CSV",
        display_df[show_cols].to_csv(index=False).encode("utf-8"),
        file_name="replenishment_purchase_orders.csv",
        mime="text/csv"
    )
