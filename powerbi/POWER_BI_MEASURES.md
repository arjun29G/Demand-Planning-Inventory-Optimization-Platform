# Power BI DAX Measures

These measures are intended for a Power BI semantic model aligned to the synthetic demand-planning dataset.

```DAX
Total Demand = SUM('FactDemand'[Historical_Demand])
Total Forecast Demand = SUM('FactDemand'[Forecast_Demand])
Total Units Sold = SUM('FactDemand'[Units_Sold])
Total Inventory = SUM('FactInventory'[Inventory_On_Hand])
Average Inventory = AVERAGE('FactInventory'[Inventory_On_Hand])
Inventory Value = SUMX('FactInventory', 'FactInventory'[Inventory_On_Hand] * RELATED('DimProduct'[Unit_Cost]))
Revenue = SUM('FactDemand'[Revenue])
Total Order Quantity = SUM('FactReplenishment'[Order_Quantity])
Average Lead Time = AVERAGE('FactInventory'[Lead_Time_Days])
Average Safety Stock = AVERAGE('FactInventory'[Safety_Stock])
Average Reorder Point = AVERAGE('FactInventory'[Reorder_Point])
Forecast Variance = SUM('FactDemand'[Forecast_Variance])
Forecast Variance % = DIVIDE([Forecast Variance], [Total Demand])
Forecast Accuracy = 1 - DIVIDE(ABS([Forecast Variance]), [Total Forecast Demand])
MAPE = AVERAGEX('FactDemand', ABS(DIVIDE('FactDemand'[Forecast_Error], 'FactDemand'[Historical_Demand])))
WAPE = DIVIDE(SUMX('FactDemand', ABS('FactDemand'[Forecast_Error])), SUM('FactDemand'[Historical_Demand]))
Forecast Bias = DIVIDE(SUM('FactDemand'[Forecast_Error]), SUM('FactDemand'[Historical_Demand]))
Stockout Events = SUM('FactInventory'[Stockout_Events])
Stockout Rate = DIVIDE([Stockout Events], [Total Demand])
Days of Supply = AVERAGE('FactInventory'[Days_of_Supply])
Inventory Turnover = DIVIDE([Total Units Sold], [Average Inventory])
Safety Stock Gap = SUM('FactInventory'[Safety_Stock_Gap])
Reorder Exception Count = CALCULATE(COUNTA('FactReplenishment'[Reorder_Exception]), 'FactReplenishment'[Reorder_Exception] = "Reorder Required")
Shortage Risk SKU Count = DISTINCTCOUNT('FactInventory'[SKU])
Replenishment Priority Count = COUNTROWS(FILTER('FactReplenishment', 'FactReplenishment'[Replenishment_Priority] <> "Low"))
```

## Important Note

The project intentionally does not create a misleading true Fill Rate measure if fulfilled quantity is not available. When a proxy is used, it must be labeled as a service-level proxy or fulfillment proxy, not as actual fill rate.

## Supporting Proxy

```DAX
Service Level Proxy = DIVIDE([Total Units Sold], [Total Demand], 0)
```

This is a proxy only and should be explicitly labeled as a service-level proxy in the dashboard. It is not a true fill-rate measure.
