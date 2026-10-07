-- SQL analytical model for the synthetic demand-planning dataset.
-- This is designed to support the existing CSV source and feed Power BI.

CREATE TABLE stg_demand (
    date_key DATE NOT NULL,
    sku VARCHAR(50) NOT NULL,
    warehouse VARCHAR(100) NOT NULL,
    supplier VARCHAR(100),
    historical_demand NUMERIC(18,2),
    units_sold NUMERIC(18,2),
    forecast_demand NUMERIC(18,2),
    forecast_error NUMERIC(18,2),
    seasonality_index NUMERIC(18,4),
    demand_variability NUMERIC(18,4),
    PRIMARY KEY (date_key, sku, warehouse)
);

CREATE TABLE stg_inventory (
    date_key DATE NOT NULL,
    sku VARCHAR(50) NOT NULL,
    warehouse VARCHAR(100) NOT NULL,
    inventory_on_hand NUMERIC(18,2),
    inventory_position NUMERIC(18,2),
    safety_stock NUMERIC(18,2),
    reorder_point NUMERIC(18,2),
    lead_time_days NUMERIC(18,2),
    unit_cost NUMERIC(18,4),
    service_level_target NUMERIC(5,4),
    PRIMARY KEY (date_key, sku, warehouse)
);

CREATE TABLE stg_purchase_orders (
    date_key DATE NOT NULL,
    sku VARCHAR(50) NOT NULL,
    warehouse VARCHAR(100) NOT NULL,
    supplier VARCHAR(100),
    order_quantity NUMERIC(18,2),
    unit_cost NUMERIC(18,4),
    revenue NUMERIC(18,2),
    PRIMARY KEY (date_key, sku, warehouse, supplier)
);

CREATE TABLE stg_products (
    sku VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(200),
    product_category VARCHAR(100),
    product_subcategory VARCHAR(100),
    unit_cost NUMERIC(18,4),
    selling_price NUMERIC(18,4)
);

CREATE TABLE stg_locations (
    warehouse VARCHAR(100) PRIMARY KEY,
    region VARCHAR(100)
);

CREATE TABLE stg_suppliers (
    supplier VARCHAR(100) PRIMARY KEY,
    supplier_name VARCHAR(200)
);

CREATE TABLE dim_date (
    date_key DATE PRIMARY KEY,
    year_num INT,
    month_num INT,
    month_name VARCHAR(20),
    day_of_week INT,
    fiscal_week INT
);

CREATE TABLE dim_product (
    sku VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(200),
    product_category VARCHAR(100),
    product_subcategory VARCHAR(100)
);

CREATE TABLE dim_location (
    warehouse VARCHAR(100) PRIMARY KEY,
    region VARCHAR(100)
);

CREATE TABLE dim_supplier (
    supplier VARCHAR(100) PRIMARY KEY,
    supplier_name VARCHAR(200)
);

CREATE TABLE fact_demand (
    date_key DATE,
    sku VARCHAR(50),
    warehouse VARCHAR(100),
    historical_demand NUMERIC(18,2),
    units_sold NUMERIC(18,2),
    forecast_demand NUMERIC(18,2),
    forecast_error NUMERIC(18,2),
    seasonality_index NUMERIC(18,4),
    demand_variability NUMERIC(18,4),
    PRIMARY KEY (date_key, sku, warehouse)
);

CREATE TABLE fact_inventory (
    date_key DATE,
    sku VARCHAR(50),
    warehouse VARCHAR(100),
    inventory_on_hand NUMERIC(18,2),
    inventory_position NUMERIC(18,2),
    safety_stock NUMERIC(18,2),
    reorder_point NUMERIC(18,2),
    lead_time_days NUMERIC(18,2),
    service_level_target NUMERIC(5,4),
    PRIMARY KEY (date_key, sku, warehouse)
);

CREATE TABLE fact_purchase_orders (
    date_key DATE,
    sku VARCHAR(50),
    warehouse VARCHAR(100),
    supplier VARCHAR(100),
    order_quantity NUMERIC(18,2),
    unit_cost NUMERIC(18,4),
    revenue NUMERIC(18,2),
    PRIMARY KEY (date_key, sku, warehouse, supplier)
);

CREATE INDEX idx_stg_demand_sku_date ON stg_demand (sku, date_key);
CREATE INDEX idx_stg_inventory_sku_warehouse ON stg_inventory (sku, warehouse, date_key);
CREATE INDEX idx_fact_inventory_warehouse ON fact_inventory (warehouse, sku);
CREATE INDEX idx_fact_demand_warehouse ON fact_demand (warehouse, sku, date_key);

CREATE VIEW vw_demand_by_sku_date_location AS
SELECT
    d.date_key,
    d.sku,
    d.warehouse,
    d.historical_demand,
    d.forecast_demand,
    d.forecast_error,
    d.demand_variability
FROM fact_demand d;

CREATE VIEW vw_inventory_position_by_sku_location AS
SELECT
    i.date_key,
    i.sku,
    i.warehouse,
    i.inventory_on_hand,
    i.inventory_position,
    i.safety_stock,
    i.reorder_point,
    i.lead_time_days,
    i.service_level_target
FROM fact_inventory i;

CREATE VIEW vw_purchase_orders_by_sku_vendor AS
SELECT
    p.date_key,
    p.sku,
    p.warehouse,
    p.supplier,
    p.order_quantity,
    p.unit_cost,
    p.revenue
FROM fact_purchase_orders p;

CREATE VIEW vw_demand_vs_inventory_gap AS
SELECT
    d.date_key,
    d.sku,
    d.warehouse,
    d.historical_demand,
    i.inventory_on_hand,
    (d.historical_demand - i.inventory_on_hand) AS demand_inventory_gap
FROM fact_demand d
LEFT JOIN fact_inventory i
    ON d.date_key = i.date_key
   AND d.sku = i.sku
   AND d.warehouse = i.warehouse;

CREATE VIEW vw_replenishment_candidates AS
SELECT
    i.date_key,
    i.sku,
    i.warehouse,
    i.inventory_on_hand,
    i.inventory_position,
    i.safety_stock,
    i.reorder_point,
    i.lead_time_days,
    CASE
        WHEN i.inventory_on_hand < i.safety_stock THEN 'Critical'
        WHEN i.inventory_on_hand < i.reorder_point THEN 'High'
        ELSE 'Low'
    END AS replenishment_priority
FROM fact_inventory i;

CREATE VIEW vw_forecast_variance AS
SELECT
    date_key,
    sku,
    warehouse,
    historical_demand,
    forecast_demand,
    forecast_error,
    ((forecast_error / NULLIF(historical_demand, 0)) * 100.0) AS percent_variance
FROM fact_demand;
