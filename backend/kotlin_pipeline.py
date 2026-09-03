#!/usr/bin/env python3
"""
Screenshot → Kotlin Compose 全流程管线
阶段 1: 源截图分析 (色调/亮度/分割线/组件)
阶段 2: HTML 预览生成 (doubao-seed-2-1-turbo + vision)
阶段 3: Kotlin Compose 代码生成 (doubao-seed-2-1-turbo + vision)
阶段 4: 编译验证 (Gradle assembleDebug)
阶段 5: 自包含 HTML 报告 (源截图 + 分析 + 生成代码 + 编译结果 + 截图)
"""
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx
import numpy as np
from PIL import Image

# === 路径 ===
BASE_DIR = Path(__file__).resolve().parent.parent
SCREENSHOT = BASE_DIR / "e2e_demo" / "screenshots" / "run_20260901" / "source_screenshot_1024.png"
RUN_DIR = BASE_DIR / "e2e_demo" / "run_20260901" / "kotlin_pipeline"
RUN_DIR.mkdir(parents=True, exist_ok=True)
ANDROID_PROJECT = BASE_DIR / "e2e_demo" / "android_project"
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

# === API ===
API_KEY = os.environ.get("ARK_API_KEY", os.environ.get("ARK_API_KEY", "REDACTED"))
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
MODEL = "doubao-seed-2-1-turbo-260628"

# === 输出文件 ===
ANALYSIS_JSON = RUN_DIR / "analysis.json"
HTML_PREVIEW = RUN_DIR / "html_preview.html"
KOTLIN_FILE = RUN_DIR / "MainActivity.kt"
COMPILE_LOG = RUN_DIR / "compile_log.txt"
HTML_SRENNABLE = RUN_DIR / "kotlin_render.html"
KOTLIN_SCREENSHOT = RUN_DIR / "kotlin_screenshot.png"
REPORT_HTML = RUN_DIR / "pipeline_report.html"


def image_to_data_url(path: str) -> str:
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/png;base64,{data}"


