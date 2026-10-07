import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd
import numpy as np

from core.data_manager import ensure_dataset_loaded, load_uploaded_csv, load_default_1m_dataset, DEFAULT_COLUMN_MAPPING
from core.powerbi_theme import pbi_header, render_kpi_card
from core.column_mapper import map_columns

st.set_page_config(
    page_title="Data Governance & 1M+ Pipeline | Planning Platform",
    page_icon="🛠️",
    layout="wide"
)

df, m = ensure_dataset_loaded()

record_count = len(df)
scale_note = (
    f"Analyzing {record_count:,}+ demand and inventory records"
    if record_count >= 1_000_000
    else f"Analyzing {record_count:,} demand and inventory records"
)

pbi_header(
    title="Data Governance & 1M+ Data Pipeline Control Center",
    subtitle=f"Enterprise Data Onboarding • Schema Validation • Data Quality • {scale_note}"
)

col_date = m.get("date", "Date")
col_sku = m.get("sku", "SKU")
col_wh = m.get("warehouse", "Warehouse")
col_sup = m.get("supplier", "Supplier")

# DATA SUMMARY KPIS
k1, k2, k3, k4, k5, k6 = st.columns(6)

with k1:
    render_kpi_card("Dataset Row Count", f"{len(df):,}", "In Memory Buffer", "neutral")

with k2:
    missing_cnt = int(df.isnull().sum().sum())
    render_kpi_card("Missing Values", f"{missing_cnt:,}", "Null cell count", "positive" if missing_cnt == 0 else "warning")

with k3:
    dups_cnt = int(df.duplicated().sum())
    render_kpi_card("Duplicate Records", f"{dups_cnt:,}", "Exact row duplicates", "positive" if dups_cnt == 0 else "negative")

with k4:
    sku_cnt = int(df[col_sku].nunique()) if col_sku in df.columns else 0
    render_kpi_card("SKU Count", f"{sku_cnt:,}", "Distinct products", "neutral")

with k5:
    wh_cnt = int(df[col_wh].nunique()) if col_wh in df.columns else 0
    render_kpi_card("Warehouse Count", f"{wh_cnt:,}", "Locations", "neutral")

with k6:
    sup_cnt = int(df[col_sup].nunique()) if col_sup in df.columns else 0
    render_kpi_card("Supplier Count", f"{sup_cnt:,}", "Vendors", "neutral")

# Date coverage
if col_date in df.columns:
    dates = pd.to_datetime(df[col_date], errors="coerce").dropna()
    if not dates.empty:
        st.caption(f"Date coverage: **{dates.min().date()}** → **{dates.max().date()}** ({dates.nunique():,} distinct dates)")
    else:
        st.caption("Date coverage: Data unavailable")

st.markdown("---")

# Required-column validation
required_business_fields = [
    "date", "sku", "warehouse", "quantity", "stock", "lead_time",
    "unit_cost", "safety_stock", "reorder_point", "forecast_demand", "units_sold",
]
validation_rows = []
for key in required_business_fields:
    col_name = m.get(key, DEFAULT_COLUMN_MAPPING.get(key, key))
    present = col_name in df.columns
    non_null = int(df[col_name].notna().sum()) if present else 0
    validation_rows.append({
        "Business Field": key,
        "Mapped Column": col_name,
        "Present": "Yes" if present else "No",
        "Non-Null Rows": non_null if present else 0,
        "Status": "OK" if present and non_null > 0 else ("Missing Column" if not present else "All Null"),
    })
validation_df = pd.DataFrame(validation_rows)
all_ok = (validation_df["Status"] == "OK").all()

st.subheader("Required-Column Validation & Data-Quality Status")
render_kpi_card(
    "Data-Quality Status",
    "PASS" if all_ok else "ATTENTION",
    f"{(validation_df['Status']=='OK').sum()}/{len(validation_df)} required fields available",
    "positive" if all_ok else "warning",
)
st.dataframe(validation_df, use_container_width=True)

st.markdown("---")

t1, t2, t3 = st.tabs(["⚡ 1M+ Dataset Pipeline & Uploader", "🧩 SAP Field Standardisation & Mapping", "🧼 Data Quality Diagnostic"])

with t1:
    st.subheader("Dataset Ingestion & Pipeline Selection")

    col_u1, col_u2 = st.columns(2)

    with col_u1:
        st.markdown("### 📤 Option A: Upload Custom CSV Dataset")
        uploaded_file = st.file_uploader("Upload CSV file (Any schema supported via Column Mapper)", type=["csv"])
        if uploaded_file is not None:
            new_df = load_uploaded_csv(uploaded_file)
            st.session_state["df"] = new_df
            st.session_state["dataset_source"] = f"Uploaded: {uploaded_file.name}"
            st.success(f"Successfully loaded {len(new_df):,} rows × {len(new_df.columns)} columns!")
            st.rerun()

    with col_u2:
        st.markdown("### ⚡ Option B: 1M+ Record Enterprise Dataset")
        st.write(
            "Generates or reloads a synthetic demand & inventory dataset "
            "(demand, inventory, lead times, safety stock, forecast, and ERP-aligned fields)."
        )
        if st.button("Generate / Reload 1M+ Record Dataset", type="primary"):
            with st.spinner("Processing 1M+ records..."):
                m1_df = load_default_1m_dataset()
                st.session_state["df"] = m1_df
                st.session_state["dataset_source"] = "Enterprise 1M+ Synthetic Dataset"
                st.success(f"Loaded {len(m1_df):,} records into memory!")
                st.rerun()

    st.markdown("---")
    st.subheader("Preview Active Dataset (First 50 Rows)")
    st.dataframe(df.head(50), use_container_width=True)

with t2:
    st.subheader("Map Dataset Columns to SAP / Demand Planning Business Entities")
    st.caption("Conceptual SAP MM/SD/PP-aligned field mapping — not a live SAP connection.")
    mapped_schema = map_columns(df)
    st.json(mapped_schema)

with t3:
    st.subheader("Data Quality & Integrity Assessment")

    null_summary = pd.DataFrame({
        "Column": df.columns,
        "Null Count": df.isnull().sum().values,
        "Null %": np.round((df.isnull().sum().values / max(1, len(df))) * 100.0, 2),
        "Data Type": [str(t) for t in df.dtypes]
    })

    st.dataframe(null_summary, use_container_width=True)
