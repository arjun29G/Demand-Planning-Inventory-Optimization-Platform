import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from core.data_manager import ensure_dataset_loaded
from core.powerbi_theme import pbi_header, render_kpi_card, apply_plotly_pbi_theme
from core.analytics_engine import (
    calculate_forecast_metrics,
    evaluate_stockout_risk,
    build_planning_summary,
    calculate_inventory_turnover,
    DATA_UNAVAILABLE,
    FORECAST_UNAVAILABLE,
)

# =========================================================
# PAGE CONFIGURATION
# =========================================================
st.set_page_config(
    page_title="Demand Planning & Inventory Optimization Platform",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize dataset & mappings
df, m = ensure_dataset_loaded()

record_count = len(df)
if record_count >= 1_000_000:
    scale_caption = f"Analyzing {record_count:,}+ demand and inventory records"
else:
    scale_caption = f"Analyzing {record_count:,} demand and inventory records"

pbi_header(
    title="Demand Planning & Inventory Optimization Platform",
    subtitle=f"Executive Demand Planning & Inventory Optimization Control Tower • {scale_caption}"
)

st.caption(
    "Power BI-style interactive planning dashboard built with Python, Streamlit and Plotly. "
    "SAP MM/SD/PP-aligned planning analytics (not a live SAP system connection)."
)

# =========================================================
# GLOBAL FILTER SIDEBAR
# =========================================================
st.sidebar.header("🎛️ Executive S&OP Filters")

source_name = st.session_state.get("dataset_source", "Active Dataset")
st.sidebar.caption(f"📁 Source: **{source_name}** ({len(df):,} records)")

col_date = m.get("date", "Date")
col_sku = m.get("sku", "SKU")
col_cat = m.get("category", "Product_Category")
col_wh = m.get("warehouse", "Warehouse")
col_sup = m.get("supplier", "Supplier")

col_qty = m.get("quantity", "Historical_Demand")
col_fct = m.get("forecast_demand", "Forecast_Demand")
col_stock = m.get("stock", "Inventory_On_Hand")
col_pos = m.get("inventory_position", "Inventory_Position")
col_cost = m.get("unit_cost", "Unit_Cost")
col_ss = m.get("safety_stock", "Safety_Stock")
col_rop = m.get("reorder_point", "Reorder_Point")
col_lead = m.get("lead_time", "Lead_Time_Days")
col_sold = m.get("units_sold", "Units_Sold")
col_stockout = m.get("stockout_events", "Stockout_Events")
col_sl = m.get("service_level", "Service_Level_Target")

has_valid_dates = False
if col_date in df.columns:
    df[col_date] = pd.to_datetime(df[col_date], errors="coerce")
    valid_dates_series = df[col_date].dropna()
    if not valid_dates_series.empty:
        has_valid_dates = True
        min_date = valid_dates_series.min().date()
        max_date = valid_dates_series.max().date()
        selected_dates = st.sidebar.date_input(
            "Date Range", [min_date, max_date], min_value=min_date, max_value=max_date
        )
    else:
        st.sidebar.warning("Date data unavailable in dataset")
        selected_dates = []
else:
    st.sidebar.warning("Date column unavailable in dataset")
    selected_dates = []

warehouses = ["All Warehouses"] + sorted(df[col_wh].dropna().unique().tolist()) if col_wh in df.columns else ["All Warehouses"]
selected_wh = st.sidebar.selectbox("Warehouse / Plant", warehouses)

categories = ["All Categories"] + sorted(df[col_cat].dropna().unique().tolist()) if col_cat in df.columns else ["All Categories"]
selected_cat = st.sidebar.selectbox("Product Category", categories)

suppliers = ["All Suppliers"] + sorted(df[col_sup].dropna().unique().tolist()) if col_sup in df.columns else ["All Suppliers"]
selected_sup = st.sidebar.selectbox("Supplier", suppliers)

# Filter application
filtered_df = df.copy()

if has_valid_dates and len(selected_dates) == 2:
    filtered_df = filtered_df[
        (filtered_df[col_date].dt.date >= selected_dates[0])
        & (filtered_df[col_date].dt.date <= selected_dates[1])
    ]

if selected_wh != "All Warehouses" and col_wh in filtered_df.columns:
    filtered_df = filtered_df[filtered_df[col_wh] == selected_wh]

if selected_cat != "All Categories" and col_cat in filtered_df.columns:
    filtered_df = filtered_df[filtered_df[col_cat] == selected_cat]

if selected_sup != "All Suppliers" and col_sup in filtered_df.columns:
    filtered_df = filtered_df[filtered_df[col_sup] == selected_sup]

if filtered_df.empty:
    st.warning("No data available for the selected filters.")
    st.stop()

# =========================================================
# AGGREGATED METRICS (SKU + Warehouse planning grain)
# =========================================================
total_skus = filtered_df[col_sku].nunique() if col_sku in filtered_df.columns else 0

# 1. Forecast Accuracy — only when Forecast_Demand exists (no Historical fallback)
if col_qty in filtered_df.columns and col_fct in filtered_df.columns:
    valid_mask = filtered_df[col_qty].notnull() & filtered_df[col_fct].notnull()
    if valid_mask.any():
        forecast_metrics = calculate_forecast_metrics(
            filtered_df.loc[valid_mask, col_qty].values,
            filtered_df.loc[valid_mask, col_fct].values
        )
        if forecast_metrics["Accuracy"] is not None:
            forecast_acc_val = forecast_metrics["Accuracy"]
            wape_val = forecast_metrics["WAPE"]
            forecast_acc_str = f"{forecast_acc_val:.1f}%"
            wape_str = f"WAPE: {wape_val:.1f}%"
            acc_status = "positive" if forecast_acc_val >= 90 else "warning"
        else:
            forecast_acc_str = FORECAST_UNAVAILABLE
            wape_str = FORECAST_UNAVAILABLE
            acc_status = "neutral"
    else:
        forecast_acc_str = FORECAST_UNAVAILABLE
        wape_str = FORECAST_UNAVAILABLE
        acc_status = "neutral"
else:
    forecast_acc_str = FORECAST_UNAVAILABLE
    wape_str = FORECAST_UNAVAILABLE
    acc_status = "neutral"

# 2. SKU + Warehouse master aggregation
sku_summary = build_planning_summary(
    filtered_df,
    col_map=m,
    date_col=col_date if has_valid_dates else None,
)

# Stockout Risk — exclude rows missing required inputs (no arbitrary defaults)
risk_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
unavailable_risk = 0
if not sku_summary.empty:
    risk_tiers = []
    stockout_probs = []
    for _, r in sku_summary.iterrows():
        inv = r.get("Inventory_On_Hand", np.nan)
        # Prefer forecast demand; do NOT fall back to historical as forecast
        mean_d = r.get("Mean_Forecast_Daily_Demand", np.nan)
        std_d = r.get("Std_Daily_Demand", np.nan)
        lt = r.get("Lead_Time_Days", np.nan)
        ss = r.get("Safety_Stock", np.nan)
        rop = r.get("Reorder_Point", np.nan)

        prob, tier = evaluate_stockout_risk(
            inventory_on_hand=inv,
            mean_daily_demand=mean_d,
            std_daily_demand=std_d,
            lead_time_days=lt,
            safety_stock=ss,
            reorder_point=rop,
        )
        risk_tiers.append(tier)
        stockout_probs.append(prob if prob is not None else np.nan)
        if tier in risk_counts:
            risk_counts[tier] += 1
        else:
            unavailable_risk += 1

    sku_summary["Risk_Level"] = risk_tiers
    sku_summary["Stockout_Prob_Pct"] = stockout_probs

high_risk_skus = risk_counts["Critical"] + risk_counts["High"]
evaluated_locations = sum(risk_counts.values())
stockout_pct = (high_risk_skus / max(1, evaluated_locations)) * 100.0 if evaluated_locations > 0 else 0.0
risk_kpi_value = f"{high_risk_skus:,}" if evaluated_locations > 0 else DATA_UNAVAILABLE
risk_kpi_sub = (
    f"{stockout_pct:.1f}% of evaluated SKU-Warehouse locations"
    if evaluated_locations > 0
    else DATA_UNAVAILABLE
)

# 3. Days of Supply = Available Inventory / Forecast Daily Demand
if (
    not sku_summary.empty
    and "Inventory_On_Hand" in sku_summary.columns
    and "Mean_Forecast_Daily_Demand" in sku_summary.columns
):
    valid_dos = sku_summary["Mean_Forecast_Daily_Demand"].notna() & (sku_summary["Mean_Forecast_Daily_Demand"] > 0)
    if valid_dos.any():
        total_available_inv = sku_summary.loc[valid_dos, "Inventory_On_Hand"].sum()
        total_fct_daily_demand = sku_summary.loc[valid_dos, "Mean_Forecast_Daily_Demand"].sum()
        days_of_supply_val = total_available_inv / total_fct_daily_demand
        days_of_supply_str = f"{days_of_supply_val:.1f} Days"
        dos_status = "positive" if 20 <= days_of_supply_val <= 45 else "warning"
        dos_sub = "Available Inv / Forecast Daily Demand"
    else:
        days_of_supply_str = FORECAST_UNAVAILABLE
        dos_status = "neutral"
        dos_sub = FORECAST_UNAVAILABLE
else:
    days_of_supply_str = FORECAST_UNAVAILABLE
    dos_status = "neutral"
    dos_sub = FORECAST_UNAVAILABLE

# 4. Inventory Turnover = Annualized COGS / Average Inventory Value
#    COGS = Units_Sold × Unit_Cost (actual sales — not Historical_Demand proxy)
date_days = None
if has_valid_dates and col_date in filtered_df.columns:
    date_days = max(1, (filtered_df[col_date].max() - filtered_df[col_date].min()).days + 1)

if (
    col_sold in filtered_df.columns
    and col_cost in filtered_df.columns
    and col_stock in filtered_df.columns
):
    inv_turnover_val = calculate_inventory_turnover(
        df=filtered_df,
        sold_col=col_sold,
        cost_col=col_cost,
        stock_col=col_stock,
        date_col=col_date if has_valid_dates else None,
        sku_col=col_sku,
        warehouse_col=col_wh if col_wh in filtered_df.columns else None,
        date_span_days=date_days,
    )
    if inv_turnover_val is not None:
        inv_turnover_str = f"{inv_turnover_val:.2f}x"
        turnover_sub = "Annualized COGS (Units Sold × Cost) / Avg Inv Value"
        turnover_status = "positive" if inv_turnover_val >= 4.0 else "neutral"
    else:
        inv_turnover_str = DATA_UNAVAILABLE
        turnover_sub = "COGS / Avg Inv"
        turnover_status = "neutral"
else:
    inv_turnover_str = DATA_UNAVAILABLE
    turnover_sub = "Requires Units_Sold, Unit_Cost, Inventory_On_Hand"
    turnover_status = "neutral"

# 5. Service Level Proxy = Units Sold / Historical Demand
# (Not a true order fill rate — dataset has no customer-order / backorder lines.)
target_sl_str = DATA_UNAVAILABLE
if col_sl in filtered_df.columns and filtered_df[col_sl].notna().any():
    sl_raw = float(filtered_df[col_sl].mean())
    # Dataset stores fractions (e.g. 0.95) or percentages
    target_sl_pct = sl_raw * 100.0 if sl_raw <= 1.0 else sl_raw
    target_sl_str = f"{target_sl_pct:.1f}%"

if col_sold in filtered_df.columns and col_qty in filtered_df.columns:
    sold_units = filtered_df[col_sold].sum()
    total_dem = filtered_df[col_qty].sum()
    if total_dem > 0:
        service_level_proxy_val = (sold_units / total_dem) * 100.0
        service_level_proxy_str = f"{service_level_proxy_val:.1f}%"
        service_level_proxy_sub = f"Service Level Proxy = Units Sold / Historical Demand • Target SL: {target_sl_str}"
        sla_status = "positive" if service_level_proxy_val >= 95 else "warning"
    else:
        service_level_proxy_str = DATA_UNAVAILABLE
        service_level_proxy_sub = "Service Level Proxy"
        sla_status = "neutral"
else:
    service_level_proxy_str = DATA_UNAVAILABLE
    service_level_proxy_sub = "Requires Units_Sold and Historical_Demand"
    sla_status = "neutral"

# 6. Safety Stock & Excess Capital (sum across SKU+Warehouse locations)
if (
    not sku_summary.empty
    and "Safety_Stock" in sku_summary.columns
    and "Unit_Cost" in sku_summary.columns
    and "Inventory_On_Hand" in sku_summary.columns
):
    valid_ss = sku_summary["Safety_Stock"].notna() & sku_summary["Unit_Cost"].notna()
    if valid_ss.any():
        total_ss_val = (sku_summary.loc[valid_ss, "Safety_Stock"] * sku_summary.loc[valid_ss, "Unit_Cost"]).sum()
        ss_val_str = f"${total_ss_val:,.0f}"
    else:
        ss_val_str = DATA_UNAVAILABLE

    # Excess = stock above (ROP + SS) only when both policy values exist — never SS * 2
    if "Reorder_Point" in sku_summary.columns:
        policy_ok = (
            sku_summary["Reorder_Point"].notna()
            & sku_summary["Safety_Stock"].notna()
            & sku_summary["Unit_Cost"].notna()
        )
        if policy_ok.any():
            max_policy_buffer = (
                sku_summary.loc[policy_ok, "Reorder_Point"]
                + sku_summary.loc[policy_ok, "Safety_Stock"]
            )
            excess_units = np.maximum(
                0,
                sku_summary.loc[policy_ok, "Inventory_On_Hand"] - max_policy_buffer
            )
            excess_inv_val = (excess_units * sku_summary.loc[policy_ok, "Unit_Cost"]).sum()
            excess_val_str = f"${excess_inv_val:,.0f}"
            excess_status = "negative" if excess_inv_val > 100000 else "positive"
        else:
            excess_val_str = DATA_UNAVAILABLE
            excess_status = "neutral"
    else:
        excess_val_str = DATA_UNAVAILABLE
        excess_status = "neutral"
else:
    ss_val_str = DATA_UNAVAILABLE
    excess_val_str = DATA_UNAVAILABLE
    excess_status = "neutral"

# =========================================================
# EXECUTIVE KPI STRIP (8 CARDS IN 2 ROWS)
# =========================================================
kpi_r1_c1, kpi_r1_c2, kpi_r1_c3, kpi_r1_c4 = st.columns(4)

with kpi_r1_c1:
    render_kpi_card("Total SKUs", f"{total_skus:,}", f"{len(filtered_df):,} Filtered Records", "neutral")

with kpi_r1_c2:
    render_kpi_card("Forecast Accuracy", forecast_acc_str, wape_str, acc_status)

with kpi_r1_c3:
    render_kpi_card("Inventory Turnover", inv_turnover_str, turnover_sub, turnover_status)

with kpi_r1_c4:
    render_kpi_card("Avg Days of Supply", days_of_supply_str, dos_sub, dos_status)

kpi_r2_c1, kpi_r2_c2, kpi_r2_c3, kpi_r2_c4 = st.columns(4)

with kpi_r2_c1:
    render_kpi_card(
        "Stockout Risk SKUs",
        risk_kpi_value,
        risk_kpi_sub,
        "negative" if high_risk_skus > 0 else ("positive" if evaluated_locations > 0 else "neutral"),
    )

with kpi_r2_c2:
    render_kpi_card("Service Level Proxy", service_level_proxy_str, service_level_proxy_sub, sla_status)

with kpi_r2_c3:
    render_kpi_card("Safety Stock Capital", ss_val_str, "Buffer Capital Invested (SKU+Warehouse)", "neutral")

with kpi_r2_c4:
    render_kpi_card("Excess Inventory Capital", excess_val_str, "Stock Above ROP + Safety Stock", excess_status)

st.markdown("---")

# =========================================================
# CHARTS & VISUAL DASHBOARD
# =========================================================
col_left, col_right = st.columns([6, 4])

with col_left:
    st.subheader("📈 Demand Forecast vs Historical Sales Trend")

    if col_date in filtered_df.columns and col_qty in filtered_df.columns and has_valid_dates:
        resample_cols = [col_qty]
        has_forecast = col_fct in filtered_df.columns and filtered_df[col_fct].notna().any()
        if has_forecast:
            resample_cols.append(col_fct)

        ts_agg = (
            filtered_df.set_index(col_date)
            .resample("ME")[resample_cols]
            .sum()
            .reset_index()
        )

        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=ts_agg[col_date], y=ts_agg[col_qty],
            name="Historical Demand", line=dict(color="#118DFF", width=3)
        ))
        if has_forecast:
            fig_trend.add_trace(go.Scatter(
                x=ts_agg[col_date], y=ts_agg[col_fct],
                name="Forecast Demand", line=dict(color="#E66C37", width=2, dash="dash")
            ))
        else:
            st.caption(FORECAST_UNAVAILABLE)
        fig_trend.update_layout(
            title="Aggregated Monthly Demand Signal & Forecast Trajectory",
            xaxis_title="Date", yaxis_title="Units"
        )
        apply_plotly_pbi_theme(fig_trend)
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("Time-series demand data unavailable for plotting.")

