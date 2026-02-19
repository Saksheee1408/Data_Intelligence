Build the next feature: NON-HARDCODED “10-WHY Chain + Probability + Time-to-Impact” that depends ONLY on the extracted internal_signals and external_signals (and their underlying metrics/values that produced them).

STRICT RULES
- Do NOT hardcode any business conclusions, probabilities, time windows, drivers, or actions.
- Do NOT add fake data.
- Do NOT change existing UI or existing internal/external signal extraction logic.
- Only ADD a new backend module + API field(s) that the current UI can render.
- The 10-WHY chain must be dependent: WHY10 depends on WHY9, WHY9 on WHY8, … WHY2 on WHY1.
- Probability + time-to-impact MUST be computed from signal evidence (severity/confidence/trend strength/recency) and NOT fixed numbers.

INPUTS AVAILABLE
- internal_signals[]: each has (title/summary, metric_key, direction, severity_score, timestamp, supporting_stats like last_value, baseline_avg, delta_pct, slope)
- external_signals[]: each has (title/summary, category, confidence_score, sentiment(optional), timestamp, extracted_entities/keywords, evidence_count, recency_score)
If some fields are missing, compute them from the source CSV / fetched results (e.g., trend slope, delta%, rolling mean).

TASK 1 — Implement “SignalEvidenceBuilder”
Create a function:
build_evidence(internal_signals, external_signals) -> evidence

Evidence must include computed, NON-hardcoded measures:
- internal_strength = aggregate of internal severities weighted by trend magnitude (delta% + slope + persistence)
- external_strength = aggregate of external confidences weighted by evidence_count + recency + entity match
- convergence_score = how many signals point to the same theme (supply/demand/cost) using clustering by metric_key/category/entities
- reliability_score = penalize if signals are few, contradictory, or low recency
Return an evidence object with numeric scores in [0..1] normalized from actual signal stats.

TASK 2 — Implement “10-WHY Chain Generator (Dependent)”
Create:
generate_10_why_chain(evidence) -> why_chain

Rules for dependency:
- WHY1 must be a direct observation from the strongest single signal (highest contribution).
- WHY2 must explain WHY1 using the next strongest related signal (same theme).
- WHY3 must explain WHY2 by linking to another supporting signal or intermediate factor.
- Continue until WHY10 reaches an actionable root-cause summary that is strictly derived from the chain (no invented causes).
- Each WHY must reference which evidence items it used (signal_ids or metric_keys) inside a “support” field.

Output format:
why_chain = {
  "why_steps": [
    {"level": 1, "text": "...", "support": {"internal": [...], "external": [...]}},
    {"level": 2, "text": "...", "support": {...}},
    ...
    {"level": 10, "text": "...", "support": {...}}
  ],
  "themes": ["SUPPLY", "DEMAND", "COST"],              // derived from clustering
  "root_cause_summary": "..."                          // derived from WHY10 text
}

TASK 3 — Implement “Future Business Impact” (NOT HARDCODED)
Create:
compute_future_impact(evidence, why_chain) -> impact

Must compute:
1) risk_level (LOW/MEDIUM/HIGH/CRITICAL)
- Derived from a risk_score = f(internal_strength, external_strength, convergence_score, reliability_score)
- Use dynamic thresholds based on distribution (e.g., quantiles of risk_score across runs or calibrated ranges), not fixed constants.

2) probability_percent (0–100)
- Compute probability = sigmoid( a*internal_strength + b*external_strength + c*convergence - d*(1-reliability) )
- a,b,c,d are learned/calibrated from data if available; otherwise estimate from evidence weights BUT do not hardcode the final probability.
- If no training/outcome data exists, compute probability from normalized evidence scores and clearly store “method”: “evidence-weighted (no outcomes yet)”.

3) time_to_impact_days (range)
- Must be derived from recency + persistence:
  - If signals are sharply increasing recently (high slope, high recency), shorter time window.
  - If gradual changes (low slope but persistent), longer window.
- Output as {"min_days": X, "max_days": Y} computed from evidence, not fixed.

4) impacted_areas[]
- Determine from themes + metric_keys mapping:
  - SUPPLY -> procurement, supplier, inventory
  - DEMAND -> sales, bookings, customer footfall
  - COST -> procurement_cost, margin, pricing
Mapping can be rule-based but MUST be generic (not jewellery-specific hardcoded storylines).

5) key_drivers[]
- List top 3–5 drivers ranked by contribution to risk_score (signal contribution weights).

6) recommended_actions[]
- Generate actions via templates tied to impacted_areas and direction:
  - e.g., if SUPPLY risk high -> “Increase buffer inventory”, “Lock supplier lead time”, “Add alternate supplier”
  - if DEMAND surge + stock down -> “Prepare stock replenishment”, “Plan staffing”
Actions are template-based but selected dynamically by drivers (no single hardcoded final message).

Output format:
impact = {
  "risk_level": "HIGH",
  "risk_score": 0.78,
  "probability_percent": 56,
  "time_to_impact_days": {"min_days": 9, "max_days": 16},
  "impacted_areas": ["INVENTORY", "PROCUREMENT", "SALES"],
  "key_drivers": [
     {"name": "gold_stock_gm decreasing", "weight": 0.31},
     {"name": "supplier_delay_days increasing", "weight": 0.27},
     {"name": "external supply chain pressure", "weight": 0.21}
  ],
  "recommended_actions": [
     {"action": "...", "reason": "linked to driver X"},
     ...
  ],
  "explanation": {
     "one_line": "Event → Why → Impact summary generated from why_chain",
     "why_chain_ref": true
  },
  "method": {
     "probability": "evidence-weighted sigmoid",
     "time_window": "recency+persistence derived",
     "notes": "no hardcoded numbers; computed from signal evidence"
  }
}

TASK 4 — API INTEGRATION (NO UI CHANGE)
- Add a new backend endpoint OR extend the existing response to include:
  response["why_chain"] = why_chain
  response["future_business_impact"] = impact
- Keep existing response fields unchanged.

TASK 5 — VALIDATION
- If only internal signals exist (no external), still produce chain+impact using internal evidence with lower reliability.
- If only external signals exist, still produce chain+impact using external evidence with lower reliability.
- If evidence is weak/insufficient, return risk_level LOW and probability based on evidence, not default.
- Include unit tests for:
  - chain dependency ordering
  - probability changes when severity/confidence changes
  - time window shrinks when recency/slope increases

Deliverables:
- New module files: evidence_builder.py, why_chain.py, impact_engine.py
- Minimal wiring changes in existing FastAPI route/controller
- JSON outputs exactly in the formats above
