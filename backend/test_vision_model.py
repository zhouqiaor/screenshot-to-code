"""
Test doubao-seed-1-6-vision-250815 with new API key.
Try multiple model ID variants and endpoint patterns.
"""
import httpx
import json
import time
import sys

API_KEY = os.environ.get("ARK_API_KEY", "REDACTED")
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

# Try all possible model ID variants
MODEL_VARIANTS = [
    "doubao-seed-1-6-vision-250815",
    "doubao-seed-1.6-vision-250815",
    "doubao-seed-16-vision-250815",
    "doubao-1-6-vision-250815",
    "doubao-seed-1-6-vision",
    # Also try the working model for reference
    "doubao-seed-2-1-turbo-260628",
]

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

print("=" * 70)
print("Testing doubao-seed-1-6-vision-250815 variants")
print(f"API Key: {API_KEY[:20]}...")
print("=" * 70)

results = []

client = httpx.Client(timeout=30.0)

for model in MODEL_VARIANTS:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "Say OK"}],
        "max_tokens": 10,
        "stream": False,
    }

    t0 = time.time()
    try:
        resp = client.post(
            f"{BASE_URL}/chat/completions",
            headers=headers,
            json=body,
            timeout=30.0,
        )
        elapsed = time.time() - t0

        if resp.status_code == 200:
            data = resp.json()
            usage = data.get("usage", {})
            content = data["choices"][0]["message"]["content"]
            print(f"  ✅ {model}")
            print(f"     Status: 200, Time: {elapsed:.1f}s")
            print(f"     Tokens: in={usage.get('prompt_tokens',0)} out={usage.get('completion_tokens',0)}")
            print(f"     Response: {content[:50]}")
            results.append({"model": model, "status": 200, "ok": True, "tokens": usage})
        else:
            error_data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            error_code = error_data.get("error", {}).get("code", "unknown")
            error_msg = error_data.get("error", {}).get("message", resp.text[:200])
            print(f"  ❌ {model}")
            print(f"     Status: {resp.status_code}, Time: {elapsed:.1f}s")
            print(f"     Error: {error_code} - {error_msg[:100]}")
            results.append({"model": model, "status": resp.status_code, "ok": False, "error": error_code})
    except Exception as e:
        elapsed = time.time() - t0
        print(f"  ❌ {model}")
        print(f"     Exception: {type(e).__name__}: {e}")
        results.append({"model": model, "status": -1, "ok": False, "error": str(e)})
    print()

# Also query the /models endpoint to check what's available
print("=" * 70)
print("Querying /models endpoint for vision models")
print("=" * 70)

try:
    resp = client.get(
        f"{BASE_URL}/models",
        headers=headers,
        timeout=30.0,
    )
    if resp.status_code == 200:
        data = resp.json()
        models = data.get("data", [])
        print(f"Total models available: {len(models)}")

        # Filter for vision-related models
        vision_models = [m for m in models if "vision" in m.get("id", "").lower() or "1-6" in m.get("id", "") or "1.6" in m.get("id", "")]
        print(f"\nVision/1.6 models found:")
        for m in vision_models:
            print(f"  - {m['id']}")

        # Also check for seed models
        seed_models = [m for m in models if "seed" in m.get("id", "").lower()]
        print(f"\nSeed models found ({len(seed_models)}):")
        for m in seed_models:
            print(f"  - {m['id']}")
    else:
        print(f"Failed to list models: {resp.status_code}")
except Exception as e:
    print(f"Error listing models: {e}")

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
for r in results:
    status = "✅ OK" if r["ok"] else f"❌ {r.get('error', r.get('status', 'unknown'))}"
    print(f"  {r['model']:45s} {status}")
