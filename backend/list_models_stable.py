import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

def list_models():
    try:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        print("Listing available models with google-generativeai...")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
    except Exception as e:
        print(f"List failed: {e}")

if __name__ == "__main__":
    list_models()
