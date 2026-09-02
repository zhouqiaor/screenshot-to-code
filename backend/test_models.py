"""
Test which Ark models have working API endpoints after account recharge.
Tests both vision and text models from the updated console data.
"""
import json
import os
import sys
import time

import httpx

API_KEY = os.environ.get("ARK_API_KEY", sys.argv[1] if len(sys.argv) > 1 else "")
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

# Updated model list from console 2026-09-01 17:17
# Only "已开通" models with remaining > 0
MODELS_TO_TEST = [
    # (display_name, model_id_for_api, remaining, vision_capable, input_price, output_price)
    ("Doubao-Seed-2.1-turbo", "doubao-seed-2-1-turbo-260628", 268378, True, 0.003, 0.015),
    ("GLM-5.2", "glm-5.2", 500000, True, 0.008, 0.028),
    ("DeepSeek-V4-pro", "deepseek-v4-pro", 223965, False, 0.009, 0.027),
    ("Doubao-Seed-1.8", "doubao-seed-1-8-250915", 500000, True, 0.0008, 0.0020),
    ("GLM-4.7", "glm-4-7", 500000, False, 0.002, 0.008),
    ("DeepSeek-V3.2", "deepseek-v3-2-250628", 500000, False, 0.002, 0.003),
    ("Doubao-Seed-Code", "doubao-seed-code-250915", 500000, False, 0.0012, 0.008),
    ("Doubao-Seed-1.6-vision", "doubao-seed-1-6-vision-250815", 500000, True, 0.0008, 0.008),
    ("Doubao-Seed-1.6-flash", "doubao-seed-1-6-flash-250828", 500000, True, 0.00015, 0.0015),
    ("Doubao-Seed-1.6", "doubao-seed-1-6-250815", 500000, True, 0.0008, 0.002),
    ("Doubao-1.5-vision-lite", "doubao-1-5-vision-lite-250328", 500000, True, 0.0015, 0.0045),
    ("Doubao-1.5-vision-pro-32k", "doubao-1-5-vision-pro-32k-250328", 500000, True, 0.003, 0.009),
    ("Doubao-1.5-pro-32k", "doubao-1-5-pro-32k-250328", 500000, False, 0.0008, 0.002),
    ("Doubao-pro-32k", "doubao-pro-32k-250328", 500000, False, 0.0008, 0.002),
    ("Doubao-lite-32k", "doubao-lite-32k-250328", 500000, False, 0.0003, 0.0006),
]

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

print(f"API Key: {API_KEY[:20]}...{API_KEY[-8:]}")
print(f"Testing {len(MODELS_TO_TEST)} models")
print("=" * 90)

results = []

for name, model_id, remaining, vision, in_price, out_price in MODELS_TO_TEST:
    body = {
        "model": model_id,
        "messages": [{"role": "user", "content": "Say OK"}],
        "max_tokens": 10,
        "stream": False,
    }
    t0 = time.time()
    try:
        resp = httpx.post(
            f"{BASE_URL}/chat/completions",
            headers=headers,
            json=body,
            timeout=30,
        )
        elapsed = time.time() - t0
        if resp.status_code == 200:
            data = resp.json()
            usage = data.get("usage", {})
            actual_model = data.get("model", model_id)
            out_content = data["choices"][0]["message"]["content"][:50]
            results.append({
                "name": name,
                "model_id": model_id,
                "status": "OK",
                "http": 200,
                "time_sec": round(elapsed, 1),
                "tokens_in": usage.get("prompt_tokens", 0),
                "tokens_out": usage.get("completion_tokens", 0),
                "actual_model": actual_model,
                "vision": vision,
                "remaining": remaining,
                "in_price": in_price,
                "out_price": out_price,
                "output_preview": out_content,
            })
            print(f"  {name:30s} OK  {elapsed:.1f}s  tok={usage.get('prompt_tokens',0)}+{usage.get('completion_tokens',0)}  \"{out_content}\"")
        else:
            err = ""
            try:
                err = resp.json().get("error", {}).get("code", resp.text[:80])
            except Exception:
                err = resp.text[:80]
            results.append({
                "name": name,
                "model_id": model_id,
                "status": "FAIL",
                "http": resp.status_code,
                "error": err,
                "time_sec": round(elapsed, 1),
            })
            print(f"  {name:30s} FAIL {resp.status_code} {err[:60]}")
    except Exception as e:
        elapsed = time.time() - t0
        results.append({
            "name": name,
            "model_id": model_id,
            "status": "ERROR",
            "error": str(e)[:80],
            "time_sec": round(elapsed, 1),
        })
        print(f"  {name:30s} ERROR {str(e)[:60]}")

print()
print("=" * 90)
ok_models = [r for r in results if r["status"] == "OK"]
print(f"Working: {len(ok_models)}/{len(results)}")

if ok_models:
    print("\n--- Working models sorted by cost ---")
    ok_models.sort(key=lambda r: (r.get("in_price", 999) + r.get("out_price", 999)))
    for r in ok_models:
        v = "VISION" if r.get("vision") else "text  "
        print(f"  {r['name']:30s} {v}  in=¥{r.get('in_price',0)}/千tok out=¥{r.get('out_price',0)}/千tok  rem={r.get('remaining',0):>7d}")

# Save results
out_path = os.path.join(os.path.dirname(__file__), "..", "e2e_demo", "model_test_results.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"\nResults saved to {out_path}")
