"""
Test the /responses endpoint (new Ark API format) vs /chat/completions (old format).
The user's doc shows using /responses with doubao-seed-1-6-vision-250815.
Let's test both endpoints with both models.
"""
import sys
sys.path.insert(0, r'C:\Users\georgeslark\.workbuddy\binaries\python\envs\default\Lib\site-packages')

import httpx
import json
import time

API_KEY = os.environ.get("ARK_API_KEY", "REDACTED")
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

client = httpx.Client(timeout=60.0)
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

print("=" * 70)
print("Test 1: /responses endpoint with doubao-seed-1-6-vision-250815")
print("       (using remote image URL from docs)")
print("=" * 70)

body_responses_vision = {
    "model": "doubao-seed-1-6-vision-250815",
    "input": [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_image",
                    "image_url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/ark_demo_img_1.png"
                },
                {
                    "type": "input_text",
                    "text": "你看见了什么？"
                }
            ]
        }
    ]
}

try:
    t0 = time.time()
    resp = client.post(f"{BASE_URL}/responses", headers=headers, json=body_responses_vision, timeout=60.0)
    elapsed = time.time() - t0
    print(f"Status: {resp.status_code} ({elapsed:.1f}s)")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Response: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
    else:
        print(f"Error: {resp.text[:500]}")
except Exception as e:
    print(f"Exception: {e}")

print()

print("=" * 70)
print("Test 2: /responses endpoint with doubao-seed-2-1-turbo-260628 (text only)")
print("=" * 70)

body_responses_text = {
    "model": "doubao-seed-2-1-turbo-260628",
    "input": [
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": "Say OK"
                }
            ]
        }
    ]
}

try:
    t0 = time.time()
    resp = client.post(f"{BASE_URL}/responses", headers=headers, json=body_responses_text, timeout=30.0)
    elapsed = time.time() - t0
    print(f"Status: {resp.status_code} ({elapsed:.1f}s)")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Response: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
    else:
        print(f"Error: {resp.text[:500]}")
except Exception as e:
    print(f"Exception: {e}")

print()

print("=" * 70)
print("Test 3: /chat/completions with doubao-seed-2-1-turbo-260628 (vision)")
print("       (using remote image URL)")
print("=" * 70)

body_chat_vision = {
    "model": "doubao-seed-2-1-turbo-260628",
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/ark_demo_img_1.png"}
                },
                {
                    "type": "text",
                    "text": "你看见了什么？"
                }
            ]
        }
    ],
    "max_tokens": 200,
    "stream": False
}

try:
    t0 = time.time()
    resp = client.post(f"{BASE_URL}/chat/completions", headers=headers, json=body_chat_vision, timeout=60.0)
    elapsed = time.time() - t0
    print(f"Status: {resp.status_code} ({elapsed:.1f}s)")
    if resp.status_code == 200:
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        print(f"Content: {content[:300]}")
        print(f"Tokens: in={usage.get('prompt_tokens',0)} out={usage.get('completion_tokens',0)}")
    else:
        print(f"Error: {resp.text[:500]}")
except Exception as e:
    print(f"Exception: {e}")

print()

print("=" * 70)
print("Test 4: /chat/completions with doubao-seed-1-6-vision-250815 (vision)")
print("       (using remote image URL - old chat format)")
print("=" * 70)

body_chat_vision_16 = {
    "model": "doubao-seed-1-6-vision-250815",
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/ark_demo_img_1.png"}
                },
                {
                    "type": "text",
                    "text": "你看见了什么？"
                }
            ]
        }
    ],
    "max_tokens": 200,
    "stream": False
}

try:
    t0 = time.time()
    resp = client.post(f"{BASE_URL}/chat/completions", headers=headers, json=body_chat_vision_16, timeout=60.0)
    elapsed = time.time() - t0
    print(f"Status: {resp.status_code} ({elapsed:.1f}s)")
    if resp.status_code == 200:
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        print(f"Content: {content[:300]}")
        print(f"Tokens: in={usage.get('prompt_tokens',0)} out={usage.get('completion_tokens',0)}")
    else:
        print(f"Error: {resp.text[:500]}")
except Exception as e:
    print(f"Exception: {e}")

# Summary
print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)

client.close()
