USE DemandPlanningWarehouse;
GO

CREATE INDEX IX_StgDemand_Date
ON stg.DemandInventoryRaw([Date]);

CREATE INDEX IX_StgDemand_SKU_Warehouse
ON stg.DemandInventoryRaw(SKU, Warehouse);

CREATE INDEX IX_StgDemand_Supplier
ON stg.DemandInventoryRaw(Supplier);

CREATE INDEX IX_StgDemand_Inventory
ON stg.DemandInventoryRaw(Inventory_On_Hand, Safety_Stock, Reorder_Point);
GO
