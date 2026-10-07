import os
from typing import Tuple
import pandas as pd
import streamlit as st
from assets.data.generate_dataset import generate_supply_chain_data

DATA_FILE_1M = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "assets", "data", "pharmaceutical_demand_1m.csv"
)

DEFAULT_COLUMN_MAPPING = {
    "date": "Date",
    "sku": "SKU",
    "product_name": "Product_Name",
    "category": "Product_Category",
    "subcategory": "Product_Subcategory",
    "warehouse": "Warehouse",
    "region": "Region",
    "supplier": "Supplier",
    "quantity": "Historical_Demand",
    "units_sold": "Units_Sold",
    "order_qty": "Order_Quantity",
    "stock": "Inventory_On_Hand",
    "inventory_position": "Inventory_Position",
    "lead_time": "Lead_Time_Days",
    "unit_cost": "Unit_Cost",
    "selling_price": "Selling_Price",
    "revenue": "Revenue",
    "safety_stock": "Safety_Stock",
    "reorder_point": "Reorder_Point",
    "service_level": "Service_Level_Target",
    "stockout_events": "Stockout_Events",
    "forecast_demand": "Forecast_Demand",
    "forecast_lower": "Forecast_Lower_Bound",
    "forecast_upper": "Forecast_Upper_Bound",
    "seasonality_index": "Seasonality_Index",
    "demand_cv": "Demand_Variability",
    "forecast_error": "Forecast_Error",
    "forecast_accuracy": "Forecast_Accuracy"
}

def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df

@st.cache_data(show_spinner="Loading 1M+ Supply Chain Dataset...", ttl=3600)
def load_default_1m_dataset() -> pd.DataFrame:
    """Loads the pre-generated 1M record dataset or generates it on demand."""
    if os.path.exists(DATA_FILE_1M):
        df = pd.read_csv(DATA_FILE_1M)
    else:
        df = generate_supply_chain_data(num_records=1000000)
        os.makedirs(os.path.dirname(DATA_FILE_1M), exist_ok=True)
        df.to_csv(DATA_FILE_1M, index=False)
    return clean_columns(df)

@st.cache_data(show_spinner="Processing CSV...", ttl=3600)
def load_uploaded_csv(uploaded_file) -> pd.DataFrame:
    df = pd.read_csv(uploaded_file)
    return clean_columns(df)

def ensure_dataset_loaded() -> Tuple[pd.DataFrame, dict]:
    """
    Ensures a dataset is loaded into st.session_state['df'].
    Defaults to the enterprise 1M record dataset if no CSV is uploaded.
    """
    if "df" not in st.session_state or st.session_state["df"] is None:
        df = load_default_1m_dataset()
        st.session_state["df"] = df
        st.session_state["column_map"] = DEFAULT_COLUMN_MAPPING
        st.session_state["dataset_source"] = "Enterprise 1M+ Synthetic Dataset"
        
    return st.session_state["df"], st.session_state.get("column_map", DEFAULT_COLUMN_MAPPING)
