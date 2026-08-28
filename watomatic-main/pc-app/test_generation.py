import requests

payload = {
    "model": "llama3.1",
    "messages": [{"role": "user", "content": "hola"}],
    "stream": False
}

try:
    res = requests.post("http://localhost:11434/api/chat", json=payload, timeout=5)
    print(f"Status Code: {res.status_code}")
    print(f"Response: {res.text[:200]}")
except Exception as e:
    print(f"Error: {e}")
