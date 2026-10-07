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
    forecast_moving_average,
    forecast_weighted_moving_average,
    forecast_exponential_smoothing,
    calculate_forecast_metrics,
    format_metric,
    DATA_UNAVAILABLE,
)

st.set_page_config(
    page_title="Demand Forecasting & Seasonality | Planning Platform",
    page_icon="📈",
    layout="wide"
)

df, m = ensure_dataset_loaded()

pbi_header(
    title="Demand Forecasting & Seasonality Intelligence",
    subtitle="Statistical Forecast Modeling • Multi-Horizon Projections • Seasonality & Accuracy Analytics"
)

col_date = m.get("date", "Date")
col_sku = m.get("sku", "SKU")
col_qty = m.get("quantity", "Historical_Demand")
col_fct = m.get("forecast_demand", "Forecast_Demand")
col_cat = m.get("category", "Product_Category")
col_wh = m.get("warehouse", "Warehouse")

df[col_date] = pd.to_datetime(df[col_date], errors="coerce")

# =========================================================
# SIDEBAR CONTROLS
# =========================================================
st.sidebar.header("🎯 Forecasting Controls")

skus = sorted(df[col_sku].dropna().astype(str).unique())
selected_sku = st.sidebar.selectbox("Select Product / SKU", skus, index=0)

warehouses = ["All Warehouses"] + sorted(df[col_wh].dropna().unique().tolist()) if col_wh in df.columns else ["All Warehouses"]
selected_wh = st.sidebar.selectbox("Warehouse / Location", warehouses)

categories = ["All Categories"] + sorted(df[col_cat].dropna().unique().tolist()) if col_cat in df.columns else ["All Categories"]
selected_cat = st.sidebar.selectbox("Filter Category", categories)

forecast_method = st.sidebar.selectbox(
    "Forecasting Model",
    ["Holt's Exponential Smoothing", "Weighted Moving Average (WMA)", "Simple Moving Average (MA)"]
)

horizon_days = st.sidebar.slider("Forecast Horizon (Days)", 7, 90, 30, step=7)
ma_window = st.sidebar.slider("Moving Average Window (Days)", 3, 30, 7)

# Filter to SKU (+ optional warehouse / category)
sku_df = df[df[col_sku].astype(str) == selected_sku].copy()

if selected_wh != "All Warehouses" and col_wh in sku_df.columns:
    sku_df = sku_df[sku_df[col_wh] == selected_wh]

if selected_cat != "All Categories" and col_cat in df.columns:
    sku_df = sku_df[sku_df[col_cat] == selected_cat]

if sku_df.empty:
    st.warning("No data available for the selected filters.")
    st.stop()

# Observed daily demand (transaction dates only) + calendar-filled series for model continuity
observed_daily = sku_df.groupby(col_date)[col_qty].sum().sort_index()
idx = pd.date_range(observed_daily.index.min(), observed_daily.index.max(), freq="D")
daily_ts = observed_daily.reindex(idx, fill_value=0)

# Dataset forecast series (for variance display — never invent Historical as Forecast)
has_dataset_forecast = col_fct in sku_df.columns and sku_df[col_fct].notna().any()
observed_fct = None
if has_dataset_forecast:
    observed_fct = sku_df.groupby(col_date)[col_fct].sum().sort_index()
    daily_fct = observed_fct.reindex(idx, fill_value=np.nan)

# =========================================================
# FORECAST CALCULATION
# =========================================================
if forecast_method == "Simple Moving Average (MA)":
    forecast_series = forecast_moving_average(daily_ts, window=ma_window, horizon=horizon_days)
elif forecast_method == "Weighted Moving Average (WMA)":
    forecast_series = forecast_weighted_moving_average(daily_ts, weights=[0.5, 0.3, 0.2], horizon=horizon_days)
else:
    forecast_series = forecast_exponential_smoothing(daily_ts, alpha=0.3, beta=0.1, horizon=horizon_days)

# Model backtest: train on calendar series; score on positive-demand test days only
# (calendar-gap zeros from reindexing must not invent extreme MAPE / WAPE)
if len(daily_ts) > horizon_days:
    train_ts = daily_ts[:-horizon_days]
    test_actuals = daily_ts[-horizon_days:]
    if forecast_method == "Simple Moving Average (MA)":
        test_preds = forecast_moving_average(train_ts, window=ma_window, horizon=horizon_days)
    elif forecast_method == "Weighted Moving Average (WMA)":
        test_preds = forecast_weighted_moving_average(train_ts, weights=[0.5, 0.3, 0.2], horizon=horizon_days)
    else:
        test_preds = forecast_exponential_smoothing(train_ts, alpha=0.3, beta=0.1, horizon=horizon_days)

    y_act = np.asarray(test_actuals.values, dtype=float)
    y_hat = np.asarray(test_preds.values[: len(y_act)], dtype=float)
    positive_days = y_act > 0
    if positive_days.any():
        metrics = calculate_forecast_metrics(y_act[positive_days], y_hat[positive_days])
    else:
        metrics = calculate_forecast_metrics(y_act, y_hat)
