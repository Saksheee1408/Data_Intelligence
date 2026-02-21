from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

def list_models():
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        print("Listing available models...")
        for model in client.models.list():
            print(f"- {model.name}")
    except Exception as e:
        print(f"List failed: {e}")

if __name__ == "__main__":
    list_models()
