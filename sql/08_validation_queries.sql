USE DemandPlanningWarehouse;
GO

-- Data quality validation for the staged dataset
SELECT
    COUNT(*) AS Row_Count,
    COUNT(DISTINCT SKU) AS SKU_Count,
    COUNT(DISTINCT Warehouse) AS Warehouse_Count,
    COUNT(DISTINCT Supplier) AS Supplier_Count,
    SUM(CASE WHEN SKU IS NULL THEN 1 ELSE 0 END) AS Null_SKU_Count,
    SUM(CASE WHEN Warehouse IS NULL THEN 1 ELSE 0 END) AS Null_Warehouse_Count,
    SUM(CASE WHEN Supplier IS NULL THEN 1 ELSE 0 END) AS Null_Supplier_Count,
    SUM(CASE WHEN Historical_Demand < 0 THEN 1 ELSE 0 END) AS Negative_Demand_Count,
    SUM(CASE WHEN Inventory_On_Hand < 0 THEN 1 ELSE 0 END) AS Negative_Inventory_Count,
    SUM(CASE WHEN Safety_Stock < 0 THEN 1 ELSE 0 END) AS Negative_Safety_Stock_Count,
    SUM(CASE WHEN Reorder_Point < 0 THEN 1 ELSE 0 END) AS Negative_Reorder_Point_Count
FROM stg.DemandInventoryRaw;
GO

-- Forecast variance check
SELECT
    SUM(Forecast_Demand - Historical_Demand) AS Forecast_Variance_Total,
    AVG(CASE WHEN Historical_Demand <> 0 THEN ((Forecast_Demand - Historical_Demand) / Historical_Demand) * 100 ELSE NULL END) AS Avg_Forecast_Variance_Percent
FROM stg.DemandInventoryRaw;
GO

-- Replenishment exception check
SELECT
    SUM(CASE WHEN Inventory_Position <= Reorder_Point THEN 1 ELSE 0 END) AS Reorder_Exceptions,
    SUM(CASE WHEN Inventory_On_Hand < Safety_Stock THEN 1 ELSE 0 END) AS Safety_Stock_Gaps
FROM stg.DemandInventoryRaw;
GO
