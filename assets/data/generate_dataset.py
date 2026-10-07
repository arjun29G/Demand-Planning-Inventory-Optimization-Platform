import os
import time
import numpy as np
import pandas as pd

def generate_supply_chain_data(num_records: int = 1000000, num_skus: int = 500, num_warehouses: int = 5) -> pd.DataFrame:
    """
    Generates a high-performance synthetic supply chain dataset with realistic 
    demand forecasting, inventory optimization, lead times, and SAP-style attributes.
    Optimized with NumPy vectorization to scale to 1M+ rows in under 2 seconds.
    """
    print(f"Generating {num_records:,} records across {num_skus} SKUs...")
    start_time = time.time()
    
    np.random.seed(42)

    # Base Master Data Definition
    skus = [f"SKU-{1000 + i}" for i in range(num_skus)]
    categories = ["Prescription Drugs", "Over-The-Counter", "Medical Devices", "Vaccines & Biologics", "Diagnostics"]
    subcategories = {
        "Prescription Drugs": ["Cardiology", "Antibiotics", "Oncology", "Neurology"],
        "Over-The-Counter": ["Analgesics", "Cold & Flu", "Vitamins", "Digestive Health"],
        "Medical Devices": ["Surgical Instruments", "Diagnostic Monitors", "PPE & Supplies", "Orthopedics"],
        "Vaccines & Biologics": ["Viral Vaccines", "Bacterial Vaccines", "Immunoglobulins"],
        "Diagnostics": ["Reagents", "Test Strips", "Imaging Consumables"]
    }
    warehouses = [f"WH-00{i+1} ({region})" for i, region in enumerate(["Central Hub", "East Coast", "West Coast", "EU Gateway", "APAC Logistics"])]
    suppliers = ["PharmaCorp Int", "MediSupply Global", "HealthPlus Ltd", "BioGen Dynamics", "Cardinal Healthcare"]
    
    # Assign SKU master attributes
    sku_master = []
    for i, sku in enumerate(skus):
        cat = categories[i % len(categories)]
        subcat = subcategories[cat][i % len(subcategories[cat])]
        unit_cost = round(float(np.random.uniform(5.0, 350.0)), 2)
        margin_pct = float(np.random.uniform(0.20, 0.60))
        selling_price = round(unit_cost * (1 + margin_pct), 2)
        base_demand = float(np.random.uniform(20.0, 400.0))
        demand_std = float(base_demand * np.random.uniform(0.10, 0.45))
        lead_time_days = int(np.random.choice([3, 5, 7, 10, 14, 21]))
        lead_time_std = float(np.random.uniform(0.5, 3.0))
        target_service_level = float(np.random.choice([0.90, 0.95, 0.98, 0.99]))
        
        sku_master.append({
            "SKU": sku,
            "Product_Name": f"PharmaItem-{sku.split('-')[1]}",
            "Product_Category": cat,
            "Product_Subcategory": subcat,
            "Unit_Cost": unit_cost,
            "Selling_Price": selling_price,
            "Base_Demand": base_demand,
            "Demand_Std": demand_std,
            "Lead_Time_Days": lead_time_days,
            "Lead_Time_Std": lead_time_std,
            "Target_Service_Level": target_service_level,
            "Supplier": suppliers[i % len(suppliers)]
        })
        
    master_df = pd.DataFrame(sku_master)
    
    # Generate Date range (730 days ~ 2 years)
    dates = pd.date_range(start="2024-01-01", periods=num_records // num_skus + 1, freq="D")
    
    # Sample SKU index and Date index array for num_records length
    sku_indices = np.random.choice(num_skus, size=num_records)
    date_indices = np.random.choice(len(dates), size=num_records)
    warehouse_indices = np.random.choice(num_warehouses, size=num_records)
    
    selected_master = master_df.iloc[sku_indices].reset_index(drop=True)
    selected_dates = dates[date_indices]
    selected_wh = [warehouses[w] for w in warehouse_indices]
    
    # Vectorized Seasonal & Trend calculation
    day_of_year = selected_dates.dayofyear.values
    month_of_year = selected_dates.month.values
    
    # Seasonality index: peaks in Q1 (flu season) & Q4 (winter surge)
    seasonality_index = 1.0 + 0.25 * np.sin(2 * np.pi * day_of_year / 365) + 0.15 * np.cos(4 * np.pi * day_of_year / 365)
    trend_factor = 1.0 + (day_of_year / 365.0) * 0.05
    
    # Compute noise and demand
    base_dem = selected_master["Base_Demand"].values
    dem_std = selected_master["Demand_Std"].values
    noise = np.random.normal(0, dem_std, size=num_records)
    
    historical_demand = np.maximum(0, np.round(base_dem * seasonality_index * trend_factor + noise)).astype(int)
    units_sold = np.maximum(0, np.round(historical_demand * np.random.uniform(0.92, 1.0))).astype(int)
    
    # Forecast demand calculation (with slight forecast error)
    forecast_bias_pct = np.random.uniform(-0.08, 0.08, size=num_records)
    forecast_demand = np.maximum(0, np.round(historical_demand * (1 + forecast_bias_pct))).astype(int)
    
    forecast_lower = np.maximum(0, np.round(forecast_demand * 0.85)).astype(int)
    forecast_upper = np.round(forecast_demand * 1.15).astype(int)
    
    # Inventory On Hand simulation
    lt_days = selected_master["Lead_Time_Days"].values
    target_sl = selected_master["Target_Service_Level"].values
    
    # Z-scores for service levels: 0.90->1.28, 0.95->1.645, 0.98->2.05, 0.99->2.33
    z_scores = np.where(target_sl >= 0.99, 2.33, np.where(target_sl >= 0.98, 2.05, np.where(target_sl >= 0.95, 1.645, 1.28)))
    
    # Safety Stock formula: SS = Z * sqrt(L * sigma_D^2 + D^2 * sigma_L^2)
    lt_std = selected_master["Lead_Time_Std"].values
    safety_stock = np.round(z_scores * np.sqrt(lt_days * (dem_std ** 2) + (base_dem ** 2) * (lt_std ** 2))).astype(int)
    reorder_point = np.round(base_dem * (lt_days / 30.0) + safety_stock).astype(int)
    
    # Simulated inventory levels
    inv_factor = np.random.uniform(0.4, 2.2, size=num_records)
    inventory_on_hand = np.maximum(0, np.round(reorder_point * inv_factor)).astype(int)
    inventory_position = inventory_on_hand + np.random.randint(0, 100, size=num_records)
    
    # Stockout events
    stockout_events = np.where(inventory_on_hand < (historical_demand * 0.2), 1, 0)
    
    # Metrics
    forecast_error = forecast_demand - historical_demand
    abs_error = np.abs(forecast_error)
    mape = np.round((abs_error / np.maximum(1, historical_demand)) * 100, 2)
    forecast_accuracy = np.clip(100.0 - mape, 0.0, 100.0)
    demand_cv = np.round(dem_std / np.maximum(1.0, base_dem), 2)
    
    # Assemble DataFrame
    df = pd.DataFrame({
        "Date": selected_dates.strftime("%Y-%m-%d"),
        "SKU": selected_master["SKU"].values,
        "Product_Name": selected_master["Product_Name"].values,
        "Product_Category": selected_master["Product_Category"].values,
        "Product_Subcategory": selected_master["Product_Subcategory"].values,
        "Warehouse": selected_wh,
        "Region": [w.split("(")[1].replace(")", "") for w in selected_wh],
        "Supplier": selected_master["Supplier"].values,
        "Historical_Demand": historical_demand,
        "Units_Sold": units_sold,
        "Order_Quantity": units_sold,
        "Inventory_On_Hand": inventory_on_hand,
        "Inventory_Position": inventory_position,
        "Lead_Time_Days": lt_days,
        "Unit_Cost": selected_master["Unit_Cost"].values,
        "Selling_Price": selected_master["Selling_Price"].values,
        "Revenue": np.round(units_sold * selected_master["Selling_Price"].values, 2),
        "Safety_Stock": safety_stock,
        "Reorder_Point": reorder_point,
        "Service_Level_Target": target_sl,
        "Stockout_Events": stockout_events,
        "Forecast_Demand": forecast_demand,
        "Forecast_Lower_Bound": forecast_lower,
        "Forecast_Upper_Bound": forecast_upper,
        "Seasonality_Index": np.round(seasonality_index, 3),
        "Demand_Variability": demand_cv,
        "Forecast_Error": forecast_error,
        "Forecast_Accuracy": forecast_accuracy
    })
    
    elapsed = time.time() - start_time
    print(f"Dataset generated successfully in {elapsed:.2f} seconds. Shape: {df.shape}")
    return df

if __name__ == "__main__":
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(output_dir, "pharmaceutical_demand_1m.csv")
    df = generate_supply_chain_data(num_records=1000000)
    print("Saving to CSV...")
    df.to_csv(output_path, index=False)
    print(f"Saved 1M record dataset to {output_path}")
