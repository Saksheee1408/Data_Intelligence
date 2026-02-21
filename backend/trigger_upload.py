import requests
import sys

# Upload the file passed as argument (or default to coffee)
filename = sys.argv[1] if len(sys.argv) > 1 else "../sample_coffee_retail.csv"

print(f"Uploading {filename} to http://localhost:8000/upload/internal...")
with open(filename, "rb") as f:
    resp = requests.post(
        "http://localhost:8000/upload/internal",
        files={"file": (filename.split("/")[-1], f, "text/csv")}
    )

print(f"\nStatus: {resp.status_code}")
try:
    data = resp.json()
    import json
    print(json.dumps(data, indent=2))
except Exception as e:
    print(resp.text[:2000])
