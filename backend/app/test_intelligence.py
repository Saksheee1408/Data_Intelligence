import unittest
import pandas as pd
import datetime
from evidence_builder import EvidenceBuilder
from why_chain import WhyChainGenerator
from impact_engine import ImpactEngine

class TestIntelligenceEngine(unittest.TestCase):
    def setUp(self):
        # Create a dummy dataframe
        dates = [datetime.datetime(2026, 2, i) for i in range(1, 11)]
        self.df = pd.DataFrame({
            'date': dates,
            'gold_stock_gm': [1000, 950, 900, 850, 800, 750, 700, 650, 600, 550],
            'sales_inr': [100, 110, 105, 120, 115, 130, 125, 140, 135, 150]
        })

    def test_chain_dependency_ordering(self):
        internal_signals = [{"signal": "Stock falling", "metric": "gold_stock_gm", "severity": 0.8}]
        builder = EvidenceBuilder(self.df)
        evidence = builder.build_evidence(internal_signals, [])
        
        why_gen = WhyChainGenerator(evidence)
        chain = why_gen.generate_10_why_chain()
        
        self.assertEqual(len(chain['why_steps']), 10)
        for i in range(len(chain['why_steps'])):
            self.assertEqual(chain['why_steps'][i]['level'], i + 1)
        
        # Check if first WHY is about stock falling
        self.assertIn("Stock falling", chain['why_steps'][0]['text'])

    def test_probability_sensitivity(self):
        # Case 1: Low severity
        internal_low = [{"signal": "Minor dip", "metric": "gold_stock_gm", "severity": 0.3}]
        builder = EvidenceBuilder(self.df)
        evidence_low = builder.build_evidence(internal_low, [])
        impact_low = ImpactEngine().compute_future_impact(evidence_low, {"themes": ["SUPPLY"]})
        
        # Case 2: High severity (Multiple internal + external signals)
        internal_high = [
            {"signal": "Major crash", "metric": "gold_stock_gm", "severity": 0.9},
            {"signal": "Critical delay", "metric": "sales_inr", "severity": 0.85},
            {"signal": "Market panic", "metric": "gold_stock_gm", "severity": 0.9}
        ]
        external_high = [
            {"signal": "Global Supply Disruption", "type": "SUPPLY", "confidence": 0.9},
            {"signal": "Market Crash Rumors", "type": "COST", "confidence": 0.85}
        ]
        evidence_high = builder.build_evidence(internal_high, external_high)
        impact_high = ImpactEngine().compute_future_impact(evidence_high, {"themes": ["SUPPLY", "COST", "DEMAND"]})
        
        self.assertGreater(impact_high['probability_percent'], impact_low['probability_percent'])
        self.assertIn(impact_high['risk_level'], ["HIGH", "CRITICAL"])

    def test_time_window_slope_dependency(self):
        # Case 1: Slow decline
        df_slow = self.df.copy()
        df_slow['gold_stock_gm'] = [1000, 995, 990, 985, 980, 975, 970, 965, 960, 955]
        evidence_slow = EvidenceBuilder(df_slow).build_evidence([{"signal": "Decline", "metric": "gold_stock_gm", "severity": 0.5}], [])
        impact_slow = ImpactEngine().compute_future_impact(evidence_slow, {"themes": ["SUPPLY"]})
        
        # Case 2: Sharp decline
        df_sharp = self.df.copy()
        df_sharp['gold_stock_gm'] = [1000, 900, 800, 700, 600, 500, 400, 300, 200, 100]
        evidence_sharp = EvidenceBuilder(df_sharp).build_evidence([{"signal": "Decline", "metric": "gold_stock_gm", "severity": 0.5}], [])
        impact_sharp = ImpactEngine().compute_future_impact(evidence_sharp, {"themes": ["SUPPLY"]})
        
        # Sharper decline should have a shorter (earlier) min_days
        self.assertLessEqual(impact_sharp['time_to_impact_days']['min_days'], impact_slow['time_to_impact_days']['min_days'])

if __name__ == '__main__':
    unittest.main()
