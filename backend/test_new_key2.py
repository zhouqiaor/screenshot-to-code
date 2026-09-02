"""Test various model ID formats with new API key."""
import httpx

API_KEY = os.environ.get("ARK_API_KEY", "REDACTED")
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# Try all possible model ID formats
model_ids = [
    "doubao-seed-1-6-vision-250815",
    "doubao-seed-1.6-vision",
    "doubao-seed-1-6-vision",
    "doubao-1-6-vision",
    "doubao-seed-1.6-vision-250815",
    # Also try the old working model with new key
    "doubao-seed-2-1-turbo-260628",
    # Try ep- prefix format (endpoint IDs)
    "ep-doubao-seed-1-6-vision-250815",
]

for mid in model_ids:
    body = {
        "model": mid,
        "messages": [{"role": "user", "content": "OK"}],
        "max_tokens": 5,
    }
    try:
        resp = httpx.post(f"{BASE_URL}/chat/completions", headers=headers, json=body, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            usage = data.get("usage", {})
            content = data["choices"][0]["message"]["content"][:30]
            print(f"  {mid:45s} OK  tok={usage.get('prompt_tokens',0)}+{usage.get('completion_tokens',0)}  \"{content}\"")
        else:
            err = ""
            try:
                err = resp.json().get("error", {}).get("code", "")[:40]
            except Exception:
                err = f"HTTP{resp.status_code}"
            print(f"  {mid:45s} {err}")
    except Exception as e:
        print(f"  {mid:45s} ERROR {str(e)[:40]}")
