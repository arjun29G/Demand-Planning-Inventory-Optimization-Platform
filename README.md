# Demand Planning & Inventory Optimization Platform

This repository implements an enterprise-style planning analytics platform built around a synthetic but SAP-MM-aligned inventory and demand dataset. The project preserves the existing Python and Streamlit application while adding the missing SQL, Power Query, DAX, and documentation layers required to align with a realistic resume project around demand planning and inventory optimization.

## Business Problem

The platform supports planning teams in understanding:
- demand forecast performance
- stock availability and inventory position
- replenishment and reorder risk
- safety-stock and reorder exceptions
- warehouse and supplier-level supply risk
- stockout exposure and shortage-prone SKUs

## Resume Positioning

The project is positioned as an SAP MM-aligned, synthetic-data demand planning and inventory optimization solution for:
- Power BI reporting
- SQL analytical modeling
- Python analytics
- Streamlit dashboarding

It is not a live SAP ERP connection and should not be described as a direct SAP production integration.

## High-Level Architecture

```text
Synthetic SAP-MM-Aligned Planning Dataset
    |
    v
Python validation and data quality checks
    |
    v
SQL staging and analytics model
    |
    v
Power Query transformations
    |
    v
Power BI semantic model and DAX measures
    |
    v
Streamlit companion dashboard
```

## Repository Structure

```text
streamlit_app/
├── app.py
├── core/
│   ├── analytics_engine.py
│   ├── data_manager.py
│   ├── column_mapper.py
│   └── powerbi_theme.py
└── pages/
    ├── 01_Demand_Forecasting_and_Seasonality.py
    ├── 02_Demand_Variability_and_ABC_XYZ.py
    ├── 03_Inventory_Optimization_and_Safety_Stock.py
    ├── 04_Stockout_Risk_Engine.py
    ├── 05_Replenishment_Planning.py
    ├── 06_Forecast_Accuracy_and_Service_Levels.py
    └── 07_Data_Governance_and_1M_Pipeline.py

sql/
├── 01_create_database.sql
├── 02_create_schema.sql
├── 03_create_staging_tables.sql
├── 04_create_dimension_tables.sql
├── 05_create_fact_tables.sql
├── 06_create_analytical_views.sql
├── 07_create_indexes.sql
├── 08_validation_queries.sql

powerbi/
├── PowerQuery_M.md
├── POWER_BI_MEASURES.md
├── Data_Model.md

docs/
├── SAP_MM_ALIGNMENT.md
├── SQL_DATA_MODEL.md
├── POWER_BI_DATA_MODEL.md
├── POWER_BI_RECONCILIATION.md
├── RESUME_ALIGNMENT_MATRIX.md
├── RESUME_CLAIM_VALIDATION.md
├── DATA_QUALITY_REPORT.md
├── PROJECT_ARCHITECTURE.md
```

## Dataset

Primary source:
- assets/data/pharmaceutical_demand_1m.csv

The dataset is synthetic but structured to resemble common SAP MM planning data. It includes fields for:
- demand history and forecast
- inventory position and safety stock
- reorder point and lead time
- warehouse and supplier segmentation
- stockout exposure
- order quantity and revenue

Actual verified dataset numbers:
- rows: 1,000,000
- SKUs: 500
- warehouses: 5
- suppliers: 5

## SAP MM Conceptual Mapping

The solution intentionally documents SAP MM equivalents such as:
- SKU -> material number
- Warehouse -> planning location / plant concept
- Supplier -> vendor
- Inventory_On_Hand -> available stock
- Safety_Stock -> planning buffer
- Reorder_Point -> replenishment trigger
- Lead_Time_Days -> purchasing lead time

See [docs/SAP_MM_ALIGNMENT.md](docs/SAP_MM_ALIGNMENT.md).

## SQL Layer

SQL scripts are created under [sql](sql) and cover:
- database setup
- schemas
- staging tables
- dimension tables
- fact tables
- analytical views
- indexes
- validation queries

The SQL layer is built to mirror the synthetic planning workflow and is intended for Power BI extraction.

## Power Query Layer

Power Query M transformations are documented in [powerbi/PowerQuery_M.md](powerbi/PowerQuery_M.md). They cover:
- data typing
- null handling
- column standardization
- date conversion
- safety-stock and reorder flags
- forecast variance and inventory status calculations

## Power BI Layer

The repository contains:
- a Power BI semantic model specification in [docs/POWER_BI_DATA_MODEL.md](docs/POWER_BI_DATA_MODEL.md)
- a DAX measure catalog in [powerbi/POWER_BI_MEASURES.md](powerbi/POWER_BI_MEASURES.md)
- a complete Power Query and DAX package for the enterprise planning dashboard

> Power BI implementation package complete; PBIX assembly remains manual because Power BI Desktop is unavailable on this machine.

The project therefore documents the exact Power BI configuration and manual assembly steps that remain outside the repository.

## DAX and KPI Logic

