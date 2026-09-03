"""Test doubao-seed-1.6-vision with all possible endpoint ID formats."""
import httpx
import json

API_KEY = os.environ.get("ARK_API_KEY", "REDACTED")
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

body_template = {
    "messages": [{"role": "user", "content": "Say OK"}],
    "max_tokens": 10,
    "stream": False,
}

# Try ALL possible formats
model_ids = [
    # The exact string user provided
    "doubao-seed-1-6-vision-250815",
    # With ep- prefix
    "ep-doubao-seed-1-6-vision-250815",
    # Various name formats
    "doubao-seed-1.6-vision-250815",
    "doubao-seed-1-6-vision",
    "doubao-1-6-vision-250815",
    "doubao-seed-1.6-vision",
    # Maybe it's a custom endpoint with different naming
    "doubao_seed_1_6_vision_250815",
    "Doubao-Seed-1.6-vision",
    "Doubao-Seed-1-6-vision",
    # Volcano sometimes uses date suffix differently
    "doubao-seed-1-6-vision-20250815",
    "doubao-seed-1-6-vision-250815-250815",
]

print(f"Testing {len(model_ids)} formats with new key")
print("=" * 80)

for mid in model_ids:
    body = {**body_template, "model": mid}
    try:
        resp = httpx.post(f"{BASE_URL}/chat/completions", headers=headers, json=body, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            usage = data.get("usage", {})
            content = data["choices"][0]["message"]["content"][:30]
            print(f"  OK   {mid:50s} tok={usage.get('prompt_tokens',0)}+{usage.get('completion_tokens',0)}  \"{content}\"")
        else:
            try:
                err = resp.json().get("error", {}).get("code", "")[:40]
            except Exception:
                err = f"HTTP{resp.status_code}"
            print(f"  FAIL {mid:50s} {err}")
    except Exception as e:
        print(f"  ERR  {mid:50s} {str(e)[:40]}")

# Also check: maybe the user's API key doesn't have access to this model
# Let's list available models via the models endpoint
print()
print("--- Checking /models endpoint ---")
try:
    resp = httpx.get(f"{BASE_URL}/models", headers=headers, timeout=15)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        models = data.get("data", [])
        print(f"Available models: {len(models)}")
        for m in models[:20]:
            print(f"  {m.get('id', 'unknown')}")
    else:
        print(f"Body: {resp.text[:300]}")
except Exception as e:
    print(f"Error: {e}")
