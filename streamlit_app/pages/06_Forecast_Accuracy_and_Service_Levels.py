import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from core.data_manager import ensure_dataset_loaded
from core.powerbi_theme import pbi_header, render_kpi_card, apply_plotly_pbi_theme
from core.analytics_engine import (
    calculate_forecast_metrics,
    format_metric,
    DATA_UNAVAILABLE,
    FORECAST_UNAVAILABLE,
)

st.set_page_config(
    page_title="Forecast Accuracy & Service Levels | Planning Platform",
    page_icon="🎯",
    layout="wide"
)

df, m = ensure_dataset_loaded()

pbi_header(
    title="Forecast Accuracy & Service-Level Governance",
    subtitle="Forecast Error Trends • Target Service Level vs Service Level Proxy • SKU / Location Filters"
)

col_date = m.get("date", "Date")
col_qty = m.get("quantity", "Historical_Demand")
col_fct = m.get("forecast_demand", "Forecast_Demand")
col_stock = m.get("stock", "Inventory_On_Hand")
col_sl = m.get("service_level", "Service_Level_Target")
col_sold = m.get("units_sold", "Units_Sold")
col_wh = m.get("warehouse", "Warehouse")
col_cat = m.get("category", "Product_Category")
col_sup = m.get("supplier", "Supplier")

df[col_date] = pd.to_datetime(df[col_date], errors="coerce")

st.sidebar.header("🎛️ Accuracy Filters")
warehouses = ["All"] + sorted(df[col_wh].dropna().unique().tolist()) if col_wh in df.columns else ["All"]
sel_wh = st.sidebar.selectbox("Warehouse", warehouses)
categories = ["All"] + sorted(df[col_cat].dropna().unique().tolist()) if col_cat in df.columns else ["All"]
sel_cat = st.sidebar.selectbox("Category", categories)
suppliers = ["All"] + sorted(df[col_sup].dropna().unique().tolist()) if col_sup in df.columns else ["All"]
sel_sup = st.sidebar.selectbox("Supplier", suppliers)

work = df.copy()
if sel_wh != "All" and col_wh in work.columns:
    work = work[work[col_wh] == sel_wh]
if sel_cat != "All" and col_cat in work.columns:
    work = work[work[col_cat] == sel_cat]
if sel_sup != "All" and col_sup in work.columns:
    work = work[work[col_sup] == sel_sup]

if work.empty:
    st.warning("No data available for the selected filters.")
    st.stop()

has_forecast = col_fct in work.columns and work[col_fct].notna().any()

if has_forecast and col_qty in work.columns:
    monthly_df = (
        work.set_index(col_date)
        .resample("ME")[[col_qty, col_fct]]
        .sum()
        .reset_index()
    )
    metrics = calculate_forecast_metrics(monthly_df[col_qty].values, monthly_df[col_fct].values)
else:
    monthly_df = pd.DataFrame()
    metrics = {"MAE": None, "RMSE": None, "MAPE": None, "WAPE": None, "Bias": None, "Accuracy": None}

# Service Level Proxy = Units Sold / Historical Demand
# (Not a true customer-order fill rate — no order/backorder lines in dataset.)
if col_sold in work.columns and col_qty in work.columns and work[col_qty].sum() > 0:
    service_level_proxy = round((work[col_sold].sum() / work[col_qty].sum()) * 100.0, 2)
else:
    service_level_proxy = None

# Target Service Level from dataset (planning target — distinct from proxy)
if col_sl in work.columns and work[col_sl].notna().any():
    sl_raw = float(work[col_sl].mean())
    target_sl_avg = round(sl_raw * 100.0, 1) if sl_raw <= 1.0 else round(sl_raw, 1)
else:
    target_sl_avg = None

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    acc = metrics["Accuracy"]
    render_kpi_card(
        "Overall Accuracy",
        format_metric(acc, "%") if has_forecast else FORECAST_UNAVAILABLE,
        "100% − WAPE (dataset Forecast_Demand)",
        "positive" if acc is not None and acc >= 90 else ("warning" if acc is not None else "neutral"),
    )
with k2:
    render_kpi_card(
        "Service Level Proxy",
        format_metric(service_level_proxy, "%") if service_level_proxy is not None else DATA_UNAVAILABLE,
        "Service Level Proxy = Units Sold / Historical Demand",
        "positive" if service_level_proxy is not None and (target_sl_avg is None or service_level_proxy >= target_sl_avg) else "warning",
    )
with k3:
    render_kpi_card(
        "Target Service Level",
        format_metric(target_sl_avg, "%") if target_sl_avg is not None else DATA_UNAVAILABLE,
        "Service_Level_Target (planning)",
        "neutral",
    )
with k4:
    render_kpi_card(
        "WAPE",
        format_metric(metrics["WAPE"], "%") if has_forecast else FORECAST_UNAVAILABLE,
        "Volume-Weighted Error",
        "neutral",
    )
with k5:
    bias = metrics["Bias"]
    render_kpi_card(
        "Forecast Bias",
        format_metric(bias, "%") if has_forecast else FORECAST_UNAVAILABLE,
        "Structural Bias",
        "positive" if bias is not None and abs(bias) < 3 else ("warning" if bias is not None else "neutral"),
    )

st.markdown("---")

t1, t2 = st.tabs(["📉 Forecast Error Trend Over Time", "📊 Target Service Level vs Service Level Proxy"])

with t1:
    if has_forecast and not monthly_df.empty:
        monthly_df["WAPE"] = np.round(
            np.abs(monthly_df[col_fct] - monthly_df[col_qty]) / np.maximum(1, monthly_df[col_qty]) * 100.0, 1
        )
        monthly_df["Accuracy"] = np.clip(100.0 - monthly_df["WAPE"], 0.0, 100.0)

        fig_acc = px.line(
            monthly_df, x=col_date, y="Accuracy",
            title="Monthly Forecast Accuracy % Evolution",
            markers=True,
            line_shape="spline"
        )
        apply_plotly_pbi_theme(fig_acc)
        st.plotly_chart(fig_acc, use_container_width=True)
    else:
        st.info(FORECAST_UNAVAILABLE)

with t2:
    if target_sl_avg is None and service_level_proxy is None:
        st.info(DATA_UNAVAILABLE)
    else:
        rows = []
        if target_sl_avg is not None:
            rows.append({"Metric": "Target Service Level", "Percentage": target_sl_avg})
        if service_level_proxy is not None:
            rows.append({"Metric": "Service Level Proxy", "Percentage": service_level_proxy})
        sla_comp = pd.DataFrame(rows)

        fig_sla = px.bar(
            sla_comp, x="Metric", y="Percentage", color="Metric",
            title="Target Service Level vs Service Level Proxy",
            text_auto=True
        )
        apply_plotly_pbi_theme(fig_sla)
        st.plotly_chart(fig_sla, use_container_width=True)

        st.caption(
            "Service Level Proxy = Units Sold / Historical Demand. "
            "This is a proxy based on available demand and sales data — not a true customer-order fill rate "
            "(order / backorder lines are not in the dataset). "
            "Target Service Level comes from Service_Level_Target and is a planning/policy input."
        )
