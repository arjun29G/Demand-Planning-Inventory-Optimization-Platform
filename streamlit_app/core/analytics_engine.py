import numpy as np
import pandas as pd
from scipy.stats import norm
from typing import Dict, Tuple, Any, Optional, List

DATA_UNAVAILABLE = "Data unavailable"
FORECAST_UNAVAILABLE = "Forecast data unavailable"


# =========================================================
# 0. PLANNING GRAIN HELPERS (SKU + Warehouse)
# =========================================================

def planning_group_keys(sku_col: str, warehouse_col: Optional[str], df: pd.DataFrame) -> List[str]:
    """Return actionable planning grain: SKU + Warehouse when warehouse exists."""
    keys = [sku_col]
    if warehouse_col and warehouse_col in df.columns:
        keys.append(warehouse_col)
    return keys


def _safe_float(value: Any) -> Optional[float]:
    """Convert to float; return None when missing/non-finite."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(out):
        return None
    return out


def calculate_inventory_position(
    on_hand: Optional[float],
    open_purchase_orders: Optional[float] = None,
) -> Optional[float]:
    """Inventory Position = On Hand + Open Purchase Orders.

    The source dataset does not provide backorder transactions, so the position is
    calculated only from actual on-hand stock and open purchase orders.
    """
    inv = _safe_float(on_hand)
    if inv is None:
        return None

    open_po = _safe_float(open_purchase_orders) if open_purchase_orders is not None else 0.0

    if open_po is None:
        open_po = 0.0

    return round(inv + open_po, 2)


def classify_replenishment_priority(
    inventory_on_hand: Optional[float],
    safety_stock: Optional[float] = None,
    reorder_point: Optional[float] = None,
    forecast_daily_demand: Optional[float] = None,
    lead_time_days: Optional[float] = None,
    demand_supply_gap: Optional[float] = 0.0,
    stockout_risk_pct: float = 0.0,
) -> str:
    """Transparent replenishment classification based on actual gap data.

    Priorities are assigned using a documented sequence:
    - Critical: inventory is near zero, below a steep safety-stock threshold, or
      stockout risk is very high.
    - High: inventory is below reorder point or below safety stock.
    - Medium: inventory is still under a planned buffer threshold or the
      demand-supply gap is material but not critical.
    - Low: inventory is comfortable and not approaching risk.
    """
    inv = _safe_float(inventory_on_hand)
    if inv is None:
        return DATA_UNAVAILABLE

    ss = _safe_float(safety_stock) if safety_stock is not None else None
    rop = _safe_float(reorder_point) if reorder_point is not None else None
    gap = _safe_float(demand_supply_gap) if demand_supply_gap is not None else 0.0
    risk = _safe_float(stockout_risk_pct) if stockout_risk_pct is not None else 0.0

    if inv <= 0 or (ss is not None and inv <= (ss * 0.25)) or (risk is not None and risk >= 35.0):
        return "Critical"

    if ss is not None and inv <= ss:
        return "High"

    if rop is not None and inv <= rop:
        return "High"

    if risk is not None and risk >= 15.0:
        return "High"

    if (rop is not None and ss is not None and inv <= ((rop + ss) * 0.75)) or (
        gap is not None and gap > 0 and rop is not None and inv <= (rop * 1.35)
    ):
        return "Medium"

    if (forecast_daily_demand is not None and lead_time_days is not None and
            inv <= (forecast_daily_demand * lead_time_days)):
        return "Medium"

    return "Low"


def validate_data_quality(
    df: pd.DataFrame,
    required_columns: Optional[List[str]] = None,
    quantity_columns: Optional[List[str]] = None,
    price_columns: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Return a transparent data-quality summary and fail status flags.

    The function is intended for validation of planning inputs and intentionally
    reports issues without silently discarding rows.
    """
    if df is None or df.empty:
        return {
            "row_count": 0,
            "duplicate_rows": 0,
            "missing_values": 0,
            "negative_quantities": 0,
            "negative_prices": 0,
            "missing_required_columns": [],
            "invalid_dates": 0,
            "overall_status": "FAIL",
            "issues": ["No data available for validation."],
        }

    missing_columns = []
    required = list(required_columns or [])
    for col in required:
        if col not in df.columns:
            missing_columns.append(col)

    duplicate_rows = int(df.duplicated().sum())
    missing_values = int(df.isnull().sum().sum())
    invalid_dates = 0

    if "Date" in df.columns:
        invalid_dates = int(pd.to_datetime(df["Date"], errors="coerce").isna().sum())

    default_quantity_columns = [
        "Historical_Demand",
        "Forecast_Demand",
        "Inventory_On_Hand",
        "Safety_Stock",
        "Reorder_Point",
        "Lead_Time_Days",
        "Units_Sold",
        "Order_Quantity",
    ]
    selected_qty_cols = quantity_columns or default_quantity_columns
    negative_quantities = 0
    for qcol in selected_qty_cols:
        if qcol in df.columns:
            negative_quantities += int((pd.to_numeric(df[qcol], errors="coerce") < 0).sum())

    negative_prices = 0
    if price_columns:
        for pcol in price_columns:
            if pcol in df.columns:
                negative_prices += int((pd.to_numeric(df[pcol], errors="coerce") < 0).sum())
    else:
        for pcol in ["Unit_Cost", "Selling_Price", "Revenue"]:
            if pcol in df.columns:
                negative_prices += int((pd.to_numeric(df[pcol], errors="coerce") < 0).sum())

    issues = []
    if duplicate_rows > 0:
        issues.append(f"Duplicate rows detected: {duplicate_rows}")
    if missing_columns:
        issues.append(f"Missing required columns: {', '.join(missing_columns)}")
    if invalid_dates > 0:
        issues.append(f"Invalid dates detected: {invalid_dates}")
    if negative_quantities > 0:
        issues.append(f"Negative quantities detected: {negative_quantities}")
    if negative_prices > 0:
        issues.append(f"Negative prices detected: {negative_prices}")

    status = "PASS" if not issues else ("WARNING" if duplicate_rows > 0 or invalid_dates > 0 else "FAIL")

    return {
        "row_count": int(len(df)),
        "duplicate_rows": duplicate_rows,
        "missing_values": missing_values,
        "negative_quantities": negative_quantities,
        "negative_prices": negative_prices,
        "missing_required_columns": missing_columns,
        "invalid_dates": invalid_dates,
        "overall_status": status,
        "issues": issues,
    }


