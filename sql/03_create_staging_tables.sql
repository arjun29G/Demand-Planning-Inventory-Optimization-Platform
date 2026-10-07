USE DemandPlanningWarehouse;
GO

IF OBJECT_ID('stg.DemandInventoryRaw', 'U') IS NULL
BEGIN
    CREATE TABLE stg.DemandInventoryRaw (
        [Date] DATE NULL,
        SKU NVARCHAR(100) NULL,
        Product_Name NVARCHAR(250) NULL,
        Product_Category NVARCHAR(150) NULL,
        Product_Subcategory NVARCHAR(150) NULL,
        Warehouse NVARCHAR(150) NULL,
        Region NVARCHAR(150) NULL,
        Supplier NVARCHAR(150) NULL,
        Historical_Demand DECIMAL(18,2) NULL,
        Units_Sold DECIMAL(18,2) NULL,
        Order_Quantity DECIMAL(18,2) NULL,
        Inventory_On_Hand DECIMAL(18,2) NULL,
        Inventory_Position DECIMAL(18,2) NULL,
        Lead_Time_Days DECIMAL(18,2) NULL,
        Unit_Cost DECIMAL(18,4) NULL,
        Selling_Price DECIMAL(18,4) NULL,
        Revenue DECIMAL(18,2) NULL,
        Safety_Stock DECIMAL(18,2) NULL,
        Reorder_Point DECIMAL(18,2) NULL,
        Service_Level_Target DECIMAL(18,4) NULL,
        Stockout_Events DECIMAL(18,2) NULL,
        Forecast_Demand DECIMAL(18,2) NULL,
        Forecast_Lower_Bound DECIMAL(18,2) NULL,
        Forecast_Upper_Bound DECIMAL(18,2) NULL,
        Seasonality_Index DECIMAL(18,4) NULL,
        Demand_Variability DECIMAL(18,4) NULL,
        Forecast_Error DECIMAL(18,2) NULL,
        Forecast_Accuracy DECIMAL(18,4) NULL
    );
END;
GO