else:
    metrics = {"MAE": None, "RMSE": None, "MAPE": None, "WAPE": None, "Bias": None, "Accuracy": None}

# Dataset forecast performance: Forecast_Demand vs Historical_Demand on observed dates only
dataset_metrics = None
if has_dataset_forecast and observed_fct is not None:
    aligned = pd.concat(
        [observed_daily.rename("actual"), observed_fct.rename("forecast")],
        axis=1,
    ).dropna()
    if not aligned.empty:
        dataset_metrics = calculate_forecast_metrics(aligned["actual"].values, aligned["forecast"].values)

# =========================================================
# SECTION 1 — MODEL BACKTEST PERFORMANCE
# =========================================================
st.subheader("Model Backtest Performance")
st.caption(
    "Evaluates the selected forecasting model (MA / WMA / Holt) against historical observations "
    "for the selected SKU / warehouse. Scored on positive-demand days in the holdout window."
)

m1, m2, m3, m4, m5, m6 = st.columns(6)

acc = metrics["Accuracy"]
with m1:
    render_kpi_card(
        "Model Forecast Accuracy",
        format_metric(acc, "%"),
        "100% − Model WAPE",
        "positive" if acc is not None and acc >= 85 else ("warning" if acc is not None else "neutral"),
    )
with m2:
    render_kpi_card("Model WAPE", format_metric(metrics["WAPE"], "%"), "Model weighted error", "neutral")
with m3:
    render_kpi_card("Model MAPE", format_metric(metrics["MAPE"], "%"), "Excludes zero-demand days", "neutral")
with m4:
    render_kpi_card("Model MAE", format_metric(metrics["MAE"], decimals=1), "Mean Abs Error", "neutral")
with m5:
    render_kpi_card("Model RMSE", format_metric(metrics["RMSE"], decimals=1), "Root Mean Sq Error", "neutral")
with m6:
    bias = metrics["Bias"]
    render_kpi_card(
        "Model Forecast Bias",
        format_metric(bias, "%"),
        "Over/Under Forecast",
        "positive" if bias is not None and abs(bias) < 5 else ("warning" if bias is not None else "neutral"),
    )

st.markdown("---")

# =========================================================
# SECTION 2 — DATASET FORECAST PERFORMANCE
# =========================================================
st.subheader("Dataset Forecast Performance")
st.caption(
    "Model Backtest Performance evaluates the selected forecasting model against historical observations, "
    "while Dataset Forecast Performance evaluates the Forecast_Demand field already present in the planning dataset."
)

d1, d2, d3 = st.columns(3)
if dataset_metrics and dataset_metrics["Accuracy"] is not None:
    with d1:
        render_kpi_card(
            "Dataset Forecast Accuracy",
            format_metric(dataset_metrics["Accuracy"], "%"),
            "100% − Dataset WAPE",
            "positive" if dataset_metrics["Accuracy"] >= 85 else "warning",
        )
    with d2:
        render_kpi_card(
            "Dataset WAPE",
            format_metric(dataset_metrics["WAPE"], "%"),
            "Forecast_Demand vs Historical_Demand",
            "neutral",
        )
    with d3:
        ds_bias = dataset_metrics["Bias"]
        render_kpi_card(
            "Dataset Forecast Bias",
            format_metric(ds_bias, "%"),
            "Dataset field bias",
            "positive" if ds_bias is not None and abs(ds_bias) < 5 else "warning",
        )
else:
    st.info("Forecast data unavailable in dataset for variance comparison (model projection still shown below).")

st.markdown("---")

# Demand variability summary for selected grain
mean_d = float(daily_ts.mean()) if len(daily_ts) else None
std_d = float(daily_ts.std()) if len(daily_ts) > 1 else None
cv = (std_d / mean_d) if (mean_d and mean_d > 0 and std_d is not None) else None
v1, v2, v3 = st.columns(3)
with v1:
    render_kpi_card("Mean Daily Demand", format_metric(mean_d, decimals=1), "Historical demand", "neutral")
with v2:
    render_kpi_card("Demand Variability (σ)", format_metric(std_d, decimals=1), "Std. deviation", "neutral")
with v3:
    render_kpi_card("Coefficient of Variation", format_metric(cv, decimals=3), "σ / μ", "neutral")

st.markdown("---")

