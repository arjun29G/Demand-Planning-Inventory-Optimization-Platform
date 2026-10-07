USE DemandPlanningWarehouse;
GO

CREATE OR ALTER VIEW mart.vw_DemandPlanning AS
SELECT
    CAST([Date] AS DATE) AS DateKey,
    SKU,
    Warehouse,
    Historical_Demand,
    Forecast_Demand,
    CAST(Forecast_Demand - Historical_Demand AS DECIMAL(18,2)) AS Forecast_Variance,
    Demand_Variability,
    Seasonality_Index,
    Forecast_Accuracy
FROM stg.DemandInventoryRaw;
GO

CREATE OR ALTER VIEW mart.vw_InventoryPosition AS
SELECT
    CAST([Date] AS DATE) AS DateKey,
    SKU,
    Warehouse,
    Inventory_On_Hand,
    Inventory_Position,
    Safety_Stock,
    Reorder_Point,
    Lead_Time_Days,
    Service_Level_Target,
    CASE
        WHEN Inventory_On_Hand < Safety_Stock THEN 'Safety Stock Gap'
        ELSE 'Within Target'
    END AS Safety_Stock_Status,
    CASE
        WHEN Inventory_Position <= Reorder_Point THEN 'Reorder Required'
        ELSE 'No Reorder'
    END AS Reorder_Exception
FROM stg.DemandInventoryRaw;
GO

CREATE OR ALTER VIEW mart.vw_SKUInventoryMovement AS
SELECT
    CAST([Date] AS DATE) AS DateKey,
    SKU,
    Product_Name,
    Warehouse,
    Region,
    Supplier,
    Units_Sold,
    Order_Quantity,
    Inventory_On_Hand,
    Inventory_Position,
    Forecast_Demand,
    Safety_Stock,
    Reorder_Point,
    Stockout_Events
FROM stg.DemandInventoryRaw;
GO

CREATE OR ALTER VIEW mart.vw_ForecastVariance AS
SELECT
    CAST([Date] AS DATE) AS DateKey,
    SKU,
    Warehouse,
    Historical_Demand,
    Forecast_Demand,
    Forecast_Demand - Historical_Demand AS Forecast_Variance,
    CASE
        WHEN Historical_Demand = 0 THEN NULL
        ELSE ((Forecast_Demand - Historical_Demand) / Historical_Demand) * 100
    END AS Forecast_Variance_Percent,
    Forecast_Accuracy
FROM stg.DemandInventoryRaw;
GO

CREATE OR ALTER VIEW mart.vw_SafetyStockExceptions AS
SELECT
    CAST([Date] AS DATE) AS DateKey,
    SKU,
    Warehouse,
    Inventory_On_Hand,
    Safety_Stock,
    Inventory_On_Hand - Safety_Stock AS Safety_Stock_Gap,
    CASE
        WHEN Inventory_On_Hand < Safety_Stock THEN 'Safety Stock Gap'
        ELSE 'Within Target'
    END AS Safety_Stock_Status
FROM stg.DemandInventoryRaw;
GO

CREATE OR ALTER VIEW mart.vw_ReorderExceptions AS
SELECT
    CAST([Date] AS DATE) AS DateKey,
    SKU,
    Warehouse,
    Inventory_Position,
    Reorder_Point,
    CASE
        WHEN Inventory_Position <= Reorder_Point THEN 'Reorder Required'
        ELSE 'No Reorder'
    END AS Reorder_Exception,
    CASE
        WHEN Inventory_Position <= Reorder_Point THEN 'High'
        ELSE 'Low'
    END AS Reorder_Severity
FROM stg.DemandInventoryRaw;
GO

CREATE OR ALTER VIEW mart.vw_ReplenishmentPriority AS
SELECT
    CAST([Date] AS DATE) AS DateKey,
    SKU,
    Warehouse,
    Inventory_On_Hand,
    Safety_Stock,
    Reorder_Point,
    Lead_Time_Days,
    Forecast_Demand,
    CASE
        WHEN Inventory_On_Hand <= 0 THEN 'Critical'
        WHEN Inventory_On_Hand < Safety_Stock THEN 'High'
        WHEN Inventory_Position <= Reorder_Point THEN 'Medium'
        ELSE 'Low'
    END AS Replenishment_Priority
FROM stg.DemandInventoryRaw;
GO

CREATE OR ALTER VIEW mart.vw_StockoutRisk AS
SELECT
    CAST([Date] AS DATE) AS DateKey,
    SKU,
    Warehouse,
    Inventory_On_Hand,
    Safety_Stock,
    Reorder_Point,
    Forecast_Demand,
    Stockout_Events,
    CASE
        WHEN Inventory_On_Hand <= 0 OR Stockout_Events > 0 THEN 'Critical'
        WHEN Inventory_On_Hand < Safety_Stock THEN 'High'
        WHEN Inventory_On_Hand < Reorder_Point THEN 'Medium'
        ELSE 'Low'
    END AS Stockout_Risk_Tier
FROM stg.DemandInventoryRaw;
GO

CREATE OR ALTER VIEW mart.vw_PlanningLocationSummary AS
SELECT
    Warehouse,
    Region,
    COUNT(DISTINCT SKU) AS Active_SKUs,
    SUM(Historical_Demand) AS Total_Demand,
    SUM(Inventory_On_Hand) AS Total_Inventory,
    SUM(Safety_Stock) AS Total_Safety_Stock,
    SUM(Reorder_Point) AS Total_Reorder_Point,
    SUM(Stockout_Events) AS Total_Stockout_Events
FROM stg.DemandInventoryRaw
GROUP BY Warehouse, Region;
GO

CREATE OR ALTER VIEW mart.vw_PurchaseOrderPlanning AS
SELECT
    CAST([Date] AS DATE) AS DateKey,
    SKU,
    Warehouse,
    Supplier,
    Order_Quantity,
    Inventory_On_Hand,
    Inventory_Position,
    Lead_Time_Days,
    Safety_Stock,
    Reorder_Point,
    CASE
        WHEN Inventory_Position <= Reorder_Point THEN 'Reorder Required'
        ELSE 'No Reorder'
    END AS Reorder_Flag
FROM stg.DemandInventoryRaw;
GO
