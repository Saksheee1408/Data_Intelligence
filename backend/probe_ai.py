from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

def probe():
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        print(f"Client created. Testing simple prompt...")
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents="test"
        )
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Probe failed: {e}")

if __name__ == "__main__":
    probe()
