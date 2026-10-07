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
from core.analytics_engine import calculate_safety_stock_parameters, DATA_UNAVAILABLE, format_metric

st.set_page_config(
    page_title="Inventory Optimization & Safety Stock | Planning Platform",
    page_icon="📦",
    layout="wide"
)

df, m = ensure_dataset_loaded()

pbi_header(
    title="Inventory Optimization & Safety Stock Simulator",
    subtitle="Service-Level Targets • Reorder Point (ROP) • EOQ • Days of Supply • Working Capital"
)

col_sku = m.get("sku", "SKU")
col_qty = m.get("quantity", "Historical_Demand")
col_fct = m.get("forecast_demand", "Forecast_Demand")
col_cost = m.get("unit_cost", "Unit_Cost")
col_lead = m.get("lead_time", "Lead_Time_Days")
col_stock = m.get("stock", "Inventory_On_Hand")
col_pos = m.get("inventory_position", "Inventory_Position")
col_ss = m.get("safety_stock", "Safety_Stock")
col_rop = m.get("reorder_point", "Reorder_Point")
col_date = m.get("date", "Date")
col_wh = m.get("warehouse", "Warehouse")
col_sl = m.get("service_level", "Service_Level_Target")
col_sold = m.get("units_sold", "Units_Sold")

st.sidebar.header("⚙️ Safety Stock & Policy Controls")

skus = sorted(df[col_sku].dropna().astype(str).unique())
selected_sku = st.sidebar.selectbox("Select Target SKU", skus, index=0)

warehouses = sorted(df[col_wh].dropna().unique().tolist()) if col_wh in df.columns else []
selected_wh = st.sidebar.selectbox("Warehouse / Location", warehouses) if warehouses else None

target_sl = st.sidebar.select_slider(
    "Target Service Level (%)",
    options=[0.90, 0.95, 0.98, 0.99],
    value=0.95,
    format_func=lambda x: f"{int(x*100)}%"
)

order_cost = st.sidebar.number_input("Ordering Cost ($/order)", min_value=10.0, max_value=2000.0, value=250.0, step=25.0)
holding_pct = st.sidebar.slider("Annual Carrying Cost (%)", 0.05, 0.40, 0.20, step=0.01)

sku_data = df[df[col_sku].astype(str) == selected_sku].copy()
if selected_wh is not None and col_wh in sku_data.columns:
    sku_data = sku_data[sku_data[col_wh] == selected_wh]

if sku_data.empty:
    st.warning("No data available for the selected filters.")
    st.stop()

sku_data[col_date] = pd.to_datetime(sku_data[col_date], errors="coerce")
sku_data = sku_data.sort_values(col_date)
latest = sku_data.iloc[-1]

mean_demand = float(sku_data[col_qty].mean()) if col_qty in sku_data.columns else None
std_demand = float(sku_data[col_qty].std()) if col_qty in sku_data.columns and len(sku_data) > 1 else None
lead_time = float(latest[col_lead]) if col_lead in sku_data.columns and pd.notna(latest[col_lead]) else None
unit_cost = float(latest[col_cost]) if col_cost in sku_data.columns and pd.notna(latest[col_cost]) else None
current_stock = float(latest[col_stock]) if col_stock in sku_data.columns and pd.notna(latest[col_stock]) else None
current_pos = float(latest[col_pos]) if col_pos in sku_data.columns and pd.notna(latest.get(col_pos)) else current_stock
dataset_ss = float(latest[col_ss]) if col_ss in sku_data.columns and pd.notna(latest[col_ss]) else None
dataset_rop = float(latest[col_rop]) if col_rop in sku_data.columns and pd.notna(latest[col_rop]) else None

# Lead-time variability from observed Lead_Time_Days at this grain (no invented default)
if col_lead in sku_data.columns and sku_data[col_lead].nunique() > 1:
    lead_time_std = float(sku_data[col_lead].std())
else:
    lead_time_std = 0.0

