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
from evidence_builder import EvidenceBuilder
from why_chain import WhyChainGenerator
from impact_engine import ImpactEngine

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
import models, database, external_sensing, dashboard_router

# ... (rest imports)

# Simple global store for demo (replace with DB query in production)
last_results = {"internal": [], "external": [], "future_impact": {}}

# Inject shared state into dashboard router
dashboard_router.data_store = last_results

app.include_router(dashboard_router.router, prefix="/api/dashboard", tags=["dashboard"])


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

    # --- Intelligence Engine Phase ---
    builder = EvidenceBuilder(df)
    evidence = builder.build_evidence(internal_signals, external_signals)
    
    why_gen = WhyChainGenerator(evidence)
    why_chain = why_gen.generate_10_why_chain()
    
    impact_eng = ImpactEngine()
    future_business_impact = impact_eng.compute_future_impact(evidence, why_chain)

    # Maintain existing response keys + Add new ones
    response_data = {
        "dataset_type": dataset_type,
        "internal_signals": internal_signals,
        "external_signals": external_signals,
        "future_impact": future_business_impact, # existing key mapping to new engine
        "why_chain": why_chain,
        "future_business_impact": future_business_impact
    }

    # Update global store for /signals endpoint
    last_results["internal"] = internal_signals
    last_results["external"] = external_signals
    last_results["future_impact"] = future_business_impact
    last_results["why_chain"] = why_chain
    last_results["future_business_impact"] = future_business_impact

    return response_data

@app.get("/signals")
async def get_signals(db: Session = Depends(database.get_db)):
    return last_results

@app.post("/trigger/external")
async def trigger_external_sensing(industry: str = "Jewellery", db: Session = Depends(database.get_db)):
    """Manual trigger to scan real-time news and macro sources"""
    news_signals = external_sensing.fetch_external_signals(db, industry=industry)
    
    # Run intelligence engine even with zero internal signals
    # We pass an empty DF or one from the last successful upload if available
    # For now, we'll try to use a dummy or empty DF if no context exists
    df_dummy = pd.DataFrame(columns=['date']) 
    
    builder = EvidenceBuilder(df_dummy)
    evidence = builder.build_evidence([], news_signals)
    
    why_gen = WhyChainGenerator(evidence)
    why_chain = why_gen.generate_10_why_chain()
    
    impact_eng = ImpactEngine()
    future_business_impact = impact_eng.compute_future_impact(evidence, why_chain)

    last_results["external"] = news_signals
    last_results["future_impact"] = future_business_impact
    last_results["why_chain"] = why_chain
    last_results["future_business_impact"] = future_business_impact
    
    return {
        "status": "success", 
        "message": f"Fetched {len(news_signals)} real-time signals.",
        "external_signals": news_signals,
        "future_impact": future_business_impact,
        "why_chain": why_chain
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
