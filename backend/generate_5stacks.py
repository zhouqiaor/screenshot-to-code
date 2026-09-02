"""
Screenshot-to-Code E2E: 从 ADB 截图生成 5 栈 UI 代码。

策略:
  1. 1 次 vision 调用 (doubao-seed-2.1-turbo) 分析截图 → 提取 UI 结构描述
  2. 5 次纯文本调用 → 生成各栈代码 (Kotlin/XML/QML/HTML/A2UI)
  总计 ~26K tokens, 远低于 5 次独立 vision 调用的 ~75K。

用法:
  export ARK_API_KEY=xxx  (或从参数传入)
  python generate_5stacks.py
"""
import asyncio
import base64
import json
import os
import sys
import time
import traceback
from pathlib import Path

import httpx

# ─── Config ───────────────────────────────────────────────────────────────────
ARK_API_KEY = os.environ.get("ARK_API_KEY", "")
ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
VISION_MODEL = "doubao-seed-2-1-turbo-260628"  # vision capable, cheaper
TEXT_MODEL = "doubao-seed-2-1-turbo-260628"    # same model for text gen

BASE_DIR = Path(__file__).resolve().parent.parent  # project root
SCREENSHOT_DIR = BASE_DIR / "e2e_demo" / "screenshots" / "run_20260901"
OUTPUT_DIR = BASE_DIR / "e2e_demo" / "run_20260901"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ─── Prompts ──────────────────────────────────────────────────────────────────

VISION_PROMPT = """\
你是一个 UI 分析专家。请分析这张 Android 设备截图，提取 UI 结构信息。

输出 JSON 格式（不要 markdown fence），包含：
{
  "theme": "dark" | "light",
  "primary_color": "#hex",
  "background_color": "#hex",
  "text_color": "#hex",
  "title": "页面标题或应用名",
  "components": [
    {
      "type": "text|button|switch|dropdown|image|list|card|slider|input",
      "text": "显示文本（如有）",
      "position": "top|center|bottom|sidebar",
      "description": "简短描述"
    }
  ],
  "layout": "vertical|horizontal|grid|tab",
  "summary": "一句话总结页面功能"
}

只输出 JSON，不要其他文字。"""

def make_stack_prompt(stack: str, ui_desc: str) -> str:
    """Generate stack-specific code prompt based on UI description."""
    base = f"""请根据以下 UI 描述，生成一个 {stack} 格式的设置页面代码。

UI 描述:
{ui_desc}

要求:
1. 代码完整可编译/可验证
2. 只输出代码，不要解释
3. 不要 markdown fence"""

    if stack == "android_compose":
        return base.replace("{stack}", "Android Jetpack Compose (Kotlin)") + """

使用 Jetpack Compose:
- @Composable 函数
- Material 3 组件
- Column/Row 布局
- Switch, Text, Button 等

输出格式:
```kotlin
package com.example.settings

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier

@Composable
fun SettingsScreen() {
    // ...
}
```"""

    elif stack == "android_xml":
        return base.replace("{stack}", "Android XML Layout") + """

使用 LinearLayout:
- xmlns:android 命名空间
- 合法 Android 控件: TextView, Button, Switch, Spinner
- android: 属性

输出格式:
```xml
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout ...>
    <!-- controls -->
</LinearLayout>
```"""

    elif stack == "qt_qml":
        return base.replace("{stack}", "Qt QML") + """

使用 QtQuick Controls:
- ApplicationWindow 根元素
- ColumnLayout 布局
- Label, Switch, ComboBox, Button

输出格式:
```qml
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    // ...
}
```"""

    elif stack == "html":
        return base.replace("{stack}", "Windows HTML/CSS 自包含页面") + """

自包含 HTML:
- DOCTYPE + html/head/body
- 内联 CSS (不引用外部资源)
- 设置页面样式: 卡片式布局, 切换开关, 下拉选择

输出格式:
```html
<!DOCTYPE html>
<html>
<head><style>...</style></head>
<body>...</body>
</html>
```"""

    elif stack == "a2ui":
        return base.replace("{stack}", "A2UI JSONL 格式") + """

A2UI JSONL 每行一个 JSON 对象:
- 合法类型: button, card, column, container, image, input, list, row, stack, text
- 每个 node 有 id, type, props, children
- 第一行是根节点 (type=column)

输出格式:
{"id":"root","type":"column","props":{},"children":["header","body"]}
{"id":"header","type":"text","props":{"text":"Settings"}}
... (每行一个 JSON)"""

    return base


# ─── Ark API client ──────────────────────────────────────────────────────────

