from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import pandas as pd
import io
import uuid
import datetime
import asyncio
import math
import models, database, external_sensing

# Create database tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Weak Signal Intelligence API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple global store for demo (replace with DB query in production)
last_results = {"internal": [], "external": [], "future_impact": {}}

def compute_future_impact(df, internal_signals, external_signals):
    # Detect Schema
    jewellery_cols = ['gold_stock_gm', 'supplier_delay_days', 'advance_bookings', 'sales_inr']
    
    if all(col in df.columns for col in jewellery_cols):
        cols = {'stock': 'gold_stock_gm', 'delay': 'supplier_delay_days', 'bookings': 'advance_bookings', 'sales': 'sales_inr'}
        is_jewellery = True
    else:
        cols = {'stock': 'battery_stock_units', 'delay': 'supplier_lead_time_days', 'bookings': None, 'sales': 'production_units'}
        is_jewellery = False

    df_recent = df.tail(7)
    
    def get_trend(col_name):
        if col_name is None or col_name not in df.columns: return 0
        series = df_recent[col_name]
        if len(series) < 2: return 0
        return (series.iloc[-1] - series.iloc[0]) / (len(series) - 1)

    trends = {
        'stock': get_trend(cols['stock']),
        'delay': get_trend(cols['delay']),
        'bookings': get_trend(cols['bookings']),
        'sales': get_trend(cols['sales'])
    }

    def get_historical_trends(col_name):
        if col_name is None or col_name not in df.columns: return []
        h_trends = []
        for i in range(len(df) - 6):
            window = df.iloc[i:i+7][col_name]
            h_trends.append((window.iloc[-1] - window.iloc[0]) / 6)
        return h_trends

    def normalize_value(val, history, reverse=False):
        if not history: return 0.5
        h = pd.Series(history)
        median = h.median()
        mad = (h - median).abs().median()
        z = (val - median) / (mad + 1e-9)
        if reverse: z = -z
        return 1 / (1 + math.exp(-z))

    stock_risk = normalize_value(trends['stock'], get_historical_trends(cols['stock']), reverse=True)
    delay_risk = normalize_value(trends['delay'], get_historical_trends(cols['delay']))
    
    if is_jewellery:
        bookings_risk = normalize_value(trends['bookings'], get_historical_trends(cols['bookings']))
        sales_risk = normalize_value(trends['sales'], get_historical_trends(cols['sales']), reverse=True)
        w_stock, w_delay, w_bookings, w_sales = 0.35, 0.25, 0.25, 0.15
    else:
        bookings_risk = 0
        sales_risk = normalize_value(trends['sales'], get_historical_trends(cols['sales'])) # Prod up is pressure
        w_stock, w_delay, w_bookings, w_sales = 0.35, 0.25, 0, 0.15
        total_w = w_stock + w_delay + w_sales
        w_stock /= total_w
        w_delay /= total_w
        w_sales /= total_w

    risk_score = w_stock*stock_risk + w_delay*delay_risk + w_bookings*bookings_risk + w_sales*sales_risk
    probability_percent = round(100 * max(0, min(0.95, risk_score)), 0)

    if probability_percent < 35: severity_level = "LOW"
    elif probability_percent <= 55: severity_level = "MEDIUM"
    elif probability_percent <= 75: severity_level = "HIGH"
    else: severity_level = "CRITICAL"

    urgency = max(stock_risk, delay_risk)
    days_min = round(14 - 10*urgency)
    days_min = max(3, min(21, days_min))
    days_max = days_min + 7
    time_window_days = f"{days_min}-{days_max} days"

    if not is_jewellery and 'battery_cost_per_unit' in df.columns:
        last_cost = df['battery_cost_per_unit'].iloc[-1]
        first_cost = df.tail(7)['battery_cost_per_unit'].iloc[0]
        procurement_cost_rise_pct = round((last_cost - first_cost) / first_cost * 100, 1) if first_cost != 0 else 0
    else:
        procurement_cost_rise_pct = round(2 + 8*(0.5*delay_risk + 0.5*stock_risk), 1)
    
    margin_risk_pct = round(procurement_cost_rise_pct * 0.6, 1)
    
    demand_pressure = "NEUTRAL"
    if is_jewellery:
        if trends['bookings'] > 0 and bookings_risk > 0.6: demand_pressure = "UP"
        elif trends['sales'] < 0 and sales_risk > 0.6: demand_pressure = "DOWN"
    else: # EV
        if trends['sales'] > 0 and sales_risk > 0.6: demand_pressure = "UP"
    
    actions = []
    if stock_risk > 0.6: actions.append("Increase buffer inventory / reorder earlier")
    if delay_risk > 0.6: actions.append("Lock supplier slots / confirm delivery schedule")
    if demand_pressure == "UP": actions.append("Prepare for demand surge (stock + staffing)")
    if severity_level in ["HIGH", "CRITICAL"]: actions.append("Pause non-essential spending until stability improves")

    drivers = []
    if stock_risk > 0.5: drivers.append("Inventory depletion")
    if delay_risk > 0.5: drivers.append("Supply chain delay")
    if bookings_risk > 0.5: drivers.append("Booking surge")
    if sales_risk > 0.5: drivers.append("Sales weakness" if is_jewellery else "Production pressure")
    
    if not drivers: drivers = ["Market trends"]
    
    impact_summary = f"Based on recent trends, risk is {severity_level} with {int(probability_percent)}% probability within {time_window_days}. Key drivers: {', '.join(drivers[:2])}. Suggested actions: {', '.join(actions[:2])}."

    return {
        "probability_percent": int(probability_percent),
        "severity_level": severity_level,
        "time_window_days": time_window_days,
        "impact_summary": impact_summary,
        "impact_breakdown": {
            "procurement_cost_rise_pct": float(procurement_cost_rise_pct),
            "margin_risk_pct": float(margin_risk_pct),
            "demand_pressure": demand_pressure
        },
        "recommended_actions": actions
    }

