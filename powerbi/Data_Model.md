# Power BI Data Model Summary

This project models the Power BI semantic layer around the same synthetic planning facts used in the Python and SQL layers.

- DimDate: date and period keys
- DimProduct: SKU, product, category, subcategory
- DimLocation: warehouse, region
- DimSupplier: supplier information
- FactDemand: demand, forecast, variance, seasonality, accuracy
- FactInventory: stock, safety stock, reorder point, days of supply
- FactForecast: forecast details and prediction intervals
- FactReplenishment: order quantity, replenishment priority, reorder exception
- FactStockout: stockout risk and shortage-prone flag

The design follows a standard star-schema pattern optimized for planner interaction and high-level supply-chain reporting.