def call_ark(messages: list, max_tokens: int = 16000) -> dict:
    """Call doubao-seed-2-1-turbo via Ark API (non-streaming)."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": False,
    }
    with httpx.Client(timeout=httpx.Timeout(900.0, connect=30.0)) as client:
        resp = client.post(f"{BASE_URL}/chat/completions", headers=headers, json=body)
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:500]}")
        return resp.json()


def strip_markdown_fences(content: str) -> str:
    """Remove markdown code fences if present."""
    if content.strip().startswith("```"):
        lines = content.strip().split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines)
    return content


# ============================================================
# 阶段 1: 源截图分析
# ============================================================
def stage1_analyze() -> dict:
    print("\n" + "=" * 60)
    print("阶段 1: 源截图分析")
    print("=" * 60)

    img = Image.open(SCREENSHOT).convert("RGB")
    w, h = img.size
    arr = np.array(img)

    # 主色调
    small = img.resize((50, 100))
    colors = small.getcolors(small.size[0] * small.size[1])
    colors.sort(reverse=True)
    top_colors = [
        {"count": c, "hex": f"#{r:02x}{g:02x}{b:02x}", "pct": round(c / (small.size[0] * small.size[1]) * 100, 1)}
        for c, (r, g, b) in colors[:15]
    ]

    # 亮度
    lum = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]

    # 分区域
    regions_v = {}
    for name, region in [("top", arr[: h // 3]), ("mid", arr[h // 3 : 2 * h // 3]), ("bot", arr[2 * h // 3 :])]:
        rlum = 0.299 * region[:, :, 0] + 0.587 * region[:, :, 1] + 0.114 * region[:, :, 2]
        mean_rgb = region.reshape(-1, 3).mean(axis=0).astype(int)
        regions_v[name] = {"lum_mean": round(float(rlum.mean()), 1), "rgb_mean": [int(x) for x in mean_rgb]}

    # 水平分割线
    row_means = lum.mean(axis=1)
    diffs = np.abs(np.diff(row_means))
    threshold = diffs.mean() + 2 * diffs.std()
    divider_rows = np.where(diffs > threshold)[0]
    clusters = []
    for r in divider_rows:
        if clusters and r - clusters[-1][-1] <= 5:
            clusters[-1].append(r)
        else:
            clusters.append([r])
    h_dividers = [int(np.mean(c)) for c in clusters if len(c) >= 2]

    # 垂直分割线
    col_means = lum.mean(axis=0)
    diffs_v = np.abs(np.diff(col_means))
    threshold_v = diffs_v.mean() + 2 * diffs_v.std()
    divider_cols = np.where(diffs_v > threshold_v)[0]
    clusters_v = []
    for c in divider_cols:
        if clusters_v and c - clusters_v[-1][-1] <= 5:
            clusters_v[-1].append(c)
        else:
            clusters_v.append([c])
    v_dividers = [int(np.mean(c)) for c in clusters_v if len(c) >= 2]

    # UI 描述（从已有分析加载）
    ui_desc_path = BASE_DIR / "e2e_demo" / "run_20260901" / "ui_description.json"
    ui_desc = json.loads(ui_desc_path.read_text(encoding="utf-8")) if ui_desc_path.exists() else {}

    analysis = {
        "timestamp": datetime.now().isoformat(),
        "screenshot": str(SCREENSHOT),
        "size": {"width": w, "height": h},
        "top_colors": top_colors,
        "luminance": {
            "mean": round(float(lum.mean()), 1),
            "min": round(float(lum.min()), 1),
            "max": round(float(lum.max()), 1),
            "dark_pct": round(float((lum < 128).sum() / lum.size * 100), 1),
            "light_pct": round(float((lum >= 128).sum() / lum.size * 100), 1),
        },
        "regions_vertical": regions_v,
        "h_dividers": h_dividers,
        "v_dividers": v_dividers,
        "ui_description": ui_desc,
    }

    ANALYSIS_JSON.write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  尺寸: {w}x{h}")
    print(f"  亮度: mean={analysis['luminance']['mean']} dark={analysis['luminance']['dark_pct']}% light={analysis['luminance']['light_pct']}%")
    print(f"  主色: {top_colors[0]['hex']} ({top_colors[0]['pct']}%)")
    print(f"  水平分割线: {h_dividers}")
    print(f"  垂直分割线: {v_dividers}")
    print(f"  UI组件: {len(ui_desc.get('components', []))} 个")
    print(f"  分析结果: {ANALYSIS_JSON}")
    return analysis


# ============================================================
# 阶段 2: HTML 预览生成
# ============================================================
def stage2_html_preview(analysis: dict) -> str:
    print("\n" + "=" * 60)
    print("阶段 2: HTML 预览生成 (doubao-seed-2-1-turbo)")
    print("=" * 60)

    data_url = image_to_data_url(str(SCREENSHOT))
    print(f"  截图 data URL: {len(data_url)} bytes")

    system_prompt = """You are an expert frontend developer. Convert the provided screenshot into a single self-contained HTML file using Tailwind CSS.

Rules:
- Output ONLY the HTML code, no explanations, no markdown fences.
- Use <script src="https://cdn.tailwindcss.com"></script> for Tailwind.
- Match the layout, colors, spacing, and typography as closely as possible.
- Use Google Fonts or publicly accessible fonts if needed.
- Use Font Awesome for icons: <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css">
- Make it self-contained in one file.
- Do NOT embed the screenshot as an image; recreate everything with HTML/CSS."""

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": data_url}},
                {"type": "text", "text": "Convert this settings screenshot into a single self-contained HTML file. Output only the HTML code."},
            ],
        },
    ]

    t0 = time.time()
    result = call_ark(messages, max_tokens=8000)
    elapsed = time.time() - t0
    content = result["choices"][0]["message"]["content"]
    usage = result.get("usage", {})

    html_code = strip_markdown_fences(content)
    HTML_PREVIEW.write_text(html_code, encoding="utf-8")

    print(f"  耗时: {elapsed:.1f}s")
    print(f"  Token: in={usage.get('prompt_tokens')} out={usage.get('completion_tokens')} total={usage.get('total_tokens')}")
    print(f"  HTML 长度: {len(html_code)} chars")
    print(f"  输出: {HTML_PREVIEW}")
    return html_code


# ============================================================
# 阶段 3: Kotlin Compose 代码生成
# ============================================================
def stage3_kotlin_generate(analysis: dict) -> str:
    print("\n" + "=" * 60)
    print("阶段 3: Kotlin Compose 代码生成 (doubao-seed-2-1-turbo)")
    print("=" * 60)

    data_url = image_to_data_url(str(SCREENSHOT))
    ui_desc = analysis.get("ui_description", {})
    components = ui_desc.get("components", [])

    # 构造组件摘要给 LLM 参考
    comp_summary = "\n".join(
        f"  - {c['type']}: {c['text']} ({c.get('position', '')}) {c.get('description', '')}"
        for c in components
    )

    system_prompt = f"""You are an expert Android Kotlin Compose developer. Convert the provided screenshot into a single Kotlin file using Jetpack Compose (Material 3).

