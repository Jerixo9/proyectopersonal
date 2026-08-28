import requests

try:
    res = requests.get("http://localhost:11434/api/tags", timeout=1.0)
    print(f"Status Code: {res.status_code}")
    if res.status_code == 200:
        data = res.json()
        print("Models:")
        for m in data.get("models", []):
            print(f"- {m.get('name')}")
except Exception as e:
    print(f"Error: {e}")
