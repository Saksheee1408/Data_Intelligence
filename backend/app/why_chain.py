from typing import List, Dict, Any

class WhyChainGenerator:
    def __init__(self, evidence: Dict):
        self.evidence = evidence
        self.internal = evidence.get('internal_signals', [])
        self.external = evidence.get('external_signals', [])
        
    def generate_10_why_chain(self) -> Dict:
        # Combine all signals and rank by strength
        all_signals = []
        for s in self.internal:
            all_signals.append({**s, "source_type": "internal", "sort_key": s.get('severity', 0.5)})
        for s in self.external:
            all_signals.append({**s, "source_type": "external", "sort_key": s.get('confidence', 0.5)})
            
        all_signals.sort(key=lambda x: x['sort_key'], reverse=True)
        
        if not all_signals:
            return self._generate_empty_chain()

        steps = []
        
        # WHY 1: Direct Observation from strongest signal
        primary = all_signals[0]
        steps.append({
            "level": 1,
            "text": f"Business performance is being impacted by {primary['signal']}.",
            "support": {
                "internal": [primary['metric']] if primary['source_type'] == 'internal' else [],
                "external": [primary['signal']] if primary['source_type'] == 'external' else []
            }
        })

        # WHY 2-9: Build dependencies
        # Since we need 10 steps, and we might not have 10 signals, we will use a mix of available signals
        # and logical connectors derived from themes.
        
        themes = self._extract_themes(all_signals)
        
        for i in range(2, 10):
            if i-1 < len(all_signals):
                current = all_signals[i-1]
                prev_text = steps[-1]['text']
                text = f"This is exacerbated because {current['signal']}, which correlates with the previously observed trend."
                support = {
                    "internal": [current['metric']] if current['source_type'] == 'internal' else [],
                    "external": [current['signal']] if current['source_type'] == 'external' else []
                }
            else:
                # Fill with logical synthesis if signals run out
                theme = themes[0] if themes else "operational factors"
                text = f"Continuous pressure on {theme} leads to a compounding effect on overall business stability."
                support = {"internal": [], "external": []}
            
            steps.append({
                "level": i,
                "text": text,
                "support": support
            })

        # WHY 10: Actionable root cause summary
        final_summary = self._synthesize_root_cause(steps, themes)
        steps.append({
            "level": 10,
            "text": f"Therefore, the root cause is {final_summary}, requiring immediate strategic intervention.",
            "support": {"internal": [], "external": []}
        })

        return {
            "why_steps": steps,
            "themes": themes,
            "root_cause_summary": final_summary
        }

    def _extract_themes(self, signals: List[Dict]) -> List[str]:
        themes = []
        mapping = {
            "SUPPLY": ['stock', 'delay', 'supplier', 'lead_time'],
            "DEMAND": ['sales', 'bookings', 'demand', 'customer'],
            "COST": ['price', 'cost', 'margin', 'inflation']
        }
        for s in signals:
            combined = (str(s.get('metric', '')) + " " + str(s.get('signal', ''))).lower()
            for theme, keywords in mapping.items():
                if any(k in combined for k in keywords):
                    if theme not in themes: themes.append(theme)
        return themes

    def _synthesize_root_cause(self, steps: List[Dict], themes: List[str]) -> str:
        if not themes: return "convergence of unexpected market and internal signals"
        theme_str = " and ".join(themes[:2])
        return f"a multi-vector convergence of {theme_str} signals"

    def _generate_empty_chain(self) -> Dict:
        return {
            "why_steps": [{"level": i, "text": "Insufficient signal data to generate causal chain.", "support": {"internal":[], "external":[]}} for i in range(1, 11)],
            "themes": [],
            "root_cause_summary": "Data scarcity"
        }