The screenshot shows: {ui_desc.get('title', 'Settings - Sound & Display')}
Layout: {ui_desc.get('layout', 'horizontal')} (sidebar + content area)
Components:
{comp_summary}

Rules:
- Output ONLY valid Kotlin code, no explanations, no markdown fences.
- Package: com.e2e.settings
- Use Material 3 components (Surface, Text, Switch, Slider, Icon, IconButton, OutlinedTextField, etc.)
- Single @Composable function named SoundDisplaySettings()
- Include a lightColorScheme with primary color #1677ff
- Use Column/Row for layout, not ConstraintLayout
- Include all necessary imports
- Use Icons.Default for icons (VolumeUp, VolumeDown, BrightnessHigh, Search, Close)
- The layout has a left sidebar (navigation list) and right content area (switches + sliders)
- Switch states: 扬声器=on, 按键音=on, 麦克风=off
- Use RoundedCornerShape for cards
- Match the screenshot's colors and spacing as closely as possible"""

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": data_url}},
                {"type": "text", "text": "Convert this settings screenshot into a single Kotlin Compose file. Output only the Kotlin code."},
            ],
        },
    ]

    t0 = time.time()
    result = call_ark(messages, max_tokens=16000)
    elapsed = time.time() - t0
    content = result["choices"][0]["message"]["content"]
    usage = result.get("usage", {})

    kotlin_code = strip_markdown_fences(content)
    # 去除可能的 package 行（我们用项目内的）
    kotlin_code = re.sub(r'^package\s+\S+', '', kotlin_code).strip()

    KOTLIN_FILE.write_text(kotlin_code, encoding="utf-8")

    print(f"  耗时: {elapsed:.1f}s")
    print(f"  Token: in={usage.get('prompt_tokens')} out={usage.get('completion_tokens')} total={usage.get('total_tokens')}")
    print(f"  代码长度: {len(kotlin_code)} chars, {kotlin_code.count(chr(10))} lines")
    print(f"  输出: {KOTLIN_FILE}")
    return kotlin_code


# ============================================================
# 阶段 4: 编译验证
# ============================================================
def stage4_compile(kotlin_code: str) -> dict:
    print("\n" + "=" * 60)
    print("阶段 4: Gradle 编译验证")
    print("=" * 60)

    # 复制 Kotlin 文件到 Android 项目
    target_kt = ANDROID_PROJECT / "app" / "src" / "main" / "java" / "com" / "e2e" / "settings" / "MainActivity.kt"
    # 先备份原文件
    backup_path = target_kt.parent / "MainActivity.kt.bak"
    if target_kt.exists():
        shutil.copy2(target_kt, backup_path)

    # 写入 package + 生成代码
    full_code = "package com.e2e.settings\n\n" + kotlin_code
    target_kt.write_text(full_code, encoding="utf-8")
    print(f"  已写入: {target_kt}")

    # 运行 Gradle
    gradlew = str(ANDROID_PROJECT / "gradlew.bat")
    result = {"gradle_build": False, "apk_path": None, "error": None, "duration": 0}

    t0 = time.time()
    try:
        proc = subprocess.run(
            [gradlew, "assembleDebug", "--quiet"],
            cwd=str(ANDROID_PROJECT),
            capture_output=True,
            text=True,
            timeout=180,
        )
        result["duration"] = round(time.time() - t0, 1)
        log = proc.stdout + proc.stderr
        COMPILE_LOG.write_text(log, encoding="utf-8")

        if proc.returncode == 0:
            result["gradle_build"] = True
            apk_path = ANDROID_PROJECT / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
            if apk_path.exists():
                result["apk_path"] = str(apk_path)
                result["apk_size"] = apk_path.stat().st_size
            print(f"  BUILD SUCCESSFUL ({result['duration']}s)")
            if result.get("apk_size"):
                print(f"  APK: {result['apk_size']:,} bytes")
        else:
            result["error"] = log[-2000:] if len(log) > 2000 else log
            print(f"  BUILD FAILED ({result['duration']}s)")
            print(f"  错误: {result['error'][-500:]}")
    except subprocess.TimeoutExpired:
        result["duration"] = round(time.time() - t0, 1)
        result["error"] = "Timeout (180s)"
        print(f"  编译超时 ({result['duration']}s)")
    except Exception as e:
        result["error"] = str(e)
        print(f"  异常: {e}")

    # 恢复备份
    if backup_path.exists():
        shutil.copy2(backup_path, target_kt)
        backup_path.unlink()

    print(f"  编译日志: {COMPILE_LOG}")
    return result


