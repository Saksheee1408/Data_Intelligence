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
    
    # --- Phase 1: Dynamic Dataset Identification (AI) ---
    import ai_engine
    try:
        dataset_info = ai_engine.detect_dataset_type(df)
        dataset_type = dataset_info.industry
        print(f"[Phase 1] Detected industry: {dataset_type} | Metrics: {dataset_info.key_metrics}")
    except Exception as e:
        print(f"[Phase 1] AI Detection failed: {e}")
        numeric_cols = df.select_dtypes(include='number').columns.tolist()
        dataset_type = "General"
        dataset_info = ai_engine.DatasetInfo(industry=dataset_type, description="Uploaded dataset", key_metrics=numeric_cols)

    # Process Data
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
    latest_timestamp = df['date'].iloc[-1].isoformat() if 'date' in df.columns else datetime.datetime.now().isoformat()

    # --- Phase 2: Dynamic Internal Signal Extraction (AI) ---
    try:
        ai_signals = ai_engine.extract_internal_signals(df, dataset_info)
        internal_signals = [s.model_dump() for s in ai_signals]
        print(f"[Phase 2] AI extracted {len(internal_signals)} internal signals")
    except Exception as e:
        print(f"[Phase 2] AI Internal Extraction failed: {e} — using SignalEngine fallback")
        from signal_engine import SignalEngine
        cols = {
            'inventory_column': next((c for c in df.columns if any(k in c.lower() for k in ['stock', 'inv', 'inventory', 'tons', 'units', 'kg'])), None),
            'demand_column': next((c for c in df.columns if any(k in c.lower() for k in ['sales', 'demand', 'bookings', 'sold', 'cups'])), None),
            'delay_column': next((c for c in df.columns if any(k in c.lower() for k in ['delay', 'lead', 'late', 'supplier', 'hours'])), None),
            'inventory_label': dataset_info.description,
            'material_name': dataset_type
        }
        engine = SignalEngine(df, cols)
        engine_signals, _ = engine.analyze_internal_signals()
        internal_signals = []
        for s in engine_signals:
            sev_str = s.get('severity', 'Low')
            sev_num = 0.9 if sev_str == 'Critical' else 0.75 if sev_str == 'High' else 0.55 if sev_str == 'Medium' else 0.35
            internal_signals.append({
                "signal": s.get('signal'),
                "metric": s.get('metric'),
                "strength": "weak",
                "severity": sev_num,
                "timestamp": latest_timestamp,
                "type": "Internal"
            })
        print(f"[Phase 2] SignalEngine fallback found {len(internal_signals)} signals")

    print(f"[Phase 2] Total internal signals: {len(internal_signals)}")
    # --- Phase 3: Dynamic External Sensing (AI topics + RSS news) ---
    try:
        dynamic_topics = ai_engine.get_external_search_topics(dataset_info)
        print(f"[Phase 3] AI-generated topics: {dynamic_topics}")
    except Exception as e:
        print(f"[Phase 3] AI Topic Generation failed: {e}")
        # Smart keyword fallback from dataset column names
        dynamic_topics = [f"{dataset_type} supply chain", f"{dataset_type} market trends", f"{dataset_info.key_metrics[0] if dataset_info.key_metrics else dataset_type} price"]
        print(f"[Phase 3] Using keyword fallback topics: {dynamic_topics}")

    external_signals = external_sensing.fetch_external_signals(
        db,
        industry=dataset_type,
        df_context=df,
        dynamic_topics=dynamic_topics
    )
    print(f"[Phase 3] Fetched {len(external_signals)} external signals")

    # --- Phase 4: Intelligence Engine Phase (AI-Driven) ---
    builder = EvidenceBuilder(df)
    evidence = builder.build_evidence(internal_signals, external_signals)
    
    try:
        why_chain_obj = ai_engine.generate_dynamic_why_chain(evidence, industry=dataset_type)
        why_chain = why_chain_obj.model_dump()
        print(f"[Phase 4] Why chain generated: {why_chain_obj.root_cause_summary[:80]}")
        impact_obj = ai_engine.compute_dynamic_impact(evidence, why_chain_obj, industry=dataset_type)
        future_business_impact = impact_obj.model_dump()
        print(f"[Phase 4] Impact computed: {impact_obj.risk_level} risk, {impact_obj.probability_percent}% probability")
    except Exception as e:
        import traceback
        print(f"[Phase 4] AI Intelligence Engine failed: {e}")
        traceback.print_exc()
        why_gen = WhyChainGenerator(evidence)
        why_chain = why_gen.generate_10_why_chain()
        impact_eng = ImpactEngine()
        future_business_impact = impact_eng.compute_future_impact(evidence, why_chain)

    # Maintain existing response keys + Add new ones
    response_data = {
        "dataset_type": dataset_type,
        "dataset_description": dataset_info.description,
        "internal_signals": internal_signals,
        "external_signals": external_signals,
        "future_impact": future_business_impact, 
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
    import ai_engine
    
    # Create dummy dataset info for manual trigger
    dummy_info = ai_engine.DatasetInfo(industry=industry, description="Manual trigger", key_metrics=[])
    try:
        dynamic_topics = ai_engine.get_external_search_topics(dummy_info)
    except:
        dynamic_topics = None

    news_signals = external_sensing.fetch_external_signals(db, industry=industry, dynamic_topics=dynamic_topics)
    
    df_dummy = pd.DataFrame(columns=['date']) 
    builder = EvidenceBuilder(df_dummy)
    evidence = builder.build_evidence([], news_signals)
    
    try:
        why_chain_obj = ai_engine.generate_dynamic_why_chain(evidence)
        why_chain = why_chain_obj.model_dump()
        impact_obj = ai_engine.compute_dynamic_impact(evidence, why_chain_obj)
        future_business_impact = impact_obj.model_dump()
    except:
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
