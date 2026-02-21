import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'app'))

import pandas as pd
import ai_engine
from dotenv import load_dotenv

load_dotenv()

def test_ai():
    print("Testing AI Engine (Stable SDK)...")
    df = pd.read_csv('../dummy_fertilizer_sales_dataset.csv')
    
    try:
        print("\n1. Testing detect_dataset_type...")
        info = ai_engine.detect_dataset_type(df)
        print(f"Detected: {info.industry}")
        print(f"Metrics: {info.key_metrics}")
        
        print("\n2. Testing extract_internal_signals...")
        signals = ai_engine.extract_internal_signals(df, info)
        print(f"Extracted {len(signals)} signals.")
        for s in signals[:2]:
            print(f"- {s.signal} ({s.metric})")

        print("\n3. Testing get_external_search_topics...")
        topics = ai_engine.get_external_search_topics(info)
        print(f"Topics: {topics}")

    except Exception as e:
        print(f"\nAI Engine Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ai()