params = None
if all(v is not None for v in [mean_demand, std_demand, lead_time, unit_cost]):
    params = calculate_safety_stock_parameters(
        mean_daily_demand=mean_demand,
        std_daily_demand=std_demand,
        lead_time_days=lead_time,
        lead_time_std=lead_time_std,
        service_level=target_sl,
        unit_cost=unit_cost,
        holding_cost_pct=holding_pct,
        order_cost=order_cost
    )

# Prefer dataset Safety_Stock / Reorder_Point when present
display_ss = dataset_ss if dataset_ss is not None else (params["Safety_Stock"] if params else None)
display_rop = dataset_rop if dataset_rop is not None else (params["Reorder_Point"] if params else None)
ltd = (mean_demand * lead_time) if (mean_demand is not None and lead_time is not None) else None

# Days of Supply using forecast when available
has_fct = col_fct in sku_data.columns and sku_data[col_fct].notna().any()
fct_daily = float(sku_data[col_fct].mean()) if has_fct else None
if current_stock is not None and fct_daily and fct_daily > 0:
    dos = current_stock / fct_daily
    dos_str = f"{dos:.1f} Days"
elif current_stock is not None and mean_demand and mean_demand > 0:
    dos = current_stock / mean_demand
    dos_str = f"{dos:.1f} Days (hist. demand basis)"
else:
    dos_str = DATA_UNAVAILABLE

inv_value = (current_stock * unit_cost) if (current_stock is not None and unit_cost is not None) else None

k1, k2, k3, k4, k5, k6 = st.columns(6)

with k1:
    render_kpi_card(
        "Safety Stock",
        f"{int(display_ss):,} Units" if display_ss is not None else DATA_UNAVAILABLE,
        "Dataset value" if dataset_ss is not None else ("Calculated" if params else DATA_UNAVAILABLE),
        "neutral",
    )
with k2:
    render_kpi_card(
        "Reorder Point",
        f"{int(display_rop):,} Units" if display_rop is not None else DATA_UNAVAILABLE,
        f"Lead-Time Demand: {int(ltd)}" if ltd is not None else DATA_UNAVAILABLE,
        "warning",
    )
with k3:
    render_kpi_card(
        "EOQ",
        f"{int(params['EOQ']):,} Units" if params else DATA_UNAVAILABLE,
        f"Annual Demand: {int(mean_demand*365):,}" if mean_demand is not None else DATA_UNAVAILABLE,
        "positive",
    )
with k4:
    render_kpi_card(
        "Inventory On Hand",
        f"{int(current_stock):,} Units" if current_stock is not None else DATA_UNAVAILABLE,
        f"Position: {int(current_pos):,}" if current_pos is not None else "In Warehouse",
        "positive" if (current_stock is not None and display_rop is not None and current_stock >= display_rop) else "negative",
    )
with k5:
    render_kpi_card("Days of Supply", dos_str, "Inv / Daily Demand", "neutral")
with k6:
    render_kpi_card(
        "Inventory Value",
        f"${inv_value:,.0f}" if inv_value is not None else DATA_UNAVAILABLE,
        f"Lead Time: {lead_time:.0f}d" if lead_time is not None else DATA_UNAVAILABLE,
        "neutral",
    )

st.markdown("---")

t1, t2, t3 = st.tabs([
    "📉 Service Level Trade-Off Curves",
    "📊 Historical Inventory Trajectory & Buffer Trend",
    "📐 Transparent Formulas & Policy Calculation"
])

