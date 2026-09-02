"""
Try to list/create Ark inference endpoints via API.
Also test the vision model with an actual image (maybe text-only doesn't work).
"""
import httpx
import json
import base64
import time

API_KEY = os.environ.get("ARK_API_KEY", "REDACTED")
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

client = httpx.Client(timeout=60.0)
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# 1. Try Ark endpoint management API (OpenAPI compatible)
print("=" * 70)
print("1. Querying Ark endpoint management APIs")
print("=" * 70)

endpoint_paths = [
    f"{BASE_URL}/endpoints",
    f"{BASE_URL}/inference-endpoints",
    f"https://ark.cn-beijing.volces.com/api/v3/endpoints",
    "https://ark.cn-beijing.volces.com/api/v3/endpoint/list",
    "https://ark.cn-beijing.volces.com/api/v3/bots",
    "https://ark.cn-beijing.volces.com/api/v3/endpoint",
]

for path in endpoint_paths:
    try:
        resp = client.get(path, headers=headers, timeout=10.0)
        print(f"  GET {path}")
        print(f"    -> {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"  GET {path}")
        print(f"    -> Error: {e}")
    print()

# 2. Try POST to create endpoint
print("=" * 70)
print("2. Try creating endpoint for doubao-seed-1-6-vision-250815")
print("=" * 70)

create_paths = [
    (f"{BASE_URL}/endpoints", {"model": "doubao-seed-1-6-vision-250815"}),
    (f"{BASE_URL}/inference-endpoints", {"model": "doubao-seed-1-6-vision-250815"}),
    ("https://ark.cn-beijing.volces.com/api/v3/endpoint/create", {"model_id": "doubao-seed-1-6-vision-250815"}),
]

for path, body_data in create_paths:
    try:
        resp = client.post(path, headers=headers, json=body_data, timeout=10.0)
        print(f"  POST {path}")
        print(f"    -> {resp.status_code}: {resp.text[:300]}")
    except Exception as e:
        print(f"  POST {path}")
        print(f"    -> Error: {e}")
    print()

# 3. Try the vision model with an actual image payload
print("=" * 70)
print("3. Test doubao-seed-1-6-vision-250815 with actual image")
print("=" * 70)

# Create a tiny 1x1 red pixel JPEG
import struct
import io
# Minimal JPEG: SOI + EOI (2 bytes) — may not work, let's use a real small image
# Use a simple 2x2 red pixel PNG
import zlib

def create_minimal_png():
    """Create a 2x2 red pixel PNG."""
    width, height = 2, 2
    raw_data = b"\xff\x00\x00" * (width * height)
    
    # PNG structure
    def chunk(chunk_type, data):
        c = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xffffffff)
        length = struct.pack(">I", len(data))
        return length + c + crc
    
    png = b"\x89PNG\r\n\x1a\n"
    # IHDR
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png += chunk(b"IHDR", ihdr_data)
    # IDAT
    raw_rows = b""
    for y in range(height):
        raw_rows += b"\x00" + raw_data[y*width*3:(y+1)*width*3]
    compressed = zlib.compress(raw_rows)
    png += chunk(b"IDAT", compressed)
    # IEND
    png += chunk(b"IEND", b"")
    return png

png_data = create_minimal_png()
b64_image = base64.b64encode(png_data).decode("utf-8")
print(f"Tiny PNG size: {len(png_data)} bytes, base64: {len(b64_image)} chars")

# Test with vision content
vision_body = {
    "model": "doubao-seed-1-6-vision-250815",
    "messages": [{
        "role": "user",
        "content": [
            {"type": "text", "text": "What do you see?"},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}},
        ],
    }],
    "max_tokens": 50,
    "stream": False,
}

try:
    resp = client.post(f"{BASE_URL}/chat/completions", headers=headers, json=vision_body, timeout=30.0)
    print(f"  Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        usage = data.get("usage", {})
        content = data["choices"][0]["message"]["content"]
        print(f"  ✅ Vision call succeeded!")
        print(f"  Tokens: in={usage.get('prompt_tokens',0)} out={usage.get('completion_tokens',0)}")
        print(f"  Response: {content[:100]}")
    else:
        print(f"  ❌ {resp.text[:300]}")
except Exception as e:
    print(f"  ❌ Error: {e}")

# 4. Try other seed-1-6 models that are in the list
print()
print("=" * 70)
print("4. Test other seed-1-6 models from the catalog")
print("=" * 70)

other_1_6_models = [
    "doubao-seed-1-6-flash-250615",
    "doubao-seed-1-6-250615",
    "doubao-seed-1-6-thinking-250615",
    "doubao-seed-1-6-thinking-250715",
    "doubao-seed-1-6-flash-250715",
    "doubao-seed-1-6-flash-250828",
]

for model in other_1_6_models:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "Say OK"}],
        "max_tokens": 10,
        "stream": False,
    }
    try:
        resp = client.post(f"{BASE_URL}/chat/completions", headers=headers, json=body, timeout=15.0)
        if resp.status_code == 200:
            data = resp.json()
            usage = data.get("usage", {})
            print(f"  ✅ {model} — 200, tokens: in={usage.get('prompt_tokens',0)} out={usage.get('completion_tokens',0)}")
        else:
            error_data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            error_code = error_data.get("error", {}).get("code", "unknown")
            print(f"  ❌ {model} — {resp.status_code} {error_code}")
    except Exception as e:
        print(f"  ❌ {model} — Error: {e}")

client.close()
