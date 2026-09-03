"""Test Ark vision API with small image."""
import base64
import os
import sys
import json
import httpx

API_KEY = os.environ.get("ARK_API_KEY", sys.argv[1] if len(sys.argv) > 1 else "")
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

# Load base64
b64_path = os.path.join(os.path.dirname(__file__), "..", "e2e_demo", "screenshots", "run_20260901", "source_b64.txt")
with open(b64_path, "r") as f:
    image_b64 = f.read()

print(f"Image base64: {len(image_b64)} chars")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# Test 1: Pure text call (known working)
print("\n--- Test 1: Pure text ---")
body1 = {
    "model": "doubao-seed-2-1-turbo-260628",
    "messages": [{"role": "user", "content": "Say OK"}],
    "max_tokens": 10,
}
resp = httpx.post(f"{BASE_URL}/chat/completions", headers=headers, json=body1, timeout=60)
print(f"Status: {resp.status_code}")
if resp.status_code != 200:
    print(f"Body: {resp.text[:300]}")
else:
    print(f"OK: {resp.json()['choices'][0]['message']['content']}")

# Test 2: Vision call with small JPEG
print("\n--- Test 2: Vision (65KB JPEG) ---")
body2 = {
    "model": "doubao-seed-2-1-turbo-260628",
    "messages": [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What do you see in this image? Reply in 1 sentence."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            ],
        }
    ],
    "max_tokens": 200,
}
print(f"Request body size: {len(json.dumps(body2))} chars")
resp = httpx.post(f"{BASE_URL}/chat/completions", headers=headers, json=body2, timeout=300)
print(f"Status: {resp.status_code}")
if resp.status_code != 200:
    print(f"Body: {resp.text[:500]}")
else:
    data = resp.json()
    print(f"Response: {data['choices'][0]['message']['content'][:200]}")
    print(f"Tokens: {data.get('usage', {})}")

# Test 3: Vision call with tiny inline base64 (1x1 pixel)
print("\n--- Test 3: Vision (tiny 1x1 pixel) ---")
tiny_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
body3 = {
    "model": "doubao-seed-2-1-turbo-260628",
    "messages": [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What color is this pixel?"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{tiny_b64}"}},
            ],
        }
    ],
    "max_tokens": 50,
}
resp = httpx.post(f"{BASE_URL}/chat/completions", headers=headers, json=body3, timeout=60)
print(f"Status: {resp.status_code}")
if resp.status_code != 200:
    print(f"Body: {resp.text[:300]}")
else:
    print(f"OK: {resp.json()['choices'][0]['message']['content'][:100]}")