with col_right:
    st.subheader("⚠️ Stockout Risk & Health Distribution")

    if evaluated_locations > 0:
        risk_df = pd.DataFrame({
            "Risk Tier": ["Critical Risk", "High Risk", "Medium Risk", "Low Risk"],
            "Count": [risk_counts["Critical"], risk_counts["High"], risk_counts["Medium"], risk_counts["Low"]]
        })

        fig_pie = px.pie(
            risk_df, names="Risk Tier", values="Count",
            color="Risk Tier",
            color_discrete_map={
                "Critical Risk": "#D83B01",
                "High Risk": "#E66C37",
                "Medium Risk": "#F2C80F",
                "Low Risk": "#107C41"
            },
            hole=0.4
        )
        fig_pie.update_layout(title="Inventory Health & Exposure Segmentation")
        apply_plotly_pbi_theme(fig_pie)
        st.plotly_chart(fig_pie, use_container_width=True)
        if unavailable_risk > 0:
            st.caption(f"{unavailable_risk:,} SKU-Warehouse locations excluded ({DATA_UNAVAILABLE}).")
    else:
        st.info(DATA_UNAVAILABLE)

st.markdown("---")

# =========================================================
# REPLENISHMENT ACTION PLAN (SKU + Warehouse)
# =========================================================
st.subheader("🚨 Priority S&OP Replenishment Action Items")

