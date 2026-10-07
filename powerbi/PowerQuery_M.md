# Power Query M Transformations

This file contains Microsoft Power Query M examples for standardizing the synthetic demand-planning dataset before it is loaded into the Power BI semantic model.

```powerquery
let
    Source = Csv.Document(File.Contents("C:\\path\\to\\pharmaceutical_demand_1m.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(
        PromotedHeaders,
        {
            {"Date", type date},
            {"SKU", type text},
            {"Product_Name", type text},
            {"Product_Category", type text},
            {"Product_Subcategory", type text},
            {"Warehouse", type text},
            {"Region", type text},
            {"Supplier", type text},
            {"Historical_Demand", type number},
            {"Units_Sold", type number},
            {"Order_Quantity", type number},
            {"Inventory_On_Hand", type number},
            {"Inventory_Position", type number},
            {"Lead_Time_Days", type number},
            {"Unit_Cost", type number},
            {"Selling_Price", type number},
            {"Revenue", type number},
            {"Safety_Stock", type number},
            {"Reorder_Point", type number},
            {"Service_Level_Target", type number},
            {"Stockout_Events", type number},
            {"Forecast_Demand", type number},
            {"Forecast_Lower_Bound", type number},
            {"Forecast_Upper_Bound", type number},
            {"Seasonality_Index", type number},
            {"Demand_Variability", type number},
            {"Forecast_Error", type number},
            {"Forecast_Accuracy", type number}
        }
    ),
    Cleaned = Table.TransformColumns(
        Typed,
        {
            {"SKU", each Text.Trim(_), type text},
            {"Warehouse", each Text.Trim(_), type text},
            {"Supplier", each Text.Trim(_), type text},
            {"Product_Name", each if _ = null then "Unknown" else _}
        }
    ),
    NullHandled = Table.ReplaceValue(Cleaned, null, 0, Replacer.ReplaceValue, {"Historical_Demand", "Units_Sold", "Order_Quantity", "Inventory_On_Hand", "Safety_Stock", "Reorder_Point", "Forecast_Demand", "Forecast_Error"}),
    ForecastVariance = Table.AddColumn(NullHandled, "Forecast_Variance", each [Forecast_Demand] - [Historical_Demand], type number),
    SafetyStockGap = Table.AddColumn(ForecastVariance, "Safety_Stock_Gap", each [Inventory_On_Hand] - [Safety_Stock], type number),
    ReorderException = Table.AddColumn(SafetyStockGap, "Reorder_Exception", each if [Inventory_Position] <= [Reorder_Point] then "Reorder Required" else "No Reorder", type text),
    ReplenishmentPriority = Table.AddColumn(ReorderException, "Replenishment_Priority", each if [Inventory_On_Hand] < [Safety_Stock] then "Critical" else if [Inventory_Position] <= [Reorder_Point] then "High" else "Low", type text),
    InventoryStatus = Table.AddColumn(ReplenishmentPriority, "Inventory_Status", each if [Inventory_On_Hand] < [Safety_Stock] then "Shortage Risk" else "Within Target", type text)
in
    InventoryStatus
```

## Transformation Purpose

- confirm column names and field types
- remove obvious nulls and normalize strings
- compute forecast variance
- compute safety stock gap
- generate reorder and replenishment flags
- prepare the data for a star-schema semantic model
