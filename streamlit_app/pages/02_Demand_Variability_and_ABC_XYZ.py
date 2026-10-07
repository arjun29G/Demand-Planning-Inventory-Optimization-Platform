import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

from core.data_manager import ensure_dataset_loaded
from core.powerbi_theme import pbi_header, render_kpi_card, apply_plotly_pbi_theme
from core.analytics_engine import analyze_demand_variability

st.set_page_config(
    page_title="Demand Variability & ABC-XYZ Analysis | Planning Platform",
    page_icon="📊",
    layout="wide"
)

df, m = ensure_dataset_loaded()

pbi_header(
    title="Demand Variability & ABC-XYZ Segmentation",
    subtitle="SKU + Warehouse Portfolio Segmentation • Coefficient of Variation (CV) • Planning Prioritization"
)

col_sku = m.get("sku", "SKU")
col_qty = m.get("quantity", "Historical_Demand")
col_rev = m.get("revenue", "Revenue")
col_cat = m.get("category", "Product_Category")
col_wh = m.get("warehouse", "Warehouse")

st.sidebar.header("🎛️ Portfolio Filters")
warehouses = ["All Warehouses"] + sorted(df[col_wh].dropna().unique().tolist()) if col_wh in df.columns else ["All Warehouses"]
selected_wh = st.sidebar.selectbox("Warehouse", warehouses)
categories = ["All Categories"] + sorted(df[col_cat].dropna().unique().tolist()) if col_cat in df.columns else ["All Categories"]
selected_cat = st.sidebar.selectbox("Category", categories)

work = df.copy()
if selected_wh != "All Warehouses" and col_wh in work.columns:
    work = work[work[col_wh] == selected_wh]
if selected_cat != "All Categories" and col_cat in work.columns:
    work = work[work[col_cat] == selected_cat]

if work.empty:
    st.warning("No data available for the selected filters.")
    st.stop()

# ABC-XYZ at SKU + Warehouse planning grain
var_df = analyze_demand_variability(
    work,
    sku_col=col_sku,
    qty_col=col_qty,
    rev_col=col_rev if col_rev in work.columns else None,
    warehouse_col=col_wh if col_wh in work.columns else None,
)

total_items = len(var_df)
x_count = (var_df["XYZ_Class"].str.startswith("X")).sum()
y_count = (var_df["XYZ_Class"].str.startswith("Y")).sum()
z_count = (var_df["XYZ_Class"].str.startswith("Z")).sum()

a_count = (var_df["ABC_Class"].str.startswith("A")).sum()
b_count = (var_df["ABC_Class"].str.startswith("B")).sum()
c_count = (var_df["ABC_Class"].str.startswith("C")).sum()

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    render_kpi_card("Planning Items", f"{total_items:,}", "SKU + Warehouse grain", "neutral")
with k2:
    render_kpi_card("Class A (High Value)", f"{a_count:,}", f"{(a_count/max(1,total_items))*100:.1f}% Portfolio", "positive")
with k3:
    render_kpi_card("Class X (Stable Demand)", f"{x_count:,}", "CV < 0.20", "positive")
with k4:
    render_kpi_card("Class Y (Medium Volatility)", f"{y_count:,}", "CV 0.20 - 0.50", "warning")
with k5:
    render_kpi_card("Class Z (High Volatility)", f"{z_count:,}", "CV > 0.50", "negative")

# Reconciliation: XYZ / ABC counts must equal planning items
xyz_total = int(x_count + y_count + z_count)
abc_total = int(a_count + b_count + c_count)
cv_median = float(var_df["CV"].median()) if "CV" in var_df.columns and not var_df.empty else None
st.caption(
    f"Reconciliation: X+Y+Z = **{xyz_total:,}** · A+B+C = **{abc_total:,}** · Planning items = **{total_items:,}**. "
    f"CV = StdDev / Mean Demand at SKU + Warehouse. "
    f"Thresholds: X (CV < 0.20), Y (0.20–0.50), Z (CV > 0.50). "
    + (
        f"Median CV ≈ {cv_median:.3f} — a Y-heavy portfolio is expected when most items fall in that CV band "
        f"(thresholds are not adjusted to force balance)."
        if cv_median is not None
        else ""
    )
)

st.markdown("---")

t1, t2 = st.tabs(["🧩 ABC-XYZ 9-Box Matrix", "📋 SKU + Warehouse Classification Table"])

with t1:
    st.subheader("ABC-XYZ Demand & Revenue Matrix")

    matrix_df = pd.crosstab(var_df["ABC_Class"], var_df["XYZ_Class"])
    matrix_sum = int(matrix_df.values.sum()) if not matrix_df.empty else 0

    fig_matrix = px.imshow(
        matrix_df.values,
        x=matrix_df.columns,
        y=matrix_df.index,
        labels=dict(x="XYZ (Demand Variability)", y="ABC (Business / Revenue Contribution)", color="Item Count"),
        color_continuous_scale="Viridis",
        text_auto=True
    )
    fig_matrix.update_layout(title="ABC-XYZ 9-Box Grid (AX–CZ)")
    apply_plotly_pbi_theme(fig_matrix)
    st.plotly_chart(fig_matrix, use_container_width=True)
    st.caption(f"9-box matrix total = **{matrix_sum:,}** (must equal planning items **{total_items:,}**).")

    st.info(
        "💡 **Strategy Guide:**\n"
        "- **A-X**: Predictable high-value — lean inventory, high service-level target, automated replenishment.\n"
        "- **A-Z**: Volatile high-value — elevated stockout / capital risk; collaborative forecasting & buffers.\n"
        "- **C-Z**: Low-value volatile — reorder-point automation or make-to-order policies."
    )

with t2:
    st.subheader("Detailed Portfolio Segmentation Table")

    selected_abc = st.multiselect(
        "Filter ABC Class",
        options=sorted(var_df["ABC_Class"].unique()),
        default=list(var_df["ABC_Class"].unique()),
    )
    selected_xyz = st.multiselect(
        "Filter XYZ Class",
        options=sorted(var_df["XYZ_Class"].unique()),
        default=list(var_df["XYZ_Class"].unique()),
    )

    filtered_var = var_df[
        (var_df["ABC_Class"].isin(selected_abc))
        & (var_df["XYZ_Class"].isin(selected_xyz))
    ]

    st.dataframe(filtered_var, use_container_width=True)

    st.download_button(
        "Download ABC-XYZ Segmentation CSV",
        filtered_var.to_csv(index=False).encode("utf-8"),
        file_name="abc_xyz_demand_variability.csv",
        mime="text/csv"
    )