@app.get("/")
async def root():
    return {"message": "Weak Signal Intelligence API is running"}

@app.post("/upload/internal")
async def upload_internal_data(file: UploadFile = File(...), db: Session = Depends(database.get_db)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    
    contents = await file.read()
    df = pd.read_csv(io.BytesIO(contents))
    
    # Dataset Detection
    jewellery_cols = ['date', 'sales_inr', 'gold_stock_gm', 'supplier_delay_days', 'advance_bookings']
    ev_cols = ['date', 'production_units', 'battery_stock_units', 'supplier_lead_time_days', 'battery_cost_per_unit']
    
    dataset_type = None
    if all(col in df.columns for col in jewellery_cols):
        dataset_type = "jewellery"
    elif all(col in df.columns for col in ev_cols):
        dataset_type = "ev"
    else:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported CSV schema. Detected columns: {list(df.columns)}"
        )

    # Process Data
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    latest_timestamp = df['date'].iloc[-1].isoformat()

    internal_signals = []

    if dataset_type == "jewellery":
        # Internal Jewellery Logic (last 3 rows)
        if len(df) >= 3:
            last3 = df.tail(3)
            # a) Stock decreasing
            stocks = last3['gold_stock_gm'].tolist()
            if stocks[0] > stocks[1] > stocks[2]:
                internal_signals.append({
                    "signal": "Gold stock is continuously decreasing",
                    "metric": "gold_stock_gm",
                    "strength": "weak",
                    "severity": 0.70,
                    "timestamp": latest_timestamp,
                    "type": "Internal"
                })
            # b) Supplier delay increasing
            delays = last3['supplier_delay_days'].tolist()
            if delays[2] - delays[0] >= 1:
                internal_signals.append({
                    "signal": "Supplier delivery delay is increasing",
                    "metric": "supplier_delay_days",
                    "strength": "weak",
                    "severity": 0.65,
                    "timestamp": latest_timestamp,
                    "type": "Internal"
                })
            # c) Advance bookings rising
            bookings = last3['advance_bookings'].tolist()
            if bookings[2] > bookings[1] > bookings[0]:
                internal_signals.append({
                    "signal": "Advance bookings are rising",
                    "metric": "advance_bookings",
                    "strength": "weak",
                    "severity": 0.60,
                    "timestamp": latest_timestamp,
                    "type": "Internal"
                })

    elif dataset_type == "ev":
        # Internal EV Logic (last 3 rows)
        if len(df) >= 3:
            last3 = df.tail(3)
            # a) Battery stock decreasing
            stocks = last3['battery_stock_units'].tolist()
            if stocks[0] > stocks[1] > stocks[2]:
                internal_signals.append({
                    "signal": "Battery stock is continuously decreasing",
                    "metric": "battery_stock_units",
                    "strength": "weak",
                    "severity": 0.70,
                    "timestamp": latest_timestamp,
                    "type": "Internal"
                })
            # b) Supplier lead time increasing
            leads = last3['supplier_lead_time_days'].tolist()
            if leads[2] - leads[0] >= 1:
                internal_signals.append({
                    "signal": "Supplier lead time is increasing",
                    "metric": "supplier_lead_time_days",
                    "strength": "weak",
                    "severity": 0.65,
                    "timestamp": latest_timestamp,
                    "type": "Internal"
                })
            # c) Production rising but stock falling
            prod = last3['production_units'].tolist()
            if prod[2] > prod[0] and stocks[2] < stocks[0]:
                internal_signals.append({
                    "signal": "Production pressure rising while stock is falling",
                    "metric": "production_units+battery_stock_units",
                    "strength": "weak",
                    "severity": 0.75,
                    "timestamp": latest_timestamp,
                    "type": "Internal"
                })

    # Multi-Source External Extraction
    external_signals = external_sensing.fetch_external_signals(db, industry=dataset_type, df_context=df)

    # Calculate Future Impact
    future_impact = compute_future_impact(df, internal_signals, external_signals)

    # Update global store for /signals endpoint
    last_results["internal"] = internal_signals
    last_results["external"] = external_signals
    last_results["future_impact"] = future_impact

    return {
        "dataset_type": dataset_type,
        "internal_signals": internal_signals,
        "external_signals": external_signals,
        "future_impact": future_impact
    }

@app.get("/signals")
async def get_signals(db: Session = Depends(database.get_db)):
    return last_results

@app.post("/trigger/external")
async def trigger_external_sensing(industry: str = "Jewellery", db: Session = Depends(database.get_db)):
    """Manual trigger to scan real-time news and macro sources"""
    news_signals = external_sensing.fetch_external_signals(db, industry=industry)
    last_results["external"] = news_signals
    return {"status": "success", "message": f"Fetched {len(news_signals)} real-time signals."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
