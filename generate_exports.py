import pandas as pd

from streamlit_app.core.data_manager import load_default_1m_dataset
from streamlit_app.core.analytics_engine import validate_data_quality


def main():
    df = load_default_1m_dataset()

    quality = validate_data_quality(
        df,
        required_columns=[
            "Date",
            "SKU",
            "Warehouse",
            "Supplier",
            "Historical_Demand",
            "Inventory_On_Hand",
            "Lead_Time_Days",
            "Safety_Stock",
            "Reorder_Point",
        ],
        quantity_columns=[
            "Historical_Demand",
            "Forecast_Demand",
            "Inventory_On_Hand",
            "Safety_Stock",
            "Reorder_Point",
            "Lead_Time_Days",
            "Units_Sold",
            "Order_Quantity",
        ],
        price_columns=["Unit_Cost", "Selling_Price", "Revenue"],
    )
    pd.DataFrame([quality]).to_csv("data_quality_report.csv", index=False)

    summary = df.groupby(["Warehouse", "SKU"], as_index=False).agg(
        Historical_Demand=("Historical_Demand", "sum"),
        Forecast_Demand=("Forecast_Demand", "sum"),
        Units_Sold=("Units_Sold", "sum"),
        Inventory_On_Hand=("Inventory_On_Hand", "mean"),
        Inventory_Position=("Inventory_Position", "mean"),
        Safety_Stock=("Safety_Stock", "mean"),
        Reorder_Point=("Reorder_Point", "mean"),
        Order_Quantity=("Order_Quantity", "sum"),
        Revenue=("Revenue", "sum"),
        Stockout_Events=("Stockout_Events", "sum"),
    )

    forecast = df[["Date", "SKU", "Warehouse", "Historical_Demand", "Forecast_Demand", "Forecast_Error", "Forecast_Accuracy"]].copy().head(20000)
    inventory = df[["SKU", "Warehouse", "Inventory_On_Hand", "Inventory_Position", "Safety_Stock", "Reorder_Point", "Lead_Time_Days"]].copy().head(20000)
    replenishment = df[["SKU", "Warehouse", "Supplier", "Inventory_On_Hand", "Inventory_Position", "Safety_Stock", "Reorder_Point", "Order_Quantity"]].copy().head(20000)
    sku_risk = df[["SKU", "Product_Name", "Product_Category", "Warehouse", "Region", "Supplier", "Inventory_On_Hand", "Safety_Stock", "Reorder_Point", "Stockout_Events"]].copy().head(20000)

    with pd.ExcelWriter("exports/planning_extract.xlsx") as writer:
        summary.head(20000).to_excel(writer, sheet_name="Demand Planning", index=False)
        inventory.to_excel(writer, sheet_name="Inventory", index=False)
        replenishment.to_excel(writer, sheet_name="Replenishment", index=False)
        forecast.to_excel(writer, sheet_name="Forecast Accuracy", index=False)
        sku_risk.to_excel(writer, sheet_name="SKU Risk", index=False)

    print(quality)
    print("xlsx_written=exports/planning_extract.xlsx")


if __name__ == "__main__":
    main()
