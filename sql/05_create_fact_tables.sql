USE DemandPlanningWarehouse;
GO

IF OBJECT_ID('dw.FactDemand', 'U') IS NULL
BEGIN
    CREATE TABLE dw.FactDemand (
        DateKey DATE NOT NULL,
        SKU NVARCHAR(100) NOT NULL,
        Warehouse NVARCHAR(150) NOT NULL,
        Historical_Demand DECIMAL(18,2) NULL,
        Units_Sold DECIMAL(18,2) NULL,
        Forecast_Demand DECIMAL(18,2) NULL,
        Forecast_Error DECIMAL(18,2) NULL,
        Forecast_Variance DECIMAL(18,2) NULL,
        Demand_Variability DECIMAL(18,4) NULL,
        Seasonality_Index DECIMAL(18,4) NULL,
        Forecast_Accuracy DECIMAL(18,4) NULL,
        CONSTRAINT PK_FactDemand PRIMARY KEY (DateKey, SKU, Warehouse)
    );
END;
GO

IF OBJECT_ID('dw.FactInventory', 'U') IS NULL
BEGIN
    CREATE TABLE dw.FactInventory (
        DateKey DATE NOT NULL,
        SKU NVARCHAR(100) NOT NULL,
        Warehouse NVARCHAR(150) NOT NULL,
        Inventory_On_Hand DECIMAL(18,2) NULL,
        Inventory_Position DECIMAL(18,2) NULL,
        Safety_Stock DECIMAL(18,2) NULL,
        Reorder_Point DECIMAL(18,2) NULL,
        Lead_Time_Days DECIMAL(18,2) NULL,
        Service_Level_Target DECIMAL(18,4) NULL,
        Stockout_Events DECIMAL(18,2) NULL,
        Days_of_Supply DECIMAL(18,2) NULL,
        CONSTRAINT PK_FactInventory PRIMARY KEY (DateKey, SKU, Warehouse)
    );
END;
GO

IF OBJECT_ID('dw.FactForecast', 'U') IS NULL
BEGIN
    CREATE TABLE dw.FactForecast (
        DateKey DATE NOT NULL,
        SKU NVARCHAR(100) NOT NULL,
        Warehouse NVARCHAR(150) NOT NULL,
        Forecast_Demand DECIMAL(18,2) NULL,
        Forecast_Lower_Bound DECIMAL(18,2) NULL,
        Forecast_Upper_Bound DECIMAL(18,2) NULL,
        Forecast_Error DECIMAL(18,2) NULL,
        Forecast_Accuracy DECIMAL(18,4) NULL,
        Forecast_Variance DECIMAL(18,2) NULL,
        CONSTRAINT PK_FactForecast PRIMARY KEY (DateKey, SKU, Warehouse)
    );
END;
GO

IF OBJECT_ID('dw.FactReplenishment', 'U') IS NULL
BEGIN
    CREATE TABLE dw.FactReplenishment (
        DateKey DATE NOT NULL,
        SKU NVARCHAR(100) NOT NULL,
        Warehouse NVARCHAR(150) NOT NULL,
        Supplier NVARCHAR(150) NULL,
        Order_Quantity DECIMAL(18,2) NULL,
        Inventory_On_Hand DECIMAL(18,2) NULL,
        Inventory_Position DECIMAL(18,2) NULL,
        Safety_Stock DECIMAL(18,2) NULL,
        Reorder_Point DECIMAL(18,2) NULL,
        Replenishment_Priority NVARCHAR(50) NULL,
        Safety_Stock_Gap DECIMAL(18,2) NULL,
        Reorder_Exception NVARCHAR(50) NULL,
        CONSTRAINT PK_FactReplenishment PRIMARY KEY (DateKey, SKU, Warehouse)
    );
END;
GO

IF OBJECT_ID('dw.FactStockout', 'U') IS NULL
BEGIN
    CREATE TABLE dw.FactStockout (
        DateKey DATE NOT NULL,
        SKU NVARCHAR(100) NOT NULL,
        Warehouse NVARCHAR(150) NOT NULL,
        Stockout_Events DECIMAL(18,2) NULL,
        Stockout_Risk_Tier NVARCHAR(50) NULL,
        Shortage_Risk_SKU BIT NULL,
        CONSTRAINT PK_FactStockout PRIMARY KEY (DateKey, SKU, Warehouse)
    );
END;
GO
