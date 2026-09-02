"""Test new API key with doubao-seed-1.6-vision endpoint."""
import httpx
import os
import sys

API_KEY = os.environ.get("ARK_API_KEY", "REDACTED")
MODEL = "doubao-seed-1-6-vision-250815"
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# Test 1: Simple text
print("--- Test 1: Simple text ---")
body1 = {
    "model": MODEL,
    "messages": [{"role": "user", "content": "Say OK"}],
    "max_tokens": 10,
}
resp = httpx.post(f"{BASE_URL}/chat/completions", headers=headers, json=body1, timeout=30)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"Response: {data['choices'][0]['message']['content'][:50]}")
    print(f"Tokens: {data.get('usage', {})}")
else:
    print(f"Body: {resp.text[:300]}")
