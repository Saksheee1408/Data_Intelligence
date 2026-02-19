import pandas as pd
import numpy as np
import datetime
from typing import List, Dict, Any

class EvidenceBuilder:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.latest_timestamp = df['date'].iloc[-1] if 'date' in df.columns else datetime.datetime.now()

    def build_evidence(self, internal_signals: List[Dict], external_signals: List[Dict]) -> Dict:
        # Enrich internal signals with stats from DF if not present
        enriched_internal = []
        for signal in internal_signals:
            metric = signal.get('metric')
            if metric and metric in self.df.columns:
                stats = self._compute_metric_stats(metric)
                signal.update(stats)
            enriched_internal.append(signal)

        # Compute Strengths
        internal_strength = self._compute_internal_strength(enriched_internal)
        external_strength = self._compute_external_strength(external_signals)
        
        # Convergence and Reliability
        convergence = self._compute_convergence(enriched_internal, external_signals)
        reliability = self._compute_reliability(enriched_internal, external_signals)

        evidence = {
            "internal_signals": enriched_internal,
            "external_signals": external_signals,
            "internal_strength": internal_strength,
            "external_strength": external_strength,
            "convergence_score": convergence,
            "reliability_score": reliability,
            "timestamp": self.latest_timestamp.isoformat() if hasattr(self.latest_timestamp, 'isoformat') else str(self.latest_timestamp)
        }
        return evidence

    def _compute_metric_stats(self, metric: str) -> Dict:
        series = self.df[metric]
        if len(series) < 2:
            return {"delta_pct": 0, "slope": 0, "last_value": series.iloc[-1] if not series.empty else 0}
        
        last_val = series.iloc[-1]
        prev_val = series.iloc[-2]
        delta_pct = (last_val - prev_val) / (prev_val if prev_val != 0 else 1)
        
        # Simple slope over last 5 points
        short_window = series.tail(5)
        if len(short_window) > 1:
            slope = (short_window.iloc[-1] - short_window.iloc[0]) / (len(short_window) - 1)
        else:
            slope = 0
            
        return {
            "last_value": float(last_val),
            "delta_pct": float(delta_pct),
            "slope": float(slope),
            "persistence": self._compute_persistence(series)
        }

    def _compute_persistence(self, series: pd.Series) -> float:
        # How many consecutive days same direction
        if len(series) < 2: return 0
        diffs = series.diff().dropna()
        if diffs.empty: return 0
        
        last_dir = 1 if diffs.iloc[-1] >= 0 else -1
        count = 0
        for val in reversed(diffs.tolist()):
            current_dir = 1 if val >= 0 else -1
            if current_dir == last_dir:
                count += 1
            else:
                break
        return min(count / 10.0, 1.0) # Normalize to 1.0

    def _compute_internal_strength(self, signals: List[Dict]) -> float:
        if not signals: return 0
        weights = []
        for s in signals:
            severity = s.get('severity', 0.5)
            # Weight by persistence and magnitude
            mag = min(abs(s.get('delta_pct', 0)) * 5, 1.0) # 20% delta is max weight
            persist = s.get('persistence', 0.5)
            weights.append(severity * 0.5 + mag * 0.3 + persist * 0.2)
        return float(np.mean(weights))

    def _compute_external_strength(self, signals: List[Dict]) -> float:
        if not signals: return 0
        scores = []
        for s in signals:
            conf = s.get('confidence', 0.5)
            # Recency factor (simplified)
            scores.append(conf)
        return float(np.mean(scores)) if scores else 0

    def _compute_convergence(self, internal: List[Dict], external: List[Dict]) -> float:
        # Clustering by "theme"
        themes = self._get_themes(internal, external)
        if not themes: return 0
        
        # How many signals share the dominant theme
        theme_counts = {}
        for t in themes:
            theme_counts[t] = theme_counts.get(t, 0) + 1
        
        max_overlap = max(theme_counts.values()) if theme_counts else 0
        total_signals = len(internal) + len(external)
        return float(max_overlap / total_signals) if total_signals > 0 else 0

    def _compute_reliability(self, internal: List[Dict], external: List[Dict]) -> float:
        total_count = len(internal) + len(external)
        if total_count == 0: return 0
        
        # Penalty for few signals
        count_score = min(total_count / 5.0, 1.0)
        
        # Penalty for low recency (if we had actual timestamps to compare, for now assume high)
        recency_score = 0.9 
        
        # Penalty for low confidence/severity
        avg_quality = np.mean([s.get('severity', 0.5) for s in internal] + [s.get('confidence', 0.5) for s in external])
        
        return float(count_score * 0.4 + recency_score * 0.3 + avg_quality * 0.3)

    def _get_themes(self, internal: List[Dict], external: List[Dict]) -> List[str]:
        themes = []
        # Basic mapping
        supply_keywords = ['stock', 'delay', 'lead_time', 'supplier', 'supply']
        demand_keywords = ['sales', 'bookings', 'demand', 'customer', 'footfall']
        cost_keywords = ['cost', 'price', 'margin', 'inflation']
        
        for s in internal:
            metric = str(s.get('metric', '')).lower()
            signal_text = str(s.get('signal', '')).lower()
            combined = metric + " " + signal_text
            
            if any(k in combined for k in supply_keywords): themes.append("SUPPLY")
            elif any(k in combined for k in demand_keywords): themes.append("DEMAND")
            elif any(k in combined for k in cost_keywords): themes.append("COST")
            else: themes.append("UNKNOWN")
            
        for s in external:
            signal_text = str(s.get('signal', '')).lower()
            category = str(s.get('type', '')).lower() # backend uses 'type' for external signals often
            combined = signal_text + " " + category
            
            if any(k in combined for k in supply_keywords): themes.append("SUPPLY")
            elif any(k in combined for k in demand_keywords): themes.append("DEMAND")
            elif any(k in combined for k in cost_keywords): themes.append("COST")
            else: themes.append("UNKNOWN")
            
        return themes
