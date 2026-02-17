import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
import models
import datetime
import random

def fetch_external_signals(db: Session, industry: str = "Jewellery"):
    """
    Fetches external context (News/Trends) and detects weak signals.
    In a real app, this would use SerpAPI or specialized news APIs.
    For this MVP, we simulate targeted sensing based on industry keywords.
    """
    
    # Industry-specific keywords for targeted sensing
    keywords = {
        "Jewellery": ["gold prices", "diamond supply chain", "luxury market trends", "consumer gold demand"],
        "Retail": ["consumer spending", "retail inflation", "e-commerce trends"],
        "Tech": ["semiconductor shortage", "AI policy", "startup funding"]
    }
    
    active_keywords = keywords.get(industry, keywords["Jewellery"])
    detected_external_signals = []

    # Simulation of targeted news sensing
    # In a full live system, this would call a real News API
    headlines = [
        f"Central banks increase {active_keywords[0]} reserves",
        f"New regulations in {industry} sector globally",
        f"Logistics disruptions impact {active_keywords[1]}",
        f"Shifting patterns in {active_keywords[2]}",
        f"Currency volatility affects {industry} imports"
    ]

    for title in headlines:
        # Simple logic: Every 'news' item is analyzed as a potential weak signal
        # Real logic would use NLP/LLM to score confidence
        severity = random.choice(["Low", "Medium", "High"])
        
        signal = models.ExternalSignal(
            type="External",
            source="Global News Feed",
            signal=title,
            metric=f"Sentiment: {random.choice(['Stable', 'Nervous', 'Bullish'])}",
            severity=severity,
            confidence=random.uniform(0.6, 0.9),
            timestamp=datetime.datetime.utcnow()
        )
        db.add(signal)
        detected_external_signals.append({
            "type": "External",
            "signal": title,
            "severity": severity,
            "timestamp": signal.timestamp.isoformat()
        })

    db.commit()
    return detected_external_signals