# =========================================================
# FORECAST VISUALIZATION
# =========================================================
t1, t2 = st.tabs(["📈 Time-Series Forecast Plot", "📊 Seasonality & Pattern Analysis"])

with t1:
    fig_fct = go.Figure()

    fig_fct.add_trace(go.Scatter(
        x=daily_ts.index, y=daily_ts.values,
        name="Historical Actual Demand",
        line=dict(color="#118DFF", width=2)
    ))

    if has_dataset_forecast:
        fig_fct.add_trace(go.Scatter(
            x=daily_fct.index, y=daily_fct.values,
            name="Dataset Forecast Demand",
            line=dict(color="#107C41", width=2, dash="dot")
        ))

    fig_fct.add_trace(go.Scatter(
        x=forecast_series.index, y=forecast_series.values,
        name=f"{forecast_method} Projection",
        line=dict(color="#E66C37", width=3, dash="solid")
    ))

    # Use residual RMSE from backtest for CI when available; else omit fabricated bands
    if metrics["RMSE"] is not None and metrics["RMSE"] > 0:
        z_85 = 1.44
        upper_bound = forecast_series.values + z_85 * metrics["RMSE"]
        lower_bound = np.maximum(0, forecast_series.values - z_85 * metrics["RMSE"])
        fig_fct.add_trace(go.Scatter(
            x=list(forecast_series.index) + list(forecast_series.index)[::-1],
            y=list(upper_bound) + list(lower_bound)[::-1],
            fill="toself",
            fillcolor="rgba(230, 108, 55, 0.15)",
            line=dict(color="rgba(255,255,255,0)"),
            name="Approx. 85% Interval (RMSE-based)"
        ))

    location_label = selected_wh if selected_wh != "All Warehouses" else "All Warehouses"
    fig_fct.update_layout(
        title=f"Demand Forecast for {selected_sku} @ {location_label} ({horizon_days}-Day Horizon)",
        xaxis_title="Date", yaxis_title="Units Demanded"
    )
    apply_plotly_pbi_theme(fig_fct)
    st.plotly_chart(fig_fct, use_container_width=True)

with t2:
    st.subheader("📅 Monthly & Day-of-Week Seasonality Decomposition")

    season_df = sku_df.copy()
    season_df["Month"] = season_df[col_date].dt.strftime("%b")
    season_df["Month_Num"] = season_df[col_date].dt.month
    season_df["DayOfWeek"] = season_df[col_date].dt.day_name()

    s_col1, s_col2 = st.columns(2)

    with s_col1:
        monthly_avg = season_df.groupby(["Month_Num", "Month"])[col_qty].mean().reset_index()
        monthly_avg["Seasonality_Index"] = monthly_avg[col_qty] / max(1.0, monthly_avg[col_qty].mean())

        fig_month = px.bar(
            monthly_avg, x="Month", y="Seasonality_Index",
            title="Monthly Seasonality Index (Base = 1.0)",
            color="Seasonality_Index",
            color_continuous_scale="Blues"
        )
        apply_plotly_pbi_theme(fig_month)
        st.plotly_chart(fig_month, use_container_width=True)

    with s_col2:
        dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        dow_avg = season_df.groupby("DayOfWeek")[col_qty].mean().reindex(dow_order).reset_index()

        fig_dow = px.line(
            dow_avg, x="DayOfWeek", y=col_qty,
            title="Average Demand by Day of Week",
            markers=True
        )
        apply_plotly_pbi_theme(fig_dow)
        st.plotly_chart(fig_dow, use_container_width=True)

with st.expander("📖 Comprehensive Guide to Forecast Metrics"):
    st.markdown(
        r"""
        **Two distinct evaluations on this page (do not treat them as the same number):**
        - **Model Backtest Performance**: Selected model (MA / WMA / Holt) vs holdout historical demand.
        - **Dataset Forecast Performance**: `Forecast_Demand` field already in the dataset vs `Historical_Demand`.

        **Metric definitions:**
        - **MAE (Mean Absolute Error)**: Average magnitude of errors in forecast units.
        - **RMSE (Root Mean Squared Error)**: Measures error variance; penalizes larger errors more heavily.
        - **MAPE (Mean Absolute Percentage Error)**: Average percentage deviation relative to positive actuals only (zero-demand days excluded).
        - **WAPE (Weighted Absolute Percentage Error)**: Volume-weighted error percentage ($\sum |Y - \hat{Y}| / \sum Y$).
        - **Forecast Bias**: Systematic over-forecasting (positive) or under-forecasting (negative).
        - **Forecast Accuracy %**: Defined as $100\% - \text{WAPE}$.
        - Supported models: Moving Average, Weighted Moving Average, Holt / Exponential Smoothing.
        - Historical Demand is never used as a silent substitute for Forecast Demand.
        """
    )