with t1:
    st.subheader("Service Level Target vs. Capital Investment & Stockout Exposure")
    if params is None:
        st.info(DATA_UNAVAILABLE)
    else:
        sl_scenarios = [0.85, 0.90, 0.92, 0.95, 0.97, 0.98, 0.99, 0.995]
        scenario_res = []
        for sl in sl_scenarios:
            res = calculate_safety_stock_parameters(
                mean_daily_demand=mean_demand,
                std_daily_demand=std_demand,
                lead_time_days=lead_time,
                lead_time_std=lead_time_std,
                service_level=sl,
                unit_cost=unit_cost,
                holding_cost_pct=holding_pct,
                order_cost=order_cost
            )
            if res is None:
                continue
            scenario_res.append({
                "Service_Level_Pct": int(sl * 100),
                "Safety_Stock_Units": res["Safety_Stock"],
                "Buffer_Capital_Value": res["Safety_Stock_Value"],
                "Stockout_Risk_Pct": round((1.0 - sl) * 100.0, 1)
            })

        scen_df = pd.DataFrame(scenario_res)
        fig_tradeoff = go.Figure()
        fig_tradeoff.add_trace(go.Scatter(
            x=scen_df["Service_Level_Pct"], y=scen_df["Buffer_Capital_Value"],
            name="Safety Stock Capital ($)", line=dict(color="#118DFF", width=3)
        ))
        fig_tradeoff.add_trace(go.Scatter(
            x=scen_df["Service_Level_Pct"], y=scen_df["Stockout_Risk_Pct"],
            name="Stockout Exposure (%)", yaxis="y2", line=dict(color="#D83B01", width=3, dash="dash")
        ))
        fig_tradeoff.update_layout(
            title="Cost Curve of Higher Target Service Levels",
            xaxis_title="Target Service Level (%)",
            yaxis=dict(title=dict(text="Buffer Investment ($)", font=dict(color="#118DFF"))),
            yaxis2=dict(title=dict(text="Stockout Risk (%)", font=dict(color="#D83B01")), overlaying="y", side="right")
        )
        apply_plotly_pbi_theme(fig_tradeoff)
        st.plotly_chart(fig_tradeoff, use_container_width=True)

with t2:
    location_label = selected_wh or "All"
    st.subheader(f"Historical Inventory On-Hand — {selected_sku} @ {location_label}")

    fig_inv_trend = go.Figure()
    fig_inv_trend.add_trace(go.Scatter(
        x=sku_data[col_date], y=sku_data[col_stock],
        name="Inventory On Hand", line=dict(color="#118DFF", width=2)
    ))
    if display_rop is not None:
        fig_inv_trend.add_trace(go.Scatter(
            x=[sku_data[col_date].min(), sku_data[col_date].max()],
            y=[display_rop, display_rop],
            name="Reorder Point (ROP)", line=dict(color="#E66C37", width=2, dash="dash")
        ))
    if display_ss is not None:
        fig_inv_trend.add_trace(go.Scatter(
            x=[sku_data[col_date].min(), sku_data[col_date].max()],
            y=[display_ss, display_ss],
            name="Safety Stock (SS Buffer)", line=dict(color="#D83B01", width=2, dash="dot")
        ))
    fig_inv_trend.update_layout(
        title="Historical Stock Level vs. Policy Thresholds",
        xaxis_title="Date", yaxis_title="Units"
    )
    apply_plotly_pbi_theme(fig_inv_trend)
    st.plotly_chart(fig_inv_trend, use_container_width=True)

with t3:
    st.subheader("Mathematical Documentation of Optimization Formulas")

    st.latex(r"Safety\ Stock\ (SS) = Z \times \sqrt{L \cdot \sigma_D^2 + D^2 \cdot \sigma_L^2}")
    st.latex(r"Reorder\ Point\ (ROP) = (D \times L) + SS")
    st.latex(r"Economic\ Order\ Quantity\ (EOQ) = \sqrt{\frac{2 \cdot D_{annual} \cdot S}{H}}")

    if params:
        st.markdown(
            f"""
            - **$Z$ (Service Factor)** = {params['Z_Score']} (for {int(target_sl*100)}% target service level).
            - **$D$ (Mean Daily Demand)** = {mean_demand:.2f} units/day.
            - **$\\sigma_D$ (Demand StdDev)** = {std_demand:.2f}.
            - **$L$ (Lead Time)** = {lead_time:.1f} days (from dataset).
            - **$\\sigma_L$ (Lead Time StdDev)** = {lead_time_std:.2f} days (observed; 0 if constant).
            - **$S$ (Order Fixed Cost)** = ${order_cost:.2f}/order.
            - **$H$ (Annual Unit Carrying Cost)** = ${unit_cost * holding_pct:.2f}/unit/year.
            - Dataset `Safety_Stock` / `Reorder_Point` are preferred for display when present; simulator values are calculated from the formulas above.
            """
        )
    else:
        st.info(DATA_UNAVAILABLE)
