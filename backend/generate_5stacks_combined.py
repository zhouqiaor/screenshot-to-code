"""
Generate all 5 stacks in a single API call to minimize token usage.
Uses the already-obtained UI description from vision analysis.
"""
import json
import os
import sys
import time
from pathlib import Path

import httpx

API_KEY = os.environ.get("ARK_API_KEY", "REDACTED")
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
MODEL = "doubao-seed-2-1-turbo-260628"

# Note: doubao-seed-1-6-vision-250815 is EOM (2026-07-10) and cannot be used.
# doubao-seed-2-1-turbo-260628 supports vision (verified via Test 3) and text generation.

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "e2e_demo" / "run_20260901"
UI_DESC_PATH = OUTPUT_DIR / "ui_description.json"

with open(UI_DESC_PATH, "r", encoding="utf-8") as f:
    ui_desc = f.read()

COMBINED_PROMPT = f"""根据以下 UI 描述，一次性生成 5 种技术栈的代码。

UI 描述:
{ui_desc}

要求: 每个栈用 === 标记分隔，格式如下:
===KOTLIN===
(代码)
===XML===
(代码)
===QML===
(代码)
===HTML===
(代码)
===A2UI===
(代码)

1. KOTLIN: Android Jetpack Compose，@Composable 函数，Material3 组件
2. XML: Android XML Layout，LinearLayout 根元素，含 xmlns:android
3. QML: QtQuick Controls，ApplicationWindow 根元素
4. HTML: 自包含 HTML（DOCTYPE + 内联 CSS），卡片式设置布局
5. A2UI: JSONL 格式，每行一个 JSON 对象，合法类型: button/card/column/container/image/input/list/row/stack/text

不要 markdown fence。直接输出代码。"""

print(f"Prompt length: {len(COMBINED_PROMPT)} chars")
print(f"Using model: {MODEL}")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

body = {
    "model": MODEL,
    "messages": [{"role": "user", "content": COMBINED_PROMPT}],
    "max_tokens": 8000,
    "temperature": 0.3,
    "stream": False,
}

print("Sending request...")
t0 = time.time()

try:
    client = httpx.Client(timeout=300.0)
    resp = client.post(
        f"{BASE_URL}/chat/completions",
        headers=headers,
        json=body,
        timeout=300.0,
    )
    elapsed = time.time() - t0
    print(f"Status: {resp.status_code} ({elapsed:.1f}s)")

    if resp.status_code != 200:
        print(f"ERROR: {resp.text[:500]}")
        sys.exit(1)

    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})

    print(f"Tokens: in={usage.get('prompt_tokens',0)} out={usage.get('completion_tokens',0)} total={usage.get('total_tokens',0)}")
    print(f"Content length: {len(content)} chars")
    print()

    # Parse sections
    sections = {}
    current_stack = None
    current_lines = []

    for line in content.split("\n"):
        if line.strip().startswith("===") and line.strip().endswith("==="):
            if current_stack:
                sections[current_stack] = "\n".join(current_lines).strip()
            current_stack = line.strip().strip("=").strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_stack:
        sections[current_stack] = "\n".join(current_lines).strip()

    # Map to filenames
    stack_files = {
        "KOTLIN": "llm_android_compose.kt",
        "XML": "llm_android_xml.xml",
        "QML": "llm_qt_qml.qml",
        "HTML": "llm_windows_html.html",
        "A2UI": "llm_a2ui.jsonl",
    }

    results = {}
    for stack, filename in stack_files.items():
        code = sections.get(stack, "")
        if code:
            # Strip markdown fence if present
            if code.startswith("```"):
                lines = code.split("\n")[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                code = "\n".join(lines)

            out_path = OUTPUT_DIR / filename
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(code)
            print(f"  {stack:8s} -> {filename:30s} {len(code):>6} chars  OK")
            results[stack] = {"file": filename, "chars": len(code), "ok": True}
        else:
            print(f"  {stack:8s} -> {'(missing)':30s} {'':>6}      MISSING")
            results[stack] = {"file": filename, "chars": 0, "ok": False}

    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    total_out = usage.get("completion_tokens", 0)
    total_in = usage.get("prompt_tokens", 0)
    cost = (total_in * 0.003 + total_out * 0.015) / 1000
    print(f"Tokens: in={total_in} out={total_out} total={total_in+total_out}")
    print(f"Cost: ¥{cost:.4f}")
    print(f"Time: {elapsed:.1f}s")
    ok_count = sum(1 for r in results.values() if r["ok"])
    print(f"Stacks: {ok_count}/5 generated")

    # Save report
    report = {
        "timestamp": f"2026-09-01T{time.strftime('%H:%M:%S')}+08:00",
        "model": MODEL,
        "tokens": {"input": total_in, "output": total_out, "total": total_in + total_out},
        "cost_cny": round(cost, 4),
        "time_sec": round(elapsed, 1),
        "stacks": results,
    }
    with open(OUTPUT_DIR / "generation_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
