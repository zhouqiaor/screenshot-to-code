"""Search for vision/multimodal models in the full model list."""
import httpx
import json

API_KEY = os.environ.get("ARK_API_KEY", "REDACTED")
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

resp = httpx.get(f"{BASE_URL}/models", headers=headers, timeout=30)
data = resp.json()
models = data.get("data", [])

print(f"Total models: {len(models)}")
print()

# Filter for vision/multimodal related
vision_keywords = ["vision", "seed-1", "seed-2", "1.6", "1-6", "2.1", "2-1", "evolving", "turbo", "glm", "deepseek"]
vision_models = []

for m in models:
    mid = m.get("id", "")
    # Check if it matches our keywords
    for kw in vision_keywords:
        if kw in mid.lower():
            vision_models.append(mid)
            break

print(f"Matched models ({len(vision_models)}):")
for mid in sorted(vision_models):
    print(f"  {mid}")

print()
print("--- All models with 'seed' or 'vision' in name ---")
for m in models:
    mid = m.get("id", "")
    if "seed" in mid.lower() or "vision" in mid.lower():
        print(f"  {mid}")

print()
print("--- All models with '1.6' or '1-6' ---")
for m in models:
    mid = m.get("id", "")
    if "1.6" in mid or "1-6" in mid:
        print(f"  {mid}")

print()
print("--- All models with '2.1' or '2-1' ---")
for m in models:
    mid = m.get("id", "")
    if "2.1" in mid or "2-1" in mid:
        print(f"  {mid}")

# Now test the ones that look like vision models
print()
print("=" * 80)
print("Testing matched models...")
body_template = {
    "messages": [{"role": "user", "content": "OK"}],
    "max_tokens": 5,
    "stream": False,
}

working = []
for mid in sorted(vision_models):
    body = {**body_template, "model": mid}
    try:
        resp = httpx.post(f"{BASE_URL}/chat/completions", headers=headers, json=body, timeout=15)
        if resp.status_code == 200:
            usage = resp.json().get("usage", {})
            print(f"  OK   {mid:50s} tok={usage.get('prompt_tokens',0)}+{usage.get('completion_tokens',0)}")
            working.append(mid)
        else:
            try:
                err = resp.json().get("error", {}).get("code", "")[:30]
            except Exception:
                err = f"HTTP{resp.status_code}"
            print(f"  FAIL {mid:50s} {err}")
    except Exception as e:
        print(f"  ERR  {mid:50s} {str(e)[:30]}")

print()
print(f"Working models: {len(working)}")
for w in working:
    print(f"  {w}")
