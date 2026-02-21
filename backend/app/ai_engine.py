import os
import json
import time
import logging
import pandas as pd
from typing import List, Dict, Any
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Groq client using OpenAI-compatible API
client = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
MODEL_NAME = "llama-3.3-70b-versatile"
logger.info(f"AI Engine initialized with Groq model: {MODEL_NAME}")

# --- Pydantic Models ---

class DatasetInfo(BaseModel):
    industry: str
    description: str
    key_metrics: List[str]

class InternalSignal(BaseModel):
    signal: str
    metric: str
    strength: str
    severity: float
    timestamp: str
    type: str

class WhyStep(BaseModel):
    level: int
    text: str
    support: Dict[str, List[str]]

class WhyChainResponse(BaseModel):
    why_steps: List[WhyStep]
    themes: List[str]
    root_cause_summary: str

class ImpactResponse(BaseModel):
    risk_level: str
    risk_score: float
    probability_percent: int
    time_to_impact_days: Dict[str, int]
    impacted_areas: List[str]
    key_drivers: List[Dict[str, Any]]
    recommended_actions: List[Dict[str, str]]
    explanation: Dict[str, Any]


def _call_groq(system_prompt: str, user_prompt: str, retries: int = 3) -> str:
    """Unified Groq API call with JSON mode and retry on rate limits."""
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            return response.choices[0].message.content
        except Exception as e:
            err_str = str(e)
            logger.warning(f"Groq attempt {attempt+1} failed: {err_str[:150]}")
            if attempt < retries - 1:
                wait = 2 ** attempt * 2
                logger.info(f"Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise e


def detect_dataset_type(df: pd.DataFrame) -> DatasetInfo:
    """Detect industry and key metrics from CSV structure."""
    columns = list(df.columns)
    sample = df.head(5).to_dict(orient='records')
    logger.info(f"[Phase 1] Detecting dataset type. Columns: {columns}")

    system = "You are a data analyst. Respond only with valid JSON."
    user = f"""Analyze this CSV and identify the industry/business domain.
Columns: {columns}
Sample rows: {json.dumps(sample, default=str)}

Return JSON:
{{
  "industry": "<specific industry, e.g. Fertilizer Agriculture, Coffee Retail, Electric Vehicles>",
  "description": "<1 sentence about the business>",
  "key_metrics": ["<most supply-chain relevant column names>"]
}}"""

    raw = _call_groq(system, user)
    return DatasetInfo.model_validate_json(raw)


def extract_internal_signals(df: pd.DataFrame, dataset_info: DatasetInfo) -> List[InternalSignal]:
    """AI-based weak signal extraction from numerical trends."""
    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    data_summary = df[numeric_cols].tail(15).to_dict(orient='records')
    latest_date = str(df['date'].iloc[-1]) if 'date' in df.columns else "2026-01-01"
    logger.info(f"[Phase 2] Extracting internal signals for: {dataset_info.industry}")

    system = "You are a Weak Signal Intelligence expert. Respond only with valid JSON."
    user = f"""Industry: {dataset_info.industry}
Description: {dataset_info.description}

Analyze these recent data rows for subtle trends and anomalies (weak signals):
{json.dumps(data_summary, default=str)}

Focus on: depletion trends, sudden spikes, demand-supply divergence, rising delays.

Return JSON:
{{
  "signals": [
    {{
      "signal": "<clear descriptive name of the signal>",
      "metric": "<column name involved>",
      "strength": "<Weak|Medium|Strong>",
      "severity": <0.0 to 1.0>,
      "timestamp": "{latest_date}",
      "type": "Internal"
    }}
  ]
}}"""

    raw = _call_groq(system, user)
    data = json.loads(raw)
    signals_list = data.get('signals', [])
    return [InternalSignal(**s) for s in signals_list]


def get_external_search_topics(dataset_info: DatasetInfo) -> List[str]:
    """Generate industry-specific news search topics."""
    logger.info(f"[Phase 3] Generating external topics for: {dataset_info.industry}")

    system = "You are a market intelligence analyst. Respond only with valid JSON."
    user = f"""For the '{dataset_info.industry}' industry with key metrics {dataset_info.key_metrics},
generate exactly 4 specific Google News search queries to detect macro-economic or supply chain risks.
Make them industry-specific (NOT generic phrases like 'supply chain disruption').

Return JSON:
{{
  "topics": ["<topic 1>", "<topic 2>", "<topic 3>", "<topic 4>"]
}}"""

    raw = _call_groq(system, user)
    data = json.loads(raw)
    topics = data.get('topics', [])
    result = [t.get('topic', str(t)) if isinstance(t, dict) else str(t) for t in topics]
    logger.info(f"[Phase 3] Generated topics: {result}")
    return result


def generate_dynamic_why_chain(evidence: Dict, industry: str = "General") -> WhyChainResponse:
    """Generate a 10-level Why Chain for the detected signals."""
    internal = evidence.get('internal_signals', [])
    external = evidence.get('external_signals', [])
    logger.info(f"[Phase 4] Generating why chain for {industry}: {len(internal)} internal, {len(external)} external signals")

    internal_summary = json.dumps(
        [{'signal': s.get('signal'), 'metric': s.get('metric'), 'severity': s.get('severity')} for s in internal],
        default=str
    )
    external_summary = json.dumps(
        [{'signal': s.get('signal'), 'type': s.get('type')} for s in external],
        default=str
    )

    system = "You are a root-cause analysis expert. Respond only with valid JSON."
    user = f"""Industry: {industry}

Internal operational signals detected:
{internal_summary}

External market signals detected:
{external_summary}

Generate a 10-level 'Why Chain' — each level explains WHY the previous situation happened.
Be specific to the {industry} industry. Make it logical and causal, not generic.

Return JSON:
{{
  "why_steps": [
    {{"level": 1, "text": "<specific observation for {industry}>", "support": {{"internal": ["<metric>"], "external": []}}}},
    {{"level": 2, "text": "<why level 1 is happening>", "support": {{"internal": [], "external": ["<signal>"]}}}}
  ],
  "themes": ["<SUPPLY|DEMAND|COST|LOGISTICS|QUALITY>"],
  "root_cause_summary": "<one sentence identifying the ultimate root cause>"
}}"""

    raw = _call_groq(system, user)
    return WhyChainResponse.model_validate_json(raw)


def compute_dynamic_impact(evidence: Dict, why_chain: WhyChainResponse, industry: str = "General") -> ImpactResponse:
    """Compute business impact, risk level, and recommended actions."""
    logger.info(f"[Phase 4] Computing business impact for {industry}")

    system = "You are a business risk analyst. Respond only with valid JSON."
    user = f"""Industry: {industry}
Root cause: {why_chain.root_cause_summary}
Themes: {why_chain.themes}
Internal signal strength: {evidence.get('internal_strength', 0):.2f}
External signal strength: {evidence.get('external_strength', 0):.2f}
Convergence score: {evidence.get('convergence_score', 0):.2f}

Assess the business impact and generate recommended actions specific to {industry}.

Return JSON:
{{
  "risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",
  "risk_score": <0.0-1.0>,
  "probability_percent": <0-100>,
  "time_to_impact_days": {{"min_days": <int>, "max_days": <int>}},
  "impacted_areas": ["<PROCUREMENT|SALES|LOGISTICS|PRODUCTION|FINANCE>"],
  "key_drivers": [{{"name": "<driver name>", "weight": <0.0-1.0>}}],
  "recommended_actions": [{{"action": "<specific action for {industry}>", "reason": "<why this helps>"}}],
  "explanation": {{"one_line": "<one sentence summary of the risk situation>"}}
}}"""

    raw = _call_groq(system, user)
    return ImpactResponse.model_validate_json(raw)
