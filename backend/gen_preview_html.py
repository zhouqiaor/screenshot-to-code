"""Generate a self-contained HTML preview from the source screenshot using doubao-seed-2-1-turbo."""
import base64
import json
import os
import sys

import httpx

API_KEY = os.environ.get("ARK_API_KEY", os.environ.get("ARK_API_KEY", "REDACTED"))
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
MODEL = "doubao-seed-2-1-turbo-260628"
SCREENSHOT = "e2e_demo/screenshots/run_20260901/source_screenshot_1024.png"
OUTPUT = "e2e_demo/run_20260901/preview_html.html"

# Resolve relative to repo root (parent of backend/)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENSHOT = os.path.join(_REPO_ROOT, SCREENSHOT)
OUTPUT = os.path.join(_REPO_ROOT, OUTPUT)

SYSTEM_PROMPT = """You are an expert frontend developer. Convert the provided screenshot into a single self-contained HTML file using Tailwind CSS.

Rules:
- Output ONLY the HTML code, no explanations, no markdown fences.
- Use <script src="https://cdn.tailwindcss.com"></script> for Tailwind.
- Match the layout, colors, spacing, and typography as closely as possible.
- Use Google Fonts or publicly accessible fonts if needed.
- Use Font Awesome for icons: <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css">
- Make it responsive and self-contained in one file.
- Do NOT embed the screenshot as an image; recreate everything with HTML/CSS.
"""

def image_to_data_url(path: str) -> str:
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/png;base64,{data}"

def main():
    if not os.path.exists(SCREENSHOT):
        print(f"Screenshot not found: {SCREENSHOT}")
        sys.exit(1)

    data_url = image_to_data_url(SCREENSHOT)
    print(f"Screenshot: {SCREENSHOT} ({len(data_url)} bytes data URL)")
    print(f"Model: {MODEL}")
    print("Calling Ark API...")

    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url},
                    },
                    {
                        "type": "text",
                        "text": "Convert this screenshot into a single self-contained HTML file using Tailwind CSS. Output only the HTML code.",
                    },
                ],
            },
        ],
        "max_tokens": 16000,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=300) as client:
        resp = client.post(
            f"{BASE_URL}/chat/completions", headers=headers, json=body
        )
        print(f"HTTP {resp.status_code}")
        if resp.status_code != 200:
            print(resp.text[:500])
            sys.exit(1)

        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        print(f"Usage: in={usage.get('prompt_tokens')} out={usage.get('completion_tokens')} total={usage.get('total_tokens')}")

        # Strip markdown fences if present
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first line (```html or ```) and last line (```)
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)

        os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
        with open(OUTPUT, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Output: {OUTPUT} ({len(content)} chars)")

if __name__ == "__main__":
    main()