# ============================================================
# 阶段 5: HTML 报告生成
# ============================================================
def stage5_report(analysis: dict, html_code: str, kotlin_code: str, compile_result: dict):
    print("\n" + "=" * 60)
    print("阶段 5: 自包含 HTML 报告生成")
    print("=" * 60)

    # 源截图 base64
    screenshot_b64 = base64.b64encode(SCREENSHOT.read_bytes()).decode("ascii")
    # HTML 预览用 data URL 嵌入 iframe
    html_b64 = base64.b64encode(html_code.encode("utf-8")).decode("ascii")
    html_data_url = f"data:text/html;base64,{html_b64}"

    # 区域分析表格行
    regions_rows = "".join(
        f'<tr><td>{k}</td><td>{v["lum_mean"]}</td><td>rgb({v["rgb_mean"][0]}, {v["rgb_mean"][1]}, {v["rgb_mean"][2]})</td></tr>'
        for k, v in analysis["regions_vertical"].items()
    )

    # 分析数据
    top_colors_html = "".join(
        f'<div style="display:inline-block;margin:2px;text-align:center">'
        f'<div style="width:40px;height:40px;background:{c["hex"]};border:1px solid #ddd;border-radius:4px"></div>'
        f'<div style="font-size:10px">{c["hex"]}</div>'
        f'<div style="font-size:9px;color:#666">{c["pct"]}%</div></div>'
        for c in analysis["top_colors"]
    )

    # 组件列表
    components = analysis.get("ui_description", {}).get("components", [])
    components_html = "".join(
        f'<tr><td>{i+1}</td><td><code>{c["type"]}</code></td><td>{c["text"]}</td><td>{c.get("position","")}</td><td style="font-size:12px;color:#666">{c.get("description","")}</td></tr>'
        for i, c in enumerate(components)
    )

    # 编译结果
    if compile_result["gradle_build"]:
        compile_html = f'<div style="color:green;font-weight:bold">BUILD SUCCESSFUL</div><div>耗时: {compile_result["duration"]}s</div>'
        if compile_result.get("apk_size"):
            compile_html += f'<div>APK: {compile_result["apk_size"]:,} bytes</div>'
    else:
        error = compile_result.get("error", "unknown")
        compile_html = f'<div style="color:red;font-weight:bold">BUILD FAILED</div><div>耗时: {compile_result["duration"]}s</div><pre style="max-height:300px;overflow:auto;background:#f5f5f5;padding:10px;border-radius:4px;font-size:11px">{error}</pre>'

    # Kotlin 代码 HTML 转义
    import html as html_mod
    kotlin_escaped = html_mod.escape(kotlin_code)
    html_escaped = html_mod.escape(html_code)

    report = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>截图转 Kotlin Compose 全流程报告</title>