The project defines DAX measures for:
- total demand
- total forecast demand
- units sold
- inventory and inventory value
- revenue
- forecast variance and variance percentage
- accuracy and MAPE/WAPE proxies
- stockout events and risk rate
- safety-stock gap
- reorder exceptions
- replenishment priority counts

Important: if a metric is not truly supported by the source, it is documented as a proxy or unsupported rather than being fabricated.

## Streamlit Application

The existing Streamlit app is preserved and remains the interactive Python companion to the analytical model. It supports:
- demand planning
- forecasting and seasonality review
- inventory optimization
- stockout risk analysis
- replenishment logic
- forecast accuracy and service-level proxy views (Units Sold / Historical Demand — not a true order fill rate)
- data governance checks

## Demand Planning and Inventory Optimization

Implemented logic includes:
- forecast variance
- forecast accuracy metrics
- historical demand and forecast views
- SKU, warehouse, category, and supplier planning segmentation
- safety stock and reorder-point evaluation
- inventory position calculation
- replenishment priority classification
- shortage risk analysis

## Supported vs unsupported metrics

- Backorders = UNSUPPORTED
- True Fill Rate = UNSUPPORTED
- Service Level Proxy = SUPPORTED AS PROXY
- Inventory Aging = UNSUPPORTED
- Direct SAP MM production connection = UNSUPPORTED

## Safety Stock and Reorder Logic

The project uses actual safety-stock and reorder-point values where they exist in the data. It calculates:
- safety stock gap = inventory on hand - safety stock
- reorder exception = inventory position <= reorder point
- replenishment priority = critical / high / medium / low based on actual inventory and risk inputs

## Backorders, Fill Rate, and Inventory Aging

These are handled honestly:
- backorders: unsupported in the current synthetic source; no actual order-line backorder table exists
- true fill rate / customer-order fulfillment: unsupported (no order / backorder lines)
- **Service Level Proxy** (Streamlit KPI): `Units Sold / Historical Demand` — labeled as a proxy, not a true fill rate
- inventory aging: no receipt-date or lot-age history exists, so it is documented as unsupported

This is explicitly documented in [docs/RESUME_CLAIM_VALIDATION.md](docs/RESUME_CLAIM_VALIDATION.md).

## Data Quality

The project validates:
- duplicate rows
- missing required columns
- negative quantities
- negative prices
- invalid dates
- null planning keys

Actual result on the source dataset:
- row count: 1,000,000
- duplicate rows: 0
- missing values: 0
- overall status: PASS

The report is stored at [data_quality_report.csv](data_quality_report.csv) and summarized in [docs/DATA_QUALITY_REPORT.md](docs/DATA_QUALITY_REPORT.md).

## Excel Export

A planning extract workbook is generated in [exports/planning_extract.xlsx](exports/planning_extract.xlsx). It contains sheets for:
- Demand Planning
- Inventory
- Replenishment
- Forecast Accuracy
- SKU Risk

## Validation and Tests

The project includes the actual regression tests:
- [tests/test_planning_metrics.py](tests/test_planning_metrics.py)
- [tests/test_reconciliation.py](tests/test_reconciliation.py)

Executed command:

```bash
cd "D:\Projects\Enterprise-SAP-Style-Supply-Chain-Analytics-Planning-Platform-main"
.\.venv\Scripts\python -m pytest tests/test_planning_metrics.py tests/test_reconciliation.py -q
```

Verified result:
- 8 passed in 7.01s

## Run Instructions

```bash
cd "D:\Projects\Enterprise-SAP-Style-Supply-Chain-Analytics-Planning-Platform-main"
.\.venv\Scripts\python generate_exports.py
.\.venv\Scripts\streamlit run streamlit_app/app.py
```

## Documentation

Key project docs:
- [docs/SAP_MM_ALIGNMENT.md](docs/SAP_MM_ALIGNMENT.md)
- [docs/SQL_DATA_MODEL.md](docs/SQL_DATA_MODEL.md)
- [docs/POWER_BI_DATA_MODEL.md](docs/POWER_BI_DATA_MODEL.md)
- [docs/POWER_BI_RECONCILIATION.md](docs/POWER_BI_RECONCILIATION.md)
- [docs/RESUME_ALIGNMENT_MATRIX.md](docs/RESUME_ALIGNMENT_MATRIX.md)
- [docs/RESUME_CLAIM_VALIDATION.md](docs/RESUME_CLAIM_VALIDATION.md)

## Honest Resume Alignment

This project is substantially aligned with the resume theme while remaining honest about the synthetic-source limitations.

Overall honest alignment: 85% to 90%

Why not 100%:
- no live SAP production connection
- no actual SAP MM extraction
- no native Power BI `.pbix` file in this environment
- no true backorder, fill-rate, or inventory-aging source fields

The project is therefore best described as:

Enterprise-style Demand Planning & Inventory Optimization Platform using a synthetic SAP-MM-aligned planning dataset, SQL analytics, Power Query preparation logic, DAX measures, and a Python/Streamlit analytical layer.

