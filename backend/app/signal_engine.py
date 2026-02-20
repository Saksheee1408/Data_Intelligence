import pandas as pd
import numpy as np
from scipy.stats import zscore, linregress

class SignalEngine:
    def __init__(self, df: pd.DataFrame, config: dict):
        self.df = df
        self.config = config
        self.latest_idx = len(df) - 1

    def _calculate_trend(self, series):
        """Calculates the slope of the last 5 points to determine trend direction."""
        if len(series) < 3:
            return 0.0
        y = series[-5:].values
        x = np.arange(len(y))
        slope, _, _, _, _ = linregress(x, y)
        # Normalize slope by mean to make it percentage-like
        mean_val = np.mean(y)
        if mean_val == 0: return 0.0
        return slope / mean_val

    def _is_anomaly(self, series, threshold=2.0):
        """Detects if the latest value is a statistical anomaly (Z-Score > threshold)"""
        if len(series) < 5:
            return False, 0.0
        z_scores = zscore(series)
        latest_z = z_scores[-1]
        return abs(latest_z) > threshold, latest_z

    def analyze_internal_signals(self):
        signals = []
        focus_areas = []

        # 1. Analyze Inventory (Criticality)
        inv_col = self.config.get('inventory_column')
        if inv_col in self.df.columns:
            series = self.df[inv_col].fillna(0)
            trend = self._calculate_trend(series)
            
            # Dynamic Rule: Continuous Depletion
            if trend < -0.02: # >2% drop trend
                signals.append({
                    "signal": f"Rapid depletion in {self.config.get('inventory_label', 'Inventory')}",
                    "metric": inv_col,
                    "severity": "High" if trend < -0.05 else "Medium",
                    "type": "Internal / Efficiency",
                    "meta": {"trend_slope": trend}
                })
                focus_areas.append(f"{self.config.get('material_name')} shortage")

        # 2. Analyze Supply Chain (Delays)
        delay_col = self.config.get('delay_column')
        if delay_col in self.df.columns:
            series = self.df[delay_col].fillna(0)
            is_spike, z_val = self._is_anomaly(series)
            
            if is_spike and z_val > 0:
                signals.append({
                    "signal": f"Abnormal spike in Supplier Delays detected",
                    "metric": delay_col,
                    "severity": "High",
                    "type": "Internal / Supply Chain",
                    "meta": {"z_score": z_val}
                })
                focus_areas.append(f"{self.config.get('material_name')} logistics delay")

        # 3. Analyze Demand vs Supply (Cross-metric logic)
        demand_col = self.config.get('demand_column') # e.g., Sales or Production
        if demand_col in self.df.columns and inv_col in self.df.columns:
            demand_trend = self._calculate_trend(self.df[demand_col])
            inv_trend = self._calculate_trend(self.df[inv_col])

            # Divergence: Demand UP (+), Inventory DOWN (-)
            if demand_trend > 0.01 and inv_trend < -0.01:
                 signals.append({
                    "signal": "Demand is outpaceing Supply (Inventory Divergence)",
                    "metric": f"{demand_col} vs {inv_col}",
                    "severity": "Critical",
                    "type": "Internal / Risk",
                    "meta": {"divergence": demand_trend - inv_trend}
                })
                 focus_areas.append(f"{self.config.get('material_name')} market demand surge")

        return signals, focus_areas