async def call_ark(
    client: httpx.AsyncClient,
    messages: list[dict],
    model: str = TEXT_MODEL,
    max_tokens: int = 4096,
    temperature: float = 0.3,
) -> dict:
    """Call Ark API (OpenAI-compatible) and return response dict."""
    headers = {
        "Authorization": f"Bearer {ARK_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    url = f"{ARK_BASE_URL}/chat/completions"
    resp = await client.post(url, headers=headers, json=body, timeout=300.0)
    resp.raise_for_status()
    return resp.json()


def extract_content(resp: dict) -> str:
    """Extract assistant message content from API response."""
    return resp["choices"][0]["message"]["content"]


def extract_usage(resp: dict) -> dict:
    """Extract token usage from API response."""
    u = resp.get("usage", {})
    return {
        "input": u.get("prompt_tokens", 0),
        "output": u.get("completion_tokens", 0),
        "total": u.get("total_tokens", 0),
    }


# ─── Main pipeline ───────────────────────────────────────────────────────────

async def main():
    if not ARK_API_KEY:
        # Try to read from arg
        if len(sys.argv) > 1:
            os.environ["ARK_API_KEY"] = sys.argv[1]
            globals()["ARK_API_KEY"] = sys.argv[1]
        else:
            print("ERROR: No ARK_API_KEY found. Set env or pass as arg.")
            sys.exit(1)

    # Load screenshot base64
    b64_path = SCREENSHOT_DIR / "source_b64.txt"
    if not b64_path.exists():
        print(f"ERROR: {b64_path} not found. Run prep_screenshot.py first.")
        sys.exit(1)

    with open(b64_path, "r") as f:
        image_b64 = f.read()

    print(f"Image base64 length: {len(image_b64)} chars")
    print(f"Using model: {VISION_MODEL}")
    print()

    total_usage = {"input": 0, "output": 0, "total": 0}
    results = {}

    async with httpx.AsyncClient() as client:
        # ── Step 1: Vision analysis ──────────────────────────────────────
        print("=" * 60)
        print("Step 1: Vision analysis (describing screenshot)")
        print("=" * 60)

        data_url = f"data:image/jpeg;base64,{image_b64}"
        vision_messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ]

        t0 = time.time()
        try:
            resp = await call_ark(client, vision_messages, model=VISION_MODEL, max_tokens=2048)
            ui_desc = extract_content(resp)
            usage = extract_usage(resp)
            total_usage["input"] += usage["input"]
            total_usage["output"] += usage["output"]
            total_usage["total"] += usage["total"]
            elapsed = time.time() - t0
            print(f"  Tokens: in={usage['input']} out={usage['output']} total={usage['total']}")
            print(f"  Time: {elapsed:.1f}s")
            print(f"  UI description preview:")
            for line in ui_desc[:500].split("\n"):
                print(f"    {line}")
            print()

            # Save UI description
            with open(OUTPUT_DIR / "ui_description.json", "w", encoding="utf-8") as f:
                f.write(ui_desc)
                f.write("\n")

        except Exception as e:
            print(f"ERROR in vision call: {e}")
            traceback.print_exc()
            return

        # ── Step 2: Generate 5 stacks (sequential to avoid rate limits) ───
        stacks = [
            ("android_compose", "llm_android_compose.kt", 4096),
            ("android_xml", "llm_android_xml.xml", 3072),
            ("qt_qml", "llm_qt_qml.qml", 3072),
            ("html", "llm_windows_html.html", 4096),
            ("a2ui", "llm_a2ui.jsonl", 2048),
        ]

        for i, (stack, filename, max_tok) in enumerate(stacks, 1):
            print("=" * 60)
            print(f"Step {i+1}: Generating {stack} → {filename}")
            print("=" * 60)

            prompt = make_stack_prompt(stack, ui_desc)
            messages = [{"role": "user", "content": prompt}]

            t0 = time.time()
            try:
                resp = await call_ark(client, messages, model=TEXT_MODEL, max_tokens=max_tok)
                code = extract_content(resp)
                usage = extract_usage(resp)
                total_usage["input"] += usage["input"]
                total_usage["output"] += usage["output"]
                total_usage["total"] += usage["total"]
                elapsed = time.time() - t0

                # Strip markdown fences if present
                code = code.strip()
                if code.startswith("```"):
                    lines = code.split("\n")
                    # Remove first line (```kotlin etc) and last line (```)
                    lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    code = "\n".join(lines)

                # Save generated code
                out_path = OUTPUT_DIR / filename
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(code)

                print(f"  Tokens: in={usage['input']} out={usage['output']} total={usage['total']}")
                print(f"  Time: {elapsed:.1f}s")
                print(f"  Chars: {len(code)}")
                print(f"  Saved: {out_path}")
                print()

                results[stack] = {
                    "file": filename,
                    "chars": len(code),
                    "tokens_in": usage["input"],
                    "tokens_out": usage["output"],
                    "time_sec": round(elapsed, 1),
                    "ok": True,
                }

            except Exception as e:
                print(f"  ERROR: {e}")
                traceback.print_exc()
                results[stack] = {"file": filename, "ok": False, "error": str(e)}
                print()

    # ── Summary ─────────────────────────────────────────────────────────
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total tokens: in={total_usage['input']} out={total_usage['output']} total={total_usage['total']}")
    print(f"Estimated cost: ¥{(total_usage['input'] * 0.003 + total_usage['output'] * 0.015) / 1000:.3f}")
    print()
    for stack, info in results.items():
        status = "PASS" if info.get("ok") else "FAIL"
        print(f"  {stack:20s} {status}  {info.get('chars', 0):>6} chars  {info.get('tokens_out', 0):>5} tok")

    # Save report
    report = {
        "timestamp": "2026-09-01T16:59:00+08:00",
        "model": VISION_MODEL,
        "screenshot": str(SCREENSHOT_DIR / "source_screenshot.png"),
        "total_tokens": total_usage,
        "stacks": results,
    }
    with open(OUTPUT_DIR / "generation_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReport saved to {OUTPUT_DIR / 'generation_report.json'}")


if __name__ == "__main__":
    asyncio.run(main())