if (
    not sku_summary.empty
    and "Inventory_On_Hand" in sku_summary.columns
    and "Reorder_Point" in sku_summary.columns
    and "Safety_Stock" in sku_summary.columns
    and "Mean_Forecast_Daily_Demand" in sku_summary.columns
    and "Lead_Time_Days" in sku_summary.columns
):
    ready = (
        sku_summary["Mean_Forecast_Daily_Demand"].notna()
        & sku_summary["Lead_Time_Days"].notna()
        & sku_summary["Safety_Stock"].notna()
        & sku_summary["Reorder_Point"].notna()
        & sku_summary["Inventory_On_Hand"].notna()
    )
    ready_df = sku_summary[ready].copy()
    if not ready_df.empty:
        pos_ready = (
            ready_df["Inventory_Position"]
            if "Inventory_Position" in ready_df.columns
            else ready_df["Inventory_On_Hand"]
        )
        reorder_mask = (pos_ready <= ready_df["Reorder_Point"]) | (
            ready_df["Inventory_On_Hand"] <= ready_df["Safety_Stock"]
        )
        reorder_candidates = ready_df[reorder_mask].copy()

        if not reorder_candidates.empty:
            fct_daily_demand = reorder_candidates["Mean_Forecast_Daily_Demand"]
            lead_days = reorder_candidates["Lead_Time_Days"]

            # Target Inventory Position = Forecast Daily Demand × Lead Time + Safety Stock
            reorder_candidates["Target_Inventory_Position"] = np.round(
                (fct_daily_demand * lead_days) + reorder_candidates["Safety_Stock"], 1
            )
            cand_pos = (
                reorder_candidates["Inventory_Position"]
                if "Inventory_Position" in reorder_candidates.columns
                else reorder_candidates["Inventory_On_Hand"]
            )
            reorder_candidates["Recommended_Order_Qty"] = np.maximum(
                0, np.round(reorder_candidates["Target_Inventory_Position"] - cand_pos)
            ).astype(int)
            reorder_candidates["Days_Of_Supply"] = np.round(
                reorder_candidates["Inventory_On_Hand"] / np.maximum(fct_daily_demand, 1e-9), 1
            )
            unit_cost_series = (
                reorder_candidates["Unit_Cost"]
                if "Unit_Cost" in reorder_candidates.columns
                else np.nan
            )
            reorder_candidates["Estimated_Order_Value"] = np.round(
                reorder_candidates["Recommended_Order_Qty"] * unit_cost_series, 2
            )
            reorder_candidates["Forecast_Daily_Demand"] = np.round(fct_daily_demand, 2)

            top_actions = reorder_candidates.sort_values("Days_Of_Supply", ascending=True).head(10)
        else:
            top_actions = pd.DataFrame()
    else:
        top_actions = pd.DataFrame()
        st.caption(FORECAST_UNAVAILABLE)
