import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

from core.data_manager import ensure_dataset_loaded
from core.powerbi_theme import pbi_header, render_kpi_card, apply_plotly_pbi_theme
from core.analytics_engine import (
    evaluate_stockout_risk,
    build_planning_summary,
    DATA_UNAVAILABLE,
    FORECAST_UNAVAILABLE,
)

st.set_page_config(
    page_title="Stockout Risk Engine | Planning Platform",
    page_icon="⚠️",
    layout="wide"
)

df, m = ensure_dataset_loaded()

pbi_header(
    title="Statistical Stockout Risk & Exposure Engine",
    subtitle="Probabilistic Lead-Time Buffer Analytics • Risk Tier Classification • SKU + Warehouse Grain"
)

col_sku = m.get("sku", "SKU")
col_wh = m.get("warehouse", "Warehouse")
col_cat = m.get("category", "Product_Category")
col_date = m.get("date", "Date")
col_sup = m.get("supplier", "Supplier")

st.sidebar.header("🎯 Stockout Risk Filters")
warehouses = ["All"] + sorted(df[col_wh].dropna().unique().tolist()) if col_wh in df.columns else ["All"]
sel_wh = st.sidebar.selectbox("Warehouse Filter", warehouses)
categories = ["All"] + sorted(df[col_cat].dropna().unique().tolist()) if col_cat in df.columns else ["All"]
sel_cat = st.sidebar.selectbox("Category Filter", categories)
suppliers = ["All"] + sorted(df[col_sup].dropna().unique().tolist()) if col_sup in df.columns else ["All"]
sel_sup = st.sidebar.selectbox("Supplier Filter", suppliers)

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

summary = build_planning_summary(work, m, date_col=col_date if col_date in work.columns else None)

risk_list = []
unavailable_count = 0
for _, r in summary.iterrows():
    inv = r.get("Inventory_On_Hand", np.nan)
    # Forecast demand required — never substitute Historical_Demand
    mean_d = r.get("Mean_Forecast_Daily_Demand", np.nan)
    std_d = r.get("Std_Daily_Demand", np.nan)
    lt = r.get("Lead_Time_Days", np.nan)
    ss = r.get("Safety_Stock", np.nan)
    rop = r.get("Reorder_Point", np.nan)

    prob, risk_level = evaluate_stockout_risk(
        inventory_on_hand=inv,
        mean_daily_demand=mean_d,
        std_daily_demand=std_d,
        lead_time_days=lt,
        safety_stock=ss,
        reorder_point=rop,
    )

    if risk_level == DATA_UNAVAILABLE or prob is None:
        unavailable_count += 1
        dos = None
        fct_display = None
    else:
        fct_display = float(mean_d) if pd.notna(mean_d) else None
        dos = round(float(inv) / fct_display, 1) if (fct_display and fct_display > 0 and pd.notna(inv)) else None

    risk_list.append({
        "SKU": r.get("SKU"),
        "Warehouse": r.get("Warehouse"),
        "Supplier": r.get("Supplier"),
        "Category": r.get("Product_Category"),
        "Current_Inventory": int(inv) if pd.notna(inv) else None,
        "Forecast_Demand": round(fct_display, 1) if fct_display is not None else FORECAST_UNAVAILABLE,
        "Safety_Stock": int(ss) if pd.notna(ss) else None,
        "Reorder_Point": int(rop) if pd.notna(rop) else None,
        "Lead_Time_Days": lt if pd.notna(lt) else None,
        "Days_Of_Supply": dos if dos is not None else DATA_UNAVAILABLE,
        "Stockout_Prob_Pct": prob if prob is not None else DATA_UNAVAILABLE,
        "Risk_Level": risk_level,
    })

risk_df = pd.DataFrame(risk_list)
evaluated = risk_df[risk_df["Risk_Level"].isin(["Critical", "High", "Medium", "Low"])]

crit_cnt = (evaluated["Risk_Level"] == "Critical").sum()
high_cnt = (evaluated["Risk_Level"] == "High").sum()
med_cnt = (evaluated["Risk_Level"] == "Medium").sum()
low_cnt = (evaluated["Risk_Level"] == "Low").sum()

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    render_kpi_card("Critical Risk", f"{crit_cnt:,}", "Inv < 50% SS or P≥35%", "negative" if crit_cnt > 0 else "positive")
with k2:
    render_kpi_card("High Risk", f"{high_cnt:,}", "Below Reorder Point or P≥15%", "warning" if high_cnt > 0 else "positive")
with k3:
    render_kpi_card("Medium Risk", f"{med_cnt:,}", "Approaching ROP", "neutral")
with k4:
    render_kpi_card("Low Risk", f"{low_cnt:,}", "Healthy Buffer", "positive")
with k5:
    render_kpi_card("Excluded / Unavailable", f"{unavailable_count:,}", "Missing required inputs", "neutral")

st.markdown("---")

sel_risk = st.sidebar.multiselect(
    "Risk Tier",
    ["Critical", "High", "Medium", "Low", DATA_UNAVAILABLE],
    default=["Critical", "High"],
)

filtered_risk = risk_df[risk_df["Risk_Level"].isin(sel_risk)]

if evaluated.empty:
    st.info(DATA_UNAVAILABLE)
else:
    col_left, col_right = st.columns([5, 5])

    with col_left:
        fig_bar = px.histogram(
            evaluated, x="Risk_Level", color="Risk_Level",
            title="Stockout Risk Portfolio Distribution",
            color_discrete_map={"Critical": "#D83B01", "High": "#E66C37", "Medium": "#F2C80F", "Low": "#107C41"}
        )
        apply_plotly_pbi_theme(fig_bar)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_right:
        plot_df = evaluated.copy()
        plot_df = plot_df[pd.to_numeric(plot_df["Days_Of_Supply"], errors="coerce").notna()]
        plot_df["Days_Of_Supply"] = pd.to_numeric(plot_df["Days_Of_Supply"], errors="coerce")
        plot_df["Stockout_Prob_Pct"] = pd.to_numeric(plot_df["Stockout_Prob_Pct"], errors="coerce")
        if not plot_df.empty:
            fig_scatter = px.scatter(
                plot_df, x="Days_Of_Supply", y="Stockout_Prob_Pct", color="Risk_Level",
                title="Days of Supply vs. Stockout Probability",
                color_discrete_map={"Critical": "#D83B01", "High": "#E66C37", "Medium": "#F2C80F", "Low": "#107C41"},
                hover_data=["SKU", "Warehouse", "Current_Inventory"]
            )
            apply_plotly_pbi_theme(fig_scatter)
            st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.info(DATA_UNAVAILABLE)

st.subheader("📋 Comprehensive Stockout Risk Ledger (SKU + Warehouse)")
if filtered_risk.empty:
    st.warning("No data available for the selected filters.")
else:
    st.dataframe(filtered_risk, use_container_width=True)
    st.download_button(
        "Download Stockout Risk Ledger CSV",
        filtered_risk.to_csv(index=False).encode("utf-8"),
        file_name="stockout_risk_ledger.csv",
        mime="text/csv"
    )
