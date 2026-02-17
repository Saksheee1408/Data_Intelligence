from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import pandas as pd
import io
import uuid
import datetime
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

@app.get("/")
async def root():
    return {"message": "Weak Signal Intelligence API is running"}

@app.post("/upload/internal")
async def upload_internal_data(file: UploadFile = File(...), db: Session = Depends(database.get_db)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    
    contents = await file.read()
    df = pd.read_csv(io.BytesIO(contents))
    
    # Basic validation of columns
    required_columns = ['date', 'sales_inr', 'gold_stock_gm', 'supplier_delay_days', 'advance_bookings']
    if not all(col in df.columns for col in required_columns):
        return {
            "error": f"CSV must contain the following columns: {', '.join(required_columns)}",
            "found": list(df.columns)
        }

    # Ensure date is datetime
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')

    # Save data to database
    batch_id = str(uuid.uuid4())
    for _, row in df.iterrows():
        internal_data = models.InternalDataRow(
            date=row['date'],
            sales_inr=row['sales_inr'],
            gold_stock_gm=row['gold_stock_gm'],
            supplier_delay_days=row['supplier_delay_days'],
            advance_bookings=row['advance_bookings'],
            upload_batch_id=batch_id
        )
        db.add(internal_data)

    # Process internal signals
    signals_data = detect_internal_signals(df)
    
    # Save signals to database
    for s in signals_data:
        db_signal = models.InternalSignal(
            type=s['type'],
            signal=s['signal'],
            metric=s['metric'],
            severity=s['severity'],
            strength=s['strength'],
            timestamp=datetime.datetime.fromisoformat(s['timestamp'])
        )
        db.add(db_signal)
    
    db.commit()
    
    return {
        "filename": file.filename,
        "batch_id": batch_id,
        "rows": len(df),
        "internal_signals": signals_data
    }

@app.get("/signals")
async def get_signals(db: Session = Depends(database.get_db)):
    internal = db.query(models.InternalSignal).order_by(models.InternalSignal.timestamp.desc()).all()
    external = db.query(models.ExternalSignal).order_by(models.ExternalSignal.timestamp.desc()).all()
    return {
        "internal": internal,
        "external": external
    }

@app.post("/trigger/external")
async def trigger_external_sensing(industry: str = "Jewellery", db: Session = Depends(database.get_db)):
    """Manual trigger to scan for external signals based on industry context"""
    signals = external_sensing.fetch_external_signals(db, industry)
    return {"status": "success", "industry": industry, "detected": signals}

def detect_internal_signals(df: pd.DataFrame):
    signals = []
    
    # Case 1: Continuous Stock Drop (last 3 entries)
    if len(df) >= 3:
        last_3 = df.tail(3)
        stocks = last_3['gold_stock_gm'].tolist()
        if stocks[0] > stocks[1] > stocks[2]:
            signals.append({
                "type": "Internal",
                "signal": "Continuous Stock Drop Detected",
                "metric": f"Stock levels: {stocks[0]} -> {stocks[1]} -> {stocks[2]} grams",
                "severity": "High" if stocks[2] < 100 else "Medium",
                "timestamp": last_3['date'].iloc[-1].isoformat(),
                "strength": "Weak Signal"
            })

    # Case 2: Rising Supplier Delay
    if len(df) >= 3:
        last_3 = df.tail(3)
        delays = last_3['supplier_delay_days'].tolist()
        if delays[2] > delays[1] >= delays[0] and delays[2] > 5:
            signals.append({
                "type": "Internal",
                "signal": "Rising Supplier Delay",
                "metric": f"Delay increased to {delays[2]} days",
                "severity": "Medium",
                "timestamp": last_3['date'].iloc[-1].isoformat(),
                "strength": "Weak Signal"
            })

    # Case 3: Sudden Demand Increase (Advance Bookings)
    if len(df) >= 3:
        last_3 = df.tail(3)
        avg_prev = last_3['advance_bookings'].iloc[:2].mean()
        current = last_3['advance_bookings'].iloc[-1]
        if current > avg_prev * 1.5:
            signals.append({
                "type": "Internal",
                "signal": "Sudden Demand Spike",
                "metric": f"Bookings jumped to {current} (Previous avg: {avg_prev:.1f})",
                "severity": "High",
                "timestamp": last_3['date'].iloc[-1].isoformat(),
                "strength": "Weak Signal"
            })

    return signals

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
