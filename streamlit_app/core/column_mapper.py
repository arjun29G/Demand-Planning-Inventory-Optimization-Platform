import streamlit as st
import pandas as pd

def map_columns(df: pd.DataFrame) -> dict:
    """
    Renders sidebar controls to map arbitrary user CSV columns to standard 
    Demand Planning & Inventory Optimization business entities.
    """
    st.sidebar.header("🧩 Column Mapping & Schema")
    cols = list(df.columns)
    
    def get_default(keywords, fallback="None"):
        for c in cols:
            if any(k.lower() in c.lower() for k in keywords):
                return c
        return fallback

    mapping = {}
    
    # Required core mappings
    mapping["date"] = st.sidebar.selectbox("📅 Date Column *", cols, index=cols.index(get_default(["date", "time", "created"], cols[0])))
    mapping["sku"] = st.sidebar.selectbox("📦 SKU / Material *", cols, index=cols.index(get_default(["sku", "material", "product_id", "item"], cols[min(1, len(cols)-1)])))
    mapping["quantity"] = st.sidebar.selectbox("🔢 Demand / Sales Qty *", cols, index=cols.index(get_default(["demand", "qty", "quantity", "sales", "units"], cols[min(2, len(cols)-1)])))
    
    with st.sidebar.expander("Additional Metadata Mappings", expanded=False):
        mapping["product_name"] = st.selectbox("Product Name", ["None"] + cols, index=(["None"] + cols).index(get_default(["product_name", "name", "description"])))
        mapping["category"] = st.selectbox("Category", ["None"] + cols, index=(["None"] + cols).index(get_default(["category", "family", "segment"])))
        mapping["subcategory"] = st.selectbox("Subcategory", ["None"] + cols, index=(["None"] + cols).index(get_default(["subcategory", "subcat"])))
        mapping["warehouse"] = st.selectbox("Warehouse", ["None"] + cols, index=(["None"] + cols).index(get_default(["warehouse", "plant", "location", "dc"])))
        mapping["supplier"] = st.selectbox("Supplier", ["None"] + cols, index=(["None"] + cols).index(get_default(["supplier", "vendor"])))
        mapping["stock"] = st.selectbox("Inventory On Hand", ["None"] + cols, index=(["None"] + cols).index(get_default(["stock", "inventory", "on_hand"])))
        mapping["lead_time"] = st.selectbox("Lead Time (Days)", ["None"] + cols, index=(["None"] + cols).index(get_default(["lead_time", "lead"])))
        mapping["unit_cost"] = st.selectbox("Unit Cost", ["None"] + cols, index=(["None"] + cols).index(get_default(["cost", "unit_cost"])))
        mapping["revenue"] = st.selectbox("Revenue", ["None"] + cols, index=(["None"] + cols).index(get_default(["revenue", "sales_value", "amount"])))
        mapping["safety_stock"] = st.selectbox("Safety Stock", ["None"] + cols, index=(["None"] + cols).index(get_default(["safety_stock", "ss"])))
        mapping["reorder_point"] = st.selectbox("Reorder Point", ["None"] + cols, index=(["None"] + cols).index(get_default(["reorder_point", "rop"])))
        mapping["forecast_demand"] = st.selectbox("Forecast Demand", ["None"] + cols, index=(["None"] + cols).index(get_default(["forecast", "forecast_demand"])))

    for k, v in mapping.items():
        if v == "None":
            mapping[k] = None

    st.session_state["column_map"] = mapping
    return mapping