def build_planning_summary(
    df: pd.DataFrame,
    col_map: Dict[str, str],
    date_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Aggregate transactional rows to the SKU + Warehouse planning grain.

    Inventory / policy fields use the chronologically latest record per grain.
    Demand statistics use mean / std over the filtered window.
    Forecast metrics are only populated when Forecast_Demand exists — never
    substituted with Historical_Demand.
    """
    sku_col = col_map.get("sku", "SKU")
    wh_col = col_map.get("warehouse", "Warehouse")
    qty_col = col_map.get("quantity", "Historical_Demand")
    fct_col = col_map.get("forecast_demand", "Forecast_Demand")
    stock_col = col_map.get("stock", "Inventory_On_Hand")
    pos_col = col_map.get("inventory_position", "Inventory_Position")
    ss_col = col_map.get("safety_stock", "Safety_Stock")
    rop_col = col_map.get("reorder_point", "Reorder_Point")
    lead_col = col_map.get("lead_time", "Lead_Time_Days")
    cost_col = col_map.get("unit_cost", "Unit_Cost")
    cat_col = col_map.get("category", "Product_Category")
    sup_col = col_map.get("supplier", "Supplier")
    sold_col = col_map.get("units_sold", "Units_Sold")

    if sku_col not in df.columns or df.empty:
        return pd.DataFrame()

    work = df.copy()
    keys = planning_group_keys(sku_col, wh_col, work)

    if date_col and date_col in work.columns:
        work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
        work = work.sort_values(by=keys + [date_col])
    else:
        work = work.sort_values(by=keys)

    # Latest snapshot per planning grain for position / policy fields
    latest = work.groupby(keys, as_index=False).tail(1)

    snap_cols = [c for c in [
        sku_col, wh_col if wh_col in work.columns else None,
        stock_col, pos_col, ss_col, rop_col, lead_col, cost_col, cat_col, sup_col
    ] if c and c in latest.columns]
    snapshot = latest[snap_cols].copy()

    rename = {
        stock_col: "Inventory_On_Hand",
        pos_col: "Inventory_Position",
        ss_col: "Safety_Stock",
        rop_col: "Reorder_Point",
        lead_col: "Lead_Time_Days",
        cost_col: "Unit_Cost",
        cat_col: "Product_Category",
        sup_col: "Supplier",
        wh_col: "Warehouse",
        sku_col: "SKU",
    }
    snapshot = snapshot.rename(columns={k: v for k, v in rename.items() if k in snapshot.columns})

    # Demand / forecast stats over the full filtered window
    stats_parts = []
    if qty_col in work.columns:
        hist = work.groupby(keys)[qty_col].agg(
            Mean_Historical_Daily_Demand="mean",
            Std_Daily_Demand=lambda x: float(x.std()) if len(x) > 1 else np.nan,
            Total_Historical_Demand="sum",
        ).reset_index()
        stats_parts.append(hist)

    if fct_col in work.columns and work[fct_col].notna().any():
        fct = work.groupby(keys)[fct_col].agg(
            Mean_Forecast_Daily_Demand="mean",
            Total_Forecast_Demand="sum",
        ).reset_index()
        stats_parts.append(fct)

    if sold_col in work.columns:
        sold = work.groupby(keys)[sold_col].agg(Total_Units_Sold="sum").reset_index()
        stats_parts.append(sold)

    summary = snapshot
    for part in stats_parts:
        part = part.rename(columns={sku_col: "SKU", wh_col: "Warehouse"} if wh_col in part.columns else {sku_col: "SKU"})
        merge_on = [c for c in ["SKU", "Warehouse"] if c in summary.columns and c in part.columns]
        if not merge_on:
            merge_on = ["SKU"]
        summary = summary.merge(part, on=merge_on, how="left")

    if "Inventory_Position" not in summary.columns and "Inventory_On_Hand" in summary.columns:
        summary["Inventory_Position"] = summary["Inventory_On_Hand"]

    # Documented ROP fallback only when inputs exist (never SS * multiplier)
    if "Reorder_Point" not in summary.columns or summary["Reorder_Point"].isna().any():
        if "Reorder_Point" not in summary.columns:
            summary["Reorder_Point"] = np.nan
        can_calc = (
            summary.get("Mean_Forecast_Daily_Demand").notna()
            & summary.get("Lead_Time_Days").notna()
            & summary.get("Safety_Stock").notna()
        ) if "Mean_Forecast_Daily_Demand" in summary.columns else pd.Series(False, index=summary.index)
        if can_calc.any():
            calc_rop = (
                summary["Mean_Forecast_Daily_Demand"] * summary["Lead_Time_Days"]
                + summary["Safety_Stock"]
            )
            summary.loc[can_calc & summary["Reorder_Point"].isna(), "Reorder_Point"] = np.round(
                calc_rop[can_calc & summary["Reorder_Point"].isna()], 1
            )

    return summary


# =========================================================
# 1. DEMAND FORECASTING & ACCURACY METRICS
# =========================================================

def forecast_moving_average(series: pd.Series, window: int = 3, horizon: int = 6) -> pd.Series:
    """Computes Simple Moving Average forecast."""
    vals = list(series.values)
    forecasts = []
    for _ in range(horizon):
        ma = np.mean(vals[-window:])
        forecasts.append(ma)
        vals.append(ma)

    last_date = series.index[-1]
    if isinstance(last_date, pd.Timestamp):
        new_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=horizon, freq="D")
    else:
        new_dates = pd.date_range(start=pd.to_datetime(last_date) + pd.Timedelta(days=1), periods=horizon, freq="D")
    return pd.Series(forecasts, index=new_dates)


def forecast_weighted_moving_average(series: pd.Series, weights: list = [0.5, 0.3, 0.2], horizon: int = 6) -> pd.Series:
    """Computes Weighted Moving Average forecast."""
    vals = list(series.values)
    window = len(weights)
    norm_weights = np.array(weights) / np.sum(weights)
    forecasts = []
    for _ in range(horizon):
        wma = np.dot(vals[-window:], norm_weights)
        forecasts.append(wma)
        vals.append(wma)

    last_date = series.index[-1]
    new_dates = pd.date_range(start=pd.to_datetime(last_date) + pd.Timedelta(days=1), periods=horizon, freq="D")
    return pd.Series(forecasts, index=new_dates)


def forecast_exponential_smoothing(series: pd.Series, alpha: float = 0.3, beta: float = 0.1, horizon: int = 6) -> pd.Series:
    """Computes Double Exponential Smoothing (Holt's Linear Trend)."""
    vals = series.values
    if len(vals) < 2:
        return pd.Series([vals[0]] * horizon)

    level = vals[0]
    trend = vals[1] - vals[0]

    for i in range(1, len(vals)):
        val = vals[i]
        last_level = level
        level = alpha * val + (1 - alpha) * (level + trend)
        trend = beta * (level - last_level) + (1 - beta) * trend

    forecasts = [level + (h + 1) * trend for h in range(horizon)]
    last_date = series.index[-1]
    new_dates = pd.date_range(start=pd.to_datetime(last_date) + pd.Timedelta(days=1), periods=horizon, freq="D")
    return pd.Series(forecasts, index=new_dates)


def calculate_forecast_metrics(actual: np.ndarray, forecast: np.ndarray) -> Dict[str, Optional[float]]:
    """
    Computes demand forecast error & accuracy metrics from paired actual/forecast values.
    Returns None metrics (not fabricated numbers) when no valid pairs exist.
    """
    actual = np.array(actual, dtype=float)
    forecast = np.array(forecast, dtype=float)

    mask = ~np.isnan(actual) & ~np.isnan(forecast)
    y_act = actual[mask]
    y_hat = forecast[mask]

    if len(y_act) == 0:
        return {"MAE": None, "RMSE": None, "MAPE": None, "WAPE": None, "Bias": None, "Accuracy": None}

    errors = y_hat - y_act
    abs_errors = np.abs(errors)

    mae = float(np.mean(abs_errors))
    rmse = float(np.sqrt(np.mean(errors ** 2)))

    # MAPE: exclude zero / non-positive actual demand so near-zero days
    # do not produce meaningless extreme percentages.
    positive_actual = y_act > 0
    if positive_actual.any():
        mape = float(np.mean(abs_errors[positive_actual] / y_act[positive_actual]) * 100.0)
        mape = round(mape, 2)
    else:
        mape = None

    sum_act = np.sum(y_act)
    wape = float((np.sum(abs_errors) / max(1.0, sum_act)) * 100.0)
    bias = float((np.sum(errors) / max(1.0, sum_act)) * 100.0)

    accuracy = max(0.0, 100.0 - wape)

    return {
        "MAE": round(mae, 2),
        "RMSE": round(rmse, 2),
        "MAPE": mape,
        "WAPE": round(wape, 2),
        "Bias": round(bias, 2),
        "Accuracy": round(accuracy, 2)
    }


def format_metric(value: Optional[float], suffix: str = "", decimals: int = 1) -> str:
    """Format a KPI for display; never invent a placeholder number."""
    if value is None or (isinstance(value, float) and (np.isnan(value) or not np.isfinite(value))):
        return DATA_UNAVAILABLE
    return f"{value:.{decimals}f}{suffix}"


# =========================================================
# 2. DEMAND VARIABILITY & ABC-XYZ MATRIX
# =========================================================

def analyze_demand_variability(
    df: pd.DataFrame,
    sku_col: str,
    qty_col: str,
    rev_col: str = None,
    warehouse_col: str = None,
) -> pd.DataFrame:
    """
    Computes Mean Demand, StdDev, CV, and ABC / XYZ classes.

    When warehouse_col is present, analysis grain is SKU + Warehouse so
    multi-location demand variability is not collapsed incorrectly.
    """
    if rev_col and rev_col in df.columns:
        val_col = rev_col
    else:
        val_col = qty_col

    keys = planning_group_keys(sku_col, warehouse_col, df)

    grp = df.groupby(keys).agg(
        Mean_Demand=(qty_col, "mean"),
        Std_Demand=(qty_col, "std"),
        Total_Volume=(qty_col, "sum"),
        Total_Value=(val_col, "sum")
    ).reset_index()

    grp["Std_Demand"] = grp["Std_Demand"].fillna(0.0)
    grp["CV"] = np.where(grp["Mean_Demand"] > 0, grp["Std_Demand"] / grp["Mean_Demand"], 0.0)
    grp["CV"] = np.round(grp["CV"], 3)

    # XYZ: X (CV < 0.2), Y (0.2-0.5), Z (> 0.5)
    grp["XYZ_Class"] = np.where(
        grp["CV"] < 0.20, "X (Low Volatility)",
        np.where(grp["CV"] <= 0.50, "Y (Med Volatility)", "Z (High Volatility)")
    )

    # ABC: 80% / 15% / 5% Pareto on Total_Value
    grp = grp.sort_values("Total_Value", ascending=False).reset_index(drop=True)
    total_val_sum = grp["Total_Value"].sum()
    grp["Cum_Share"] = (grp["Total_Value"].cumsum() / max(1.0, total_val_sum)) * 100.0

    grp["ABC_Class"] = np.where(
        grp["Cum_Share"] <= 80.0, "A (High Value)",
        np.where(grp["Cum_Share"] <= 95.0, "B (Med Value)", "C (Low Value)")
    )

    grp["ABC_XYZ_Matrix"] = grp["ABC_Class"].str[0] + "-" + grp["XYZ_Class"].str[0]
    return grp


# =========================================================
# 3. SAFETY STOCK & INVENTORY OPTIMIZATION
# =========================================================

def calculate_safety_stock_parameters(
    mean_daily_demand: float,
    std_daily_demand: float,
    lead_time_days: float,
    lead_time_std: float = 0.0,
    service_level: float = 0.95,
    unit_cost: float = 0.0,
    holding_cost_pct: float = 0.20,
    order_cost: float = 250.0
) -> Optional[Dict[str, float]]:
    """
    Safety Stock (SS) = Z * sqrt( L * std_D^2 + D^2 * std_L^2 )
    Reorder Point (ROP) = (D * L) + SS
    EOQ = sqrt( (2 * D_annual * S) / H )

    Returns None when required inputs are missing or non-positive where required.
    Does not invent Lead Time / Demand / Std defaults.
    """
    mean_daily_demand = _safe_float(mean_daily_demand)
    std_daily_demand = _safe_float(std_daily_demand)
    lead_time_days = _safe_float(lead_time_days)
    lead_time_std = _safe_float(lead_time_std)
    unit_cost = _safe_float(unit_cost)

    if mean_daily_demand is None or mean_daily_demand < 0:
        return None
    if std_daily_demand is None or std_daily_demand < 0:
        return None
    if lead_time_days is None or lead_time_days <= 0:
        return None
    if lead_time_std is None or lead_time_std < 0:
        lead_time_std = 0.0
    if unit_cost is None or unit_cost < 0:
        unit_cost = 0.0

    z = float(norm.ppf(service_level))

    ss = z * np.sqrt(
        lead_time_days * (std_daily_demand ** 2) + (mean_daily_demand ** 2) * (lead_time_std ** 2)
    )
    ss = float(np.round(np.maximum(0, ss), 1))

    ltd = mean_daily_demand * lead_time_days
    rop = float(np.round(ltd + ss, 1))

    annual_demand = mean_daily_demand * 365.0
    holding_cost_per_unit = max(0.01, unit_cost * holding_cost_pct) if unit_cost > 0 else 1.0

    eoq = float(np.round(np.sqrt((2 * annual_demand * order_cost) / holding_cost_per_unit), 1))
    ss_value = float(np.round(ss * unit_cost, 2))

    return {
        "Mean_Daily_Demand": round(mean_daily_demand, 2),
        "Std_Daily_Demand": round(std_daily_demand, 2),
        "Lead_Time_Days": round(lead_time_days, 1),
        "Lead_Time_Std": round(lead_time_std, 2),
        "Service_Level": service_level,
        "Z_Score": round(z, 3),
        "Lead_Time_Demand": round(ltd, 1),
        "Safety_Stock": ss,
        "Safety_Stock_Value": ss_value,
        "Reorder_Point": rop,
        "EOQ": eoq
    }


# =========================================================
# 4. STOCKOUT RISK ENGINE
# =========================================================

def evaluate_stockout_risk(
    inventory_on_hand: Optional[float],
    mean_daily_demand: Optional[float],
    std_daily_demand: Optional[float],
    lead_time_days: Optional[float],
    safety_stock: Optional[float],
    reorder_point: Optional[float]
) -> Tuple[Optional[float], str]:
    """
    Computes stockout probability during lead time and assigns risk tier.

    Required inputs must be present and valid. Missing inputs return
    (None, "Data unavailable") — never invented Lead Time / Demand / Std / SS.
    Risk tiers (Critical / High / Medium / Low) use documented policy bands
    against actual Safety Stock and Reorder Point values.
    """
    inv = _safe_float(inventory_on_hand)
    mean_d = _safe_float(mean_daily_demand)
    std_d = _safe_float(std_daily_demand)
    lt = _safe_float(lead_time_days)
    ss = _safe_float(safety_stock)
    rop = _safe_float(reorder_point)

    if any(v is None for v in [inv, mean_d, std_d, lt, ss, rop]):
        return None, DATA_UNAVAILABLE
    if lt <= 0 or mean_d < 0 or std_d < 0 or inv < 0:
        return None, DATA_UNAVAILABLE

    ltd = mean_d * lt
    std_ltd = std_d * np.sqrt(lt)

    if std_ltd <= 0:
        # Deterministic demand over lead time — binary stockout check
        stockout_prob = 100.0 if inv < ltd else 0.0
    else:
        z_avail = (inv - ltd) / std_ltd
        stockout_prob = float(np.clip(1.0 - norm.cdf(z_avail), 0.0, 1.0)) * 100.0

    # Policy bands use actual SS / ROP (classification only — not invented SS values)
    if inv <= (ss * 0.5) or stockout_prob >= 35.0:
        risk_level = "Critical"
    elif inv <= rop or stockout_prob >= 15.0:
        risk_level = "High"
    elif inv <= (rop * 1.3):
        risk_level = "Medium"
    else:
        risk_level = "Low"

    return round(stockout_prob, 2), risk_level


# =========================================================
# 5. DAYS OF SUPPLY & TURNOVER
# =========================================================

def calculate_inventory_turnover(
    df: pd.DataFrame,
    sold_col: str,
    cost_col: str,
    stock_col: str,
    date_col: Optional[str] = None,
    sku_col: Optional[str] = None,
    warehouse_col: Optional[str] = None,
    date_span_days: Optional[int] = None,
) -> Optional[float]:
    """
    Inventory Turnover = Annualized COGS / Average Inventory Value

    COGS = Units_Sold × Unit_Cost  (actual sales, not historical demand proxy)

    Average Inventory Value prefers a time-series average of total inventory capital
    at the daily SKU + Warehouse grain (sum of location inventories per day, then
    mean across days). Falls back to mean(row stock × cost) only when dates/keys
    are unavailable.

    Returns None when required columns are missing or average inventory is zero.
    """
    if df is None or df.empty:
        return None
    if sold_col not in df.columns or cost_col not in df.columns or stock_col not in df.columns:
        return None

    cogs_period = float((df[sold_col].astype(float) * df[cost_col].astype(float)).sum())
    if cogs_period < 0:
        return None

    avg_inv_val = None
    keys = []
    if sku_col and sku_col in df.columns:
        keys.append(sku_col)
    if warehouse_col and warehouse_col in df.columns:
        keys.append(warehouse_col)

    if date_col and date_col in df.columns and keys:
        work = df[[date_col, sold_col, cost_col, stock_col] + keys].copy()
        work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
        work = work.dropna(subset=[date_col])
        if not work.empty:
            # Latest inventory snapshot per SKU+Warehouse per day
            daily_loc = (
                work.sort_values(date_col)
                .groupby([date_col] + keys, as_index=False)
                .agg(**{
                    "_stock": (stock_col, "last"),
                    "_cost": (cost_col, "last"),
                })
            )
            daily_loc["_inv_val"] = daily_loc["_stock"].astype(float) * daily_loc["_cost"].astype(float)
            daily_total = daily_loc.groupby(date_col)["_inv_val"].sum()
            if not daily_total.empty and daily_total.mean() > 0:
                avg_inv_val = float(daily_total.mean())
                if date_span_days is None:
                    date_span_days = max(1, (work[date_col].max() - work[date_col].min()).days + 1)

    if avg_inv_val is None:
        avg_inv_val = float((df[stock_col].astype(float) * df[cost_col].astype(float)).mean())

    if avg_inv_val is None or avg_inv_val <= 0:
        return None

    span = max(1, int(date_span_days)) if date_span_days else 365
    cogs_annualized = cogs_period * (365.0 / span)
    return round(cogs_annualized / avg_inv_val, 2)


def calculate_inventory_kpis(
    inventory_on_hand: float,
    expected_daily_demand: float,
    cogs_annual: float,
    unit_cost: float,
    target_days_of_supply: float = 30.0
) -> Dict[str, Any]:
    """
    Computes Days of Supply, Inventory Turnover, and Inventory Imbalance.
    Does not floor inventory value with arbitrary constants.
    """
    inv = _safe_float(inventory_on_hand)
    demand = _safe_float(expected_daily_demand)
    cost = _safe_float(unit_cost) or 0.0
    cogs = _safe_float(cogs_annual) or 0.0

    if inv is None or demand is None or demand <= 0:
        days_of_supply = None
        status = DATA_UNAVAILABLE
    else:
        days_of_supply = float(np.round(inv / demand, 1))
        if days_of_supply < target_days_of_supply * 0.5:
            status = "Severely Understocked"
        elif days_of_supply < target_days_of_supply:
            status = "Understocked"
        elif days_of_supply <= target_days_of_supply * 1.5:
            status = "Optimal"
        elif days_of_supply <= target_days_of_supply * 2.5:
            status = "Overstocked"
        else:
            status = "Excess / Non-Moving"

    inv_value = (inv * cost) if inv is not None else None
    if inv_value is not None and inv_value > 0 and cogs > 0:
        turnover = float(np.round(cogs / inv_value, 2))
    else:
        turnover = None

    return {
        "Days_Of_Supply": days_of_supply,
        "Target_Days_Of_Supply": target_days_of_supply,
        "Days_Diff": round(days_of_supply - target_days_of_supply, 1) if days_of_supply is not None else None,
        "Inventory_Turnover": turnover,
        "Inventory_Value": round(inv_value, 2) if inv_value is not None else None,
        "Status": status
    }


# =========================================================
# 6. REPLENISHMENT PLANNING ENGINE
# =========================================================

def generate_replenishment_recommendation(
    sku: str,
    inventory_on_hand: Optional[float],
    inventory_position: Optional[float],
    reorder_point: Optional[float],
    lead_time_days: Optional[float],
    forecast_daily_demand: Optional[float],
    safety_stock: Optional[float],
    warehouse: str = None,
    supplier: str = None,
    unit_cost: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Target Inventory Position = Forecast Daily Demand × Lead Time + Safety Stock
    Recommended Order Quantity = MAX(0, Target Inventory Position − Inventory Position)

    Records missing required forecast / policy inputs are marked Needs_Order=False
    with Recommended_Order_Qty as Data unavailable rather than inventing values.
    """
    inv = _safe_float(inventory_on_hand)
    pos = _safe_float(inventory_position)
    rop = _safe_float(reorder_point)
    lt = _safe_float(lead_time_days)
    fct = _safe_float(forecast_daily_demand)
    ss = _safe_float(safety_stock)
    cost = _safe_float(unit_cost)

    if pos is None:
        pos = inv

    result = {
        "SKU": sku,
        "Warehouse": warehouse,
        "Supplier": supplier,
        "Inventory_On_Hand": int(inv) if inv is not None else None,
        "Inventory_Position": int(pos) if pos is not None else None,
        "Safety_Stock": int(ss) if ss is not None else None,
        "Reorder_Point": int(rop) if rop is not None else None,
        "Lead_Time_Days": lt,
        "Forecast_Daily_Demand": round(fct, 2) if fct is not None else None,
        "Needs_Order": False,
        "Recommended_Order_Qty": None,
        "Target_Inventory_Position": None,
        "Days_Of_Supply": None,
        "Estimated_Order_Value": None,
        "Expected_Stockout_Date": DATA_UNAVAILABLE,
        "Recommended_Order_Date": DATA_UNAVAILABLE,
        "Status_Note": None,
    }

    if any(v is None for v in [inv, pos, rop, lt, fct, ss]):
        result["Status_Note"] = FORECAST_UNAVAILABLE if fct is None else DATA_UNAVAILABLE
        return result

    target_pos = fct * lt + ss
    recommended_qty = int(max(0, round(target_pos - pos)))
    days_of_supply = round(inv / fct, 1) if fct > 0 else None

    needs_order = (pos <= rop) or (inv <= ss)

    today = pd.Timestamp.now().normalize()
    if fct > 0:
        days_until_stockout = max(0.0, inv / fct)
        expected_stockout_date = today + pd.Timedelta(days=int(days_until_stockout))
        recommended_order_date = max(today, expected_stockout_date - pd.Timedelta(days=int(lt)))
        result["Expected_Stockout_Date"] = expected_stockout_date.strftime("%Y-%m-%d")
        result["Recommended_Order_Date"] = recommended_order_date.strftime("%Y-%m-%d")

    result.update({
        "Needs_Order": bool(needs_order and recommended_qty > 0),
        "Recommended_Order_Qty": recommended_qty if needs_order else 0,
        "Target_Inventory_Position": round(target_pos, 1),
        "Days_Of_Supply": days_of_supply,
        "Estimated_Order_Value": round(recommended_qty * cost, 2) if (needs_order and cost is not None) else (0.0 if not needs_order else None),
        "Status_Note": None,
    })
    return result
