"""Test all activated models with various endpoint ID formats."""
import json
import os
import sys
import time

import httpx

API_KEY = os.environ.get("ARK_API_KEY", sys.argv[1] if len(sys.argv) > 1 else "")
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

# Try multiple endpoint ID formats for each model
MODELS_TO_TEST = [
    # (display_name, [possible model IDs])
    ("Doubao-Seed-2.1-turbo", ["doubao-seed-2-1-turbo-260628"]),
    ("GLM-5.2", ["glm-5.2", "glm-52", "glm5.2", "glm_5_2"]),
    ("DeepSeek-V4-pro", ["deepseek-v4-pro", "deepseek-v4-pro-250915", "deepseek-v4-pro-official"]),
    ("Doubao-Seed-1.8", ["doubao-seed-1-8-250915", "doubao-seed-1-8", "doubao-seed-1.8"]),
    ("GLM-4.7", ["glm-4-7", "glm-4.7", "glm47"]),
    ("DeepSeek-V3.2", ["deepseek-v3-2-250628", "deepseek-v3.2", "deepseek-v3-2"]),
    ("Doubao-Seed-Code", ["doubao-seed-code-250915", "doubao-seed-code"]),
    ("Doubao-Seed-1.6-vision", ["doubao-seed-1-6-vision-250815", "doubao-seed-1-6-vision"]),
    ("Doubao-Seed-1.6-flash", ["doubao-seed-1-6-flash-250828", "doubao-seed-1-6-flash"]),
    ("Doubao-Seed-1.6", ["doubao-seed-1-6-250815", "doubao-seed-1-6"]),
    ("Doubao-1.5-vision-lite", ["doubao-1-5-vision-lite-250328", "doubao-1-5-vision-lite"]),
    ("Doubao-1.5-pro-32k", ["doubao-1-5-pro-32k-250328", "doubao-1-5-pro-32k"]),
    ("Doubao-pro-32k", ["doubao-pro-32k-250328", "doubao-pro-32k"]),
]

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

body_template = {
    "messages": [{"role": "user", "content": "Say OK"}],
    "max_tokens": 5,
    "stream": False,
}

print(f"Testing {sum(len(m[1]) for m in MODELS_TO_TEST)} model ID variants")
print("=" * 80)

working_models = []

for name, model_ids in MODELS_TO_TEST:
    for mid in model_ids:
        body = {**body_template, "model": mid}
        try:
            resp = httpx.post(
                f"{BASE_URL}/chat/completions",
                headers=headers,
                json=body,
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                usage = data.get("usage", {})
                print(f"  {name:30s} {mid:40s} OK  tok={usage.get('prompt_tokens',0)}+{usage.get('completion_tokens',0)}")
                working_models.append({"name": name, "model_id": mid, "usage": usage})
                break
            else:
                err_code = ""
                try:
                    err_code = resp.json().get("error", {}).get("code", "")[:30]
                except Exception:
                    err_code = f"HTTP{resp.status_code}"
                print(f"  {name:30s} {mid:40s} {err_code}")
        except Exception as e:
            print(f"  {name:30s} {mid:40s} ERROR {str(e)[:40]}")

print()
print("=" * 80)
print(f"Working models: {len(working_models)}")
for m in working_models:
    print(f"  {m['name']} -> {m['model_id']}")
