from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import pandas as pd
import io
import uuid
import datetime
import asyncio
import models, database

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
last_results = {"internal": [], "external": []}

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
    external_signals = []

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

        # External-like Derived Jewellery Logic (last 5 rows)
        if len(df) >= 5:
            last5 = df.tail(5)
            # a) Supplier delay trend
            delays5 = last5['supplier_delay_days'].tolist()
            if delays5[-1] > sum(delays5)/5: # Simple trend indicator
                external_signals.append({
                    "signal": "Supply chain pressure increasing (delivery delays rising)",
                    "dimension": "supply_chain",
                    "confidence": 0.65,
                    "timestamp": latest_timestamp,
                    "type": "External (Supply Chain)", 
                    "severity": "Medium",
                    "metric": f"Last 5-day Avg: {sum(delays5)/5:.1f}"
                })
            # b) Sales momentum
            sales = df['sales_inr'].tolist()
            prev5_avg = sum(sales[-10:-5]) / 5 if len(sales) >= 10 else sales[0]
            curr5_avg = sum(sales[-5:]) / 5
            if prev5_avg > 0 and (prev5_avg - curr5_avg) / prev5_avg > 0.08:
                external_signals.append({
                    "signal": "Demand-side weakness forming (sales momentum declining)",
                    "dimension": "consumer_behavior",
                    "confidence": 0.60,
                    "timestamp": latest_timestamp,
                    "type": "External (Consumer)",
                    "severity": "Medium",
                    "metric": f"Drop: {((prev5_avg - curr5_avg)/prev5_avg)*100:.1f}%"
                })
            # c) Demand spike risk
            if len(df) >= 3:
                last3 = df.tail(3)
                if last3['advance_bookings'].iloc[-1] > last3['advance_bookings'].iloc[0] and \
                   last3['gold_stock_gm'].iloc[-1] < last3['gold_stock_gm'].iloc[0]:
                    external_signals.append({
                        "signal": "Upcoming demand spike risk with limited supply",
                        "dimension": "economic",
                        "confidence": 0.70,
                        "timestamp": latest_timestamp,
                        "type": "External (Economic)",
                        "severity": "High",
                        "metric": "Bookings Up / Stock Down"
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

        # External-like Derived EV Logic (last 5 rows)
        if len(df) >= 5:
            last5 = df.tail(5)
            # a) Input cost pressure
            costs = last5['battery_cost_per_unit'].tolist()
            cost_increase = (costs[-1] - costs[0]) / costs[0] if costs[0] > 0 else 0
            if cost_increase >= 0.05:
                external_signals.append({
                    "signal": "Input cost pressure rising (battery cost increasing)",
                    "dimension": "economic",
                    "confidence": 0.70,
                    "timestamp": latest_timestamp,
                    "type": "External (Economic)",
                    "severity": "High",
                    "metric": f"Increase: {cost_increase*100:.1f}%"
                })
            # b) Logistics risk
            leads5 = last5['supplier_lead_time_days'].tolist()
            if leads5[-1] > sum(leads5)/5:
                external_signals.append({
                    "signal": "Logistics / supplier disruption risk increasing",
                    "dimension": "supply_chain",
                    "confidence": 0.65,
                    "timestamp": latest_timestamp,
                    "type": "External (Supply Chain)",
                    "severity": "Medium",
                    "metric": f"Lead Time: {leads5[-1]} days"
                })
            # c) Margin risk
            if last5['production_units'].iloc[-1] > last5['production_units'].iloc[0] and \
               last5['battery_cost_per_unit'].iloc[-1] > last5['battery_cost_per_unit'].iloc[0]:
                external_signals.append({
                    "signal": "Margin risk forming (higher input cost during scaling)",
                    "dimension": "economic",
                    "confidence": 0.60,
                    "timestamp": latest_timestamp,
                    "type": "External (Economic)",
                    "severity": "Medium",
                    "metric": "Prod Up / Cost Up"
                })

    # Update global store for /signals endpoint
    last_results["internal"] = internal_signals
    last_results["external"] = external_signals

    return {
        "dataset_type": dataset_type,
        "internal_signals": internal_signals,
        "external_signals": external_signals
    }

@app.get("/signals")
async def get_signals(db: Session = Depends(database.get_db)):
    return last_results

@app.post("/trigger/external")
async def trigger_external_sensing(industry: str = "Jewellery", db: Session = Depends(database.get_db)):
    """Manual trigger to scan (Mocked for CSV-only version)"""
    return {"status": "success", "message": "Derived signals updated from CSV context."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