<style>
body {{ font-family: -apple-system, "Microsoft YaHei", sans-serif; margin: 0; padding: 20px; background: #f8f9fa; color: #333; }}
h1 {{ color: #1677ff; border-bottom: 2px solid #1677ff; padding-bottom: 10px; }}
h2 {{ color: #495057; margin-top: 30px; border-left: 4px solid #1677ff; padding-left: 10px; }}
.card {{ background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 20px; margin: 15px 0; }}
pre {{ background: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 6px; overflow-x: auto; font-size: 12px; max-height: 500px; }}
table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
th {{ background: #f1f3f5; }}
img.screenshot {{ max-width: 100%; border: 1px solid #ddd; border-radius: 8px; }}
.stat {{ display: inline-block; margin: 5px 15px; text-align: center; }}
.stat .num {{ font-size: 28px; font-weight: bold; color: #1677ff; }}
.stat .label {{ font-size: 12px; color: #666; }}
</style>
</head>
<body>

<h1>Screenshot → Kotlin Compose 全流程报告</h1>
<div style="color:#666;font-size:13px">生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | 模型: {MODEL}</div>

<div class="card">
<h2>📸 源截图</h2>
<img class="screenshot" src="data:image/png;base64,{screenshot_b64}" alt="源截图" />
<div style="margin-top:10px;color:#666;font-size:13px">
  尺寸: {analysis['size']['width']}x{analysis['size']['height']} |
  亮度: {analysis['luminance']['mean']} (暗 {analysis['luminance']['dark_pct']}% / 亮 {analysis['luminance']['light_pct']}%)
</div>
</div>

<div class="card">
<h2>🎨 色调分析</h2>
<div>{top_colors_html}</div>
<h3>区域分析（上/中/下）</h3>
<table>
<tr><th>区域</th><th>平均亮度</th><th>平均 RGB</th></tr>
{regions_rows}
</table>
<h3>分割线</h3>
<div>水平: {analysis['h_dividers']} | 垂直: {analysis['v_dividers']}</div>
</div>

<div class="card">
<h2>🧩 UI 组件识别</h2>
<table>
<tr><th>#</th><th>类型</th><th>文本</th><th>位置</th><th>描述</th></tr>
{components_html}
</table>
</div>

<div class="card">
<h2>📄 HTML 预览 (Tailwind CSS)</h2>
<iframe src="{html_data_url}" style="width:100%;height:500px;border:1px solid #ddd;border-radius:6px"></iframe>
<details><summary style="cursor:pointer;margin-top:10px;color:#1677ff">查看 HTML 源码</summary><pre>{html_escaped}</pre></details>
</div>

<div class="card">
<h2>⚡ Kotlin Compose 代码</h2>
<div class="stat"><div class="num">{kotlin_code.count(chr(10))}</div><div class="label">行数</div></div>
<div class="stat"><div class="num">{len(kotlin_code)}</div><div class="label">字符数</div></div>
<div class="stat"><div class="num">{kotlin_code.count("import")}</div><div class="label">import 数</div></div>
<pre>{kotlin_escaped}</pre>
</div>

<div class="card">
<h2>🔨 Gradle 编译验证</h2>
{compile_html}
</div>

</body>
</html>"""

    REPORT_HTML.write_text(report, encoding="utf-8")
    print(f"  报告: {REPORT_HTML}")
    print(f"  大小: {REPORT_HTML.stat().st_size:,} bytes")


# ============================================================
# 主流程
# ============================================================
def main():
    print("=" * 60)
    print("Screenshot → Kotlin Compose 全流程管线")
    print(f"模型: {MODEL}")
    print(f"截图: {SCREENSHOT}")
    print(f"输出: {RUN_DIR}")
    print("=" * 60)

    if not SCREENSHOT.exists():
        print(f"ERROR: 截图不存在: {SCREENSHOT}")
        sys.exit(1)

    # 阶段 1
    analysis = stage1_analyze()

    # 阶段 2
    html_code = stage2_html_preview(analysis)

    # 阶段 3
    kotlin_code = stage3_kotlin_generate(analysis)

    # 阶段 4
    compile_result = stage4_compile(kotlin_code)

    # 阶段 5
    stage5_report(analysis, html_code, kotlin_code, compile_result)

    print("\n" + "=" * 60)
    print("全流程完成!")
    print("=" * 60)
    print(f"报告: {REPORT_HTML}")


if __name__ == "__main__":
    main()
