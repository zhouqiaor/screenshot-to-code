"""Test Ark API connectivity."""
import os
import sys
import httpx

API_KEY = os.environ.get("ARK_API_KEY", sys.argv[1] if len(sys.argv) > 1 else "")
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

print(f"API Key: {API_KEY[:20]}...{API_KEY[-10:]}")
print(f"Base URL: {BASE_URL}")

# Test 1: Simple text call
print("\n--- Test 1: Simple text call ---")
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}
body = {
    "model": "doubao-seed-2-1-turbo-260628",
    "messages": [{"role": "user", "content": "Say hello in 3 words"}],
    "max_tokens": 50,
}
try:
    resp = httpx.post(f"{BASE_URL}/chat/completions", headers=headers, json=body, timeout=30)
    print(f"Status: {resp.status_code}")
    print(f"Headers: {dict(resp.headers)}")
    if resp.status_code != 200:
        print(f"Body: {resp.text[:500]}")
    else:
        import json
        data = resp.json()
        print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
except Exception as e:
    print(f"Error: {e}")

# Test 2: doubao-seed-evolving
print("\n--- Test 2: doubao-seed-evolving ---")
body2 = {
    "model": "doubao-seed-evolving",
    "messages": [{"role": "user", "content": "Say hello"}],
    "max_tokens": 50,
}
try:
    resp = httpx.post(f"{BASE_URL}/chat/completions", headers=headers, json=body2, timeout=30)
    print(f"Status: {resp.status_code}")
    if resp.status_code != 200:
        print(f"Body: {resp.text[:500]}")
    else:
        import json
        data = resp.json()
        print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
except Exception as e:
    print(f"Error: {e}")

# Test 3: Try with x-api-key header
print("\n--- Test 3: x-api-key header ---")
headers3 = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json",
}
try:
    resp = httpx.post(f"{BASE_URL}/chat/completions", headers=headers3, json=body, timeout=30)
    print(f"Status: {resp.status_code}")
    if resp.status_code != 200:
        print(f"Body: {resp.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
