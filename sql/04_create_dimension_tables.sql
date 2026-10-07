USE DemandPlanningWarehouse;
GO

IF OBJECT_ID('dw.DimDate', 'U') IS NULL
BEGIN
    CREATE TABLE dw.DimDate (
        DateKey DATE NOT NULL PRIMARY KEY,
        DateValue DATE NOT NULL,
        YearNumber INT NOT NULL,
        MonthNumber INT NOT NULL,
        MonthName NVARCHAR(20) NOT NULL,
        DayNumber INT NOT NULL,
        FiscalPeriod NVARCHAR(50) NULL
    );
END;
GO

IF OBJECT_ID('dw.DimProduct', 'U') IS NULL
BEGIN
    CREATE TABLE dw.DimProduct (
        SKU NVARCHAR(100) NOT NULL PRIMARY KEY,
        Product_Name NVARCHAR(250) NULL,
        Product_Category NVARCHAR(150) NULL,
        Product_Subcategory NVARCHAR(150) NULL,
        Unit_Cost DECIMAL(18,4) NULL,
        Selling_Price DECIMAL(18,4) NULL
    );
END;
GO

IF OBJECT_ID('dw.DimLocation', 'U') IS NULL
BEGIN
    CREATE TABLE dw.DimLocation (
        Warehouse NVARCHAR(150) NOT NULL PRIMARY KEY,
        Region NVARCHAR(150) NULL,
        LocationType NVARCHAR(50) NULL
    );
END;
GO

IF OBJECT_ID('dw.DimSupplier', 'U') IS NULL
BEGIN
    CREATE TABLE dw.DimSupplier (
        Supplier NVARCHAR(150) NOT NULL PRIMARY KEY,
        Supplier_Name NVARCHAR(250) NULL,
        Supplier_Region NVARCHAR(150) NULL
    );
END;
GO
