"""
Generate the missing A2UI stack and a more complete HTML stack.
The first combined call ran out of tokens (26206 output tokens for 5 stacks).
"""
import sys
sys.path.insert(0, r'C:\Users\georgeslark\.workbuddy\binaries\python\envs\default\Lib\site-packages')

import json
import time
import httpx
from pathlib import Path

API_KEY = os.environ.get("ARK_API_KEY", "REDACTED")
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
MODEL = "doubao-seed-2-1-turbo-260628"

BASE_DIR = Path(r'C:\Code\screenshot-to-code')
OUTPUT_DIR = BASE_DIR / "e2e_demo" / "run_20260901"
UI_DESC_PATH = OUTPUT_DIR / "ui_description.json"

with open(UI_DESC_PATH, "r", encoding="utf-8") as f:
    ui_desc = f.read()

client = httpx.Client(timeout=300.0)
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# 1. Generate A2UI JSONL
print("=" * 60)
print("Generating A2UI JSONL...")
print("=" * 60)

a2ui_prompt = f"""根据以下 UI 描述，生成 A2UI JSONL 格式代码。

UI 描述:
{ui_desc}

A2UI 格式说明:
- JSONL 格式，每行一个 JSON 对象
- 合法类型: button, card, column, container, image, input, list, row, stack, text
- 每个对象必须有 "type" 字段
- 可选字段: text, children, style, onClick, placeholder, value, checked, min, max, icon

页面结构: 设置 - 声音与显示
- 左侧: 侧边栏（搜索框 + 导航列表）
- 右侧: 声音与显示设置项（扬声器开关、音量滑块、提示音量滑块、按键音开关、麦克风开关、亮度滑块）

直接输出 JSONL，不要 markdown fence，不要解释。"""

body = {
    "model": MODEL,
    "messages": [{"role": "user", "content": a2ui_prompt}],
    "max_tokens": 4000,
    "temperature": 0.3,
    "stream": False,
}

t0 = time.time()
resp = client.post(f"{BASE_URL}/chat/completions", headers=headers, json=body, timeout=300.0)
elapsed = time.time() - t0
print(f"Status: {resp.status_code} ({elapsed:.1f}s)")

if resp.status_code == 200:
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    print(f"Tokens: in={usage.get('prompt_tokens',0)} out={usage.get('completion_tokens',0)}")
    print(f"Content length: {len(content)} chars")

    # Strip markdown fence if present
    if content.strip().startswith("```"):
        lines = content.strip().split("\n")[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)

    out_path = OUTPUT_DIR / "llm_a2ui.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  A2UI -> llm_a2ui.jsonl {len(content)} chars  OK")
else:
    print(f"ERROR: {resp.text[:500]}")

# 2. Generate a more complete HTML
print()
print("=" * 60)
print("Generating complete HTML...")
print("=" * 60)

html_prompt = f"""根据以下 UI 描述，生成一个完整的自包含 HTML 文件。

UI 描述:
{ui_desc}

要求:
- 完整的 HTML 文件（DOCTYPE + html + head + body）
- 内联 CSS（不用外部样式表）
- 模拟设置页面布局：左侧侧边栏 + 右侧设置内容
- 侧边栏包含：搜索框、导航列表（企业服务配置、声音与显示[当前选中]、摄像机、壁纸、Wi-Fi、智慧功能、高级设置）
- 右侧内容区：标题"声音与显示"，包含扬声器开关、音量滑块、提示音量滑块、按键音开关、麦克风开关、亮度滑块
- 关闭按钮(×)在右上角
- 使用卡片式布局，圆角，阴影效果
- 开关用 checkbox + slider 样式实现
- 滑块用 input[type=range] 实现
- 配色: 背景 #f5f5f5, 卡片白色, 主色 #1677ff, 文字 #212121

直接输出完整 HTML 代码，不要 markdown fence，不要解释。"""

body_html = {
    "model": MODEL,
    "messages": [{"role": "user", "content": html_prompt}],
    "max_tokens": 6000,
    "temperature": 0.3,
    "stream": False,
}

t0 = time.time()
resp = client.post(f"{BASE_URL}/chat/completions", headers=headers, json=body_html, timeout=300.0)
elapsed = time.time() - t0
print(f"Status: {resp.status_code} ({elapsed:.1f}s)")

if resp.status_code == 200:
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    print(f"Tokens: in={usage.get('prompt_tokens',0)} out={usage.get('completion_tokens',0)}")
    print(f"Content length: {len(content)} chars")

    # Strip markdown fence if present
    if content.strip().startswith("```"):
        lines = content.strip().split("\n")[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)

    out_path = OUTPUT_DIR / "llm_windows_html.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  HTML -> llm_windows_html.html {len(content)} chars  OK")
else:
    print(f"ERROR: {resp.text[:500]}")

# Summary
print()
print("=" * 60)
print("SUPPLEMENTARY GENERATION SUMMARY")
print("=" * 60)
try:
    total_in = usage.get('prompt_tokens', 0)
    total_out = usage.get('completion_tokens', 0)
except Exception:
    total_in = 0
    total_out = 0
print(f"Tokens: in={total_in} out={total_out} total={total_in+total_out}")
cost = (total_in * 0.003 + total_out * 0.015) / 1000
print(f"Cost: ¥{cost:.4f}")

client.close()
