import feedparser
from textblob import TextBlob
from sqlalchemy.orm import Session
import models
import datetime
import urllib.parse

def fetch_external_signals(db: Session, industry: str = "Jewellery"):
    """
    Fetches real-time external signals using Google News RSS and performs sentiment analysis.
    """
    
    # Industry-specific topics for targeted sensing
    topics = {
        "Jewellery": ["Gold Price", "Jewellery Market", "Diamond Supply Chain", "Luxury Retail Trends", "Global Inflation"],
        "Retail": ["Consumer Spending", "Retail Inflation", "E-commerce Trends India"],
        "Tech": ["Semiconductor Shortage", "AI Policy Europe", "Venture Capital Tech"]
    }
    
    active_topics = topics.get(industry, topics["Jewellery"])
    detected_external_signals = []

    # Category Mapping Keywords
    categories = {
        "Economic": ["Inflation", "Rates", "Price", "Recession", "Economy", "Currency"],
        "Regulatory": ["Regulation", "Tax", "Ban", "Compliance", "Law", "Policy"],
        "Consumer": ["Consumer", "Spending", "Trend", "Demand", "Retail"],
        "Supply Chain": ["Supply", "Shortage", "Logistics", "Shipping", "Supplier", "Inventory"],
        "Technology": ["AI", "Technology", "Innovation", "Digital", "Automation"]
    }

    for topic in active_topics:
        encoded_topic = urllib.parse.quote(topic)
        rss_url = f"https://news.google.com/rss/search?q={encoded_topic}&hl=en-IN&gl=IN&ceid=IN:en"
        
        feed = feedparser.parse(rss_url)
        
        # Take the top 3-5 entries per topic to avoid noise
        for entry in feed.entries[:5]:
            headline = entry.title
            source = entry.source.get('title', 'Unknown Source')
            
            # 1. Deduplication: Check if this headline exists in the last 24 hours
            existing = db.query(models.ExternalSignal).filter(
                models.ExternalSignal.signal == headline,
                models.ExternalSignal.timestamp >= (datetime.datetime.utcnow() - datetime.timedelta(days=1))
            ).first()
            
            if existing:
                continue

            # 2. Sentiment Analysis
            analysis = TextBlob(headline)
            sentiment_score = analysis.sentiment.polarity # Range [-1, 1]
            
            # Determine Severity based on sentiment and keyword presence
            severity = "Low"
            if sentiment_score < -0.1:
                severity = "High" if sentiment_score < -0.4 else "Medium"
            elif sentiment_score > 0.4:
                severity = "Medium" # Opportunities can also be significant signals

            # 3. Classification
            signal_type = "External"
            for cat, keywords in categories.items():
                if any(kw.lower() in headline.lower() for kw in keywords):
                    signal_type = f"External ({cat})"
                    break

            # 4. Save to DB
            signal = models.ExternalSignal(
                type=signal_type,
                source=source,
                signal=headline,
                metric=f"Sentiment: {sentiment_score:.2f} ({'Negative' if sentiment_score < 0 else 'Positive' if sentiment_score > 0 else 'Neutral'})",
                severity=severity,
                confidence=0.85, # Base confidence for RSS verified news
                timestamp=datetime.datetime.utcnow()
            )
            db.add(signal)
            detected_external_signals.append({
                "type": signal_type,
                "signal": headline,
                "severity": severity,
                "timestamp": signal.timestamp.isoformat()
            })

    db.commit()
    return detected_external_signals
