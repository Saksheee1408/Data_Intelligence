import feedparser
try:
    from textblob import TextBlob
except ImportError:
    class TextBlob:
        def __init__(self, text):
            self.sentiment = type('Sentiment', (), {'polarity': 0.0})()
from sqlalchemy.orm import Session
import models
import datetime
import urllib.parse
import pandas as pd

def fetch_external_signals(db: Session, industry: str = "Jewellery", df_context: pd.DataFrame = None):
    """
    Multi-Source External Signal Extraction:
    Source 1: Google News RSS (Real-world events)
    Source 2: Contextual Macro Indicators (Trend analysis from data)
    Source 3: Industry Sentiment Analysis (Headline scoring)
    """
    
    all_signals = []

    # --- SOURCE 1 & 3: Real-Time News & Sentiment ---
    topics = {
        "Jewellery": ["Gold Price", "Jewellery Market", "Bullion Demand"],
        "ev": ["Battery Raw Materials", "EV Charging Infrastructure", "Lithium Price"]
    }
    
    active_topics = topics.get(industry, topics["Jewellery"])
    
    for topic in active_topics:
        encoded_topic = urllib.parse.quote(topic)
        rss_url = f"https://news.google.com/rss/search?q={encoded_topic}&hl=en-IN&gl=IN&ceid=IN:en"
        feed = feedparser.parse(rss_url)
        
        for entry in feed.entries[:3]: # Top 3 per topic
            headline = entry.title
            analysis = TextBlob(headline)
            sentiment = analysis.sentiment.polarity
            
            signal = {
                "signal": headline,
                "type": f"News Source ({topic})",
                "severity": "High" if sentiment < -0.2 else "Medium" if sentiment < 0.2 else "Low",
                "confidence": 0.85,
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "metric": f"Sentiment: {sentiment:.2f}"
            }
            all_signals.append(signal)

    # --- SOURCE 2: Contextual Macro Indicators (Derived from CSV) ---
    if df_context is not None:
        if industry == "Jewellery":
            # Example: Gold stock vs Sales imbalance as an Economic Indicator
            if len(df_context) >= 5:
                avg_stock = df_context['gold_stock_gm'].mean()
                latest_stock = df_context['gold_stock_gm'].iloc[-1]
                if latest_stock < avg_stock * 0.8:
                    all_signals.append({
                        "signal": "External Market Scarcity Indicator (Derived from Stock depletion)",
                        "type": "Market Macro",
                        "severity": "Medium",
                        "confidence": 0.70,
                        "timestamp": datetime.datetime.utcnow().isoformat(),
                        "metric": f"Stock Deviation: -{((avg_stock-latest_stock)/avg_stock)*100:.1f}%"
                    })
        elif industry == "ev":
            # Example: Cost volatility as an Economic Indicator
            costs = df_context['battery_cost_per_unit'].tolist()
            if len(costs) >= 5:
                cost_volatility = (max(costs[-5:]) - min(costs[-5:])) / min(costs[-5:])
                if cost_volatility > 0.05:
                    all_signals.append({
                        "signal": "Global Supply Chain Inflation (Detected from Battery Cost Volatility)",
                        "type": "Economic Macro",
                        "severity": "High",
                        "confidence": 0.75,
                        "timestamp": datetime.datetime.utcnow().isoformat(),
                        "metric": f"Volatility Index: {cost_volatility*100:.1f}%"
                    })

    return all_signals
