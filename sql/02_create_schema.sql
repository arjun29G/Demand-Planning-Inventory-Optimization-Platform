USE DemandPlanningWarehouse;
GO

IF SCHEMA_ID('stg') IS NULL
    EXEC('CREATE SCHEMA stg');
GO

IF SCHEMA_ID('dw') IS NULL
    EXEC('CREATE SCHEMA dw');
GO

IF SCHEMA_ID('mart') IS NULL
    EXEC('CREATE SCHEMA mart');
GO
