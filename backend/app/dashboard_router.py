from fastapi import APIRouter, HTTPException
import time
from typing import Dict, List, Any
import datetime

router = APIRouter()

# This will be injected from main.py
# Structure: {"internal": [], "external": [], "future_impact": {}}
data_store: Dict[str, Any] = {}
app_start_time: float = time.time()

@router.get("/summary")
async def get_dashboard_summary():
    internal = data_store.get("internal", [])
    external = data_store.get("external", [])
    
    total_signals = len(internal) + len(external)
    
    # Active alerts: Severity >= Medium (0.4) or High/Critical string
    def is_active(s):
        params = s if isinstance(s, dict) else s.__dict__
        sev = params.get('severity', 0)
        if isinstance(sev, (int, float)):
            return sev >= 0.4
        return str(sev).upper() in ['MEDIUM', 'HIGH', 'CRITICAL']

    active_alerts = len([s for s in internal if is_active(s)]) + \
                   len([s for s in external if is_active(s)])
    
    # Orchestrator status (mock logic: if >0 signals, it's running)
    orchestrator_status = "Running" if total_signals > 0 else "Waiting"
    
    uptime_seconds = time.time() - app_start_time
    
    future_impact = data_store.get("future_impact", {})

    return {
        "totalSignalsMonitored": total_signals,
        "activeAlerts": active_alerts,
        "orchestratorStatus": orchestrator_status,
        "systemUptimeSeconds": uptime_seconds,
        "futureImpact": future_impact
    }

@router.get("/severity")
async def get_dashboard_severity():
    internal = data_store.get("internal", [])
    external = data_store.get("external", [])
    all_signals = internal + external
    
    high = 0
    medium = 0
    low = 0
    
    for s in all_signals:
        params = s if isinstance(s, dict) else s.__dict__
        sev = params.get('severity', 0)
        val = 0
        
        if isinstance(sev, (int, float)):
            val = sev
        elif str(sev).upper() == 'HIGH': val = 0.8
        elif str(sev).upper() == 'MEDIUM': val = 0.5
        else: val = 0.2
            
        if val >= 0.7: high += 1
        elif val >= 0.4: medium += 1
        else: low += 1
            
    return {
        "high": high,
        "medium": medium,
        "low": low
    }

@router.get("/alerts")
async def get_dashboard_alerts(limit: int = 20):
    internal = data_store.get("internal", [])
    external = data_store.get("external", [])
    future_impact = data_store.get("future_impact", {})
    
    # Normalize and combine
    # Internal signals have 'signal', 'severity', 'metric', 'timestamp'
    # External signals have 'signal', 'severity', 'confidence', 'timestamp', 'source'
    
    combined = []
    
    for s in internal:
        p = s if isinstance(s, dict) else s.__dict__
        combined.append({
            "timestamp": p.get("timestamp", datetime.datetime.now().isoformat()),
            "signalName": p.get("signal", "Unknown Signal"),
            "severity": p.get("severity", 0),
            "impactSummary": future_impact.get("risk_level", "Unknown") if future_impact else "Pending Analysis",
            "actions": "View Explanation" # Placeholder for UI action
        })
        
    for s in external:
        p = s if isinstance(s, dict) else s.__dict__
        combined.append({
            "timestamp": p.get("timestamp", datetime.datetime.now().isoformat()),
            "signalName": p.get("signal", "Unknown Signal"),
            "severity": p.get("severity", 0),
            "impactSummary": future_impact.get("risk_level", "Unknown") if future_impact else "Pending Analysis",
            "actions": "View Explanation"
        })
        
    # Sort by timestamp desc (mock timestamp sort if needed, but assuming ISO strings work)
    # Using a simple key for stability
    combined.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
    
    return combined[:limit]
