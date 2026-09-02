"""Quick test if Ark API still works."""
import httpx
import os
import sys

key = os.environ.get("ARK_API_KEY", sys.argv[1] if len(sys.argv) > 1 else "")
headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
body = {
    "model": "doubao-seed-2-1-turbo-260628",
    "messages": [{"role": "user", "content": "OK"}],
    "max_tokens": 5,
}
resp = httpx.post(
    "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
    headers=headers,
    json=body,
    timeout=30,
)
print(f"Status: {resp.status_code}")
print(f"Body: {resp.text[:300]}")