else:
    top_actions = pd.DataFrame()

if not top_actions.empty:
    display_cols = []
    col_map_display = {
        "SKU": "SKU",
        "Warehouse": "Warehouse",
        "Supplier": "Supplier",
        "Product_Category": "Category",
        "Inventory_On_Hand": "Inventory",
        "Forecast_Daily_Demand": "Forecast Demand",
        "Safety_Stock": "Safety Stock",
        "Reorder_Point": "Reorder Point",
        "Lead_Time_Days": "Lead Time",
        "Days_Of_Supply": "Days of Supply",
        "Recommended_Order_Qty": "Recommended Order Quantity",
        "Estimated_Order_Value": "Estimated Order Value ($)",
    }
    for col in col_map_display.keys():
        if col in top_actions.columns:
            display_cols.append(col)

    disp_df = top_actions[display_cols].rename(columns=col_map_display)
    st.dataframe(disp_df, use_container_width=True)
else:
    st.info("No immediate replenishment actions under current filters (or required forecast/policy data unavailable).")

# =========================================================
# SAP MM / SD / PP ENTERPRISE ALIGNMENT (conceptual)
# =========================================================
with st.expander("🏛️ SAP MM / SD / PP-Aligned Planning Analytics", expanded=False):
    st.markdown(
        """
        This platform provides **SAP MM/SD/PP-aligned planning analytics**. It is **not** connected to a live SAP system.

        | Business Function | SAP Module Alignment | Role in this Platform |
        |---|---|---|
        | **Demand Signals** | **SAP SD (Sales & Distribution)** | Historical demand, sales, and service-level proxy analytics. |
        | **Planned Requirements** | **SAP PP (Production Planning)** | Forecast demand and material-availability style planning views. |
        | **Inventory & Buffer Policy** | **SAP MM (Materials Management)** | Inventory position, safety stock, reorder point, replenishment. |
        """
    )
