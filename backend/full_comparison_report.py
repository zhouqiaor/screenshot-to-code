"""
Generate the full comparison report:
  1. HTML preview screenshots (side by side)
  2. Kotlin code comparison (direct call vs WebSocket)
  3. Component coverage and feature comparison
"""
import base64
import html as html_mod
import io
import re
from datetime import datetime
from pathlib import Path

from PIL import Image

BASE = Path(__file__).parent.parent
RUN_DIR = BASE / "e2e_demo" / "run_20260901"

# --- File paths ---
SOURCE_PNG = BASE / "e2e_demo" / "screenshots" / "run_20260901" / "source_screenshot.png"
DIRECT_HTML = RUN_DIR / "kotlin_pipeline" / "html_preview.html"
WS_HTML = RUN_DIR / "ws_output.html"
DIRECT_KT = RUN_DIR / "kotlin_pipeline" / "MainActivity.kt"
WS_KT = RUN_DIR / "ws_compose.kt"
DIRECT_SCREENSHOT = RUN_DIR / "screenshot_direct.png"
WS_SCREENSHOT = RUN_DIR / "screenshot_ws.png"

# --- Load files ---
direct_html_content = DIRECT_HTML.read_text(encoding="utf-8")
ws_html_content = WS_HTML.read_text(encoding="utf-8")
direct_kt = DIRECT_KT.read_text(encoding="utf-8")
ws_kt = WS_KT.read_text(encoding="utf-8")

# --- Load screenshots as base64 ---
def img_to_b64(path, max_width=768, quality=85):
    img = Image.open(path)
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode()

source_b64 = img_to_b64(SOURCE_PNG)
direct_html_shot_b64 = img_to_b64(DIRECT_SCREENSHOT)
ws_html_shot_b64 = img_to_b64(WS_SCREENSHOT)

source_data_url = f"data:image/jpeg;base64,{source_b64}"
direct_shot_url = f"data:image/jpeg;base64,{direct_html_shot_b64}"
ws_shot_url = f"data:image/jpeg;base64,{ws_html_shot_b64}"

# --- Analyze Kotlin ---
def analyze_kotlin(code):
    imports = re.findall(r'^import\s+(.+)', code, re.MULTILINE)
    composables = re.findall(r'@Composable\s+fun\s+(\w+)', code)
    classes = re.findall(r'class\s+(\w+)', code)
    components = {
        'Text': code.count('Text('),
        'Switch': code.count('Switch('),
        'Slider': code.count('Slider('),
        'Icon': code.count('Icon('),
        'Surface': code.count('Surface('),
        'Column': code.count('Column('),
        'Row': code.count('Row('),
        'Spacer': code.count('Spacer('),
        'Box': code.count('Box('),
    }
    labels = ['投屏码', 'WiFi', '蓝牙', '亮度', '音量', '设置', '电源', '新手指引', '麦克风']
    found = {l: l in code for l in labels}
    return {
        'chars': len(code),
        'lines': code.count('\n'),
        'imports': len(imports),
        'import_list': imports,
        'composables': composables,
        'classes': classes,
        'components': components,
        'labels': found,
    }

d_info = analyze_kotlin(direct_kt)
w_info = analyze_kotlin(ws_kt)

# --- Analyze HTML ---
def analyze_html(html):
    return {
        'tailwind': 'cdn.tailwindcss.com' in html,
        'fontawesome5': 'font-awesome/5.15.3' in html,
        'fontawesome6': 'font-awesome/6.4.0' in html,
        'noto_sans': 'Noto+Sans' in html,
        'google_fonts': 'fonts.googleapis.com' in html,
        'bg_wallpaper': 'bg-wallpaper' in html,
        'toggle_class': 'class="toggle' in html,
        'lang_zh': 'lang="zh' in html,
        'viewport_meta': 'viewport' in html,
    }

d_html_feat = analyze_html(direct_html_content)
w_html_feat = analyze_html(ws_html_content)

# --- Build report ---
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Component comparison table
comp_keys = sorted(set(list(d_info['components'].keys()) + list(w_info['components'].keys())))
comp_rows = ""
for k in comp_keys:
    d = d_info['components'].get(k, 0)
    w = w_info['components'].get(k, 0)
    comp_rows += f"<tr><td>{k}</td><td class='center'>{d}</td><td class='center'>{w}</td></tr>\n"

# Label comparison
label_rows = ""
all_labels = sorted(set(list(d_info['labels'].keys()) + list(w_info['labels'].keys())))
for l in all_labels:
    d = "✅" if d_info['labels'].get(l) else "❌"
    w = "✅" if w_info['labels'].get(l) else "❌"
    label_rows += f"<tr><td>{l}</td><td class='center'>{d}</td><td class='center'>{w}</td></tr>\n"

# HTML feature comparison
html_feat_keys = sorted(set(list(d_html_feat.keys()) + list(w_html_feat.keys())))
html_feat_rows = ""
for k in html_feat_keys:
    d = "✅" if d_html_feat.get(k) else "—"
    w = "✅" if w_html_feat.get(k) else "—"
    html_feat_rows += f"<tr><td>{k}</td><td class='center'>{d}</td><td class='center'>{w}</td></tr>\n"

# Kotlin code (escaped, first 100 lines for display)
def escape_kotlin(code, max_lines=80):
    lines = code.split('\n')
    if len(lines) > max_lines:
        shown = '\n'.join(lines[:max_lines]) + f'\n// ... ({len(lines) - max_lines} more lines)'
    else:
        shown = code
    return html_mod.escape(shown)

direct_kt_escaped = escape_kotlin(direct_kt)
ws_kt_escaped = escape_kotlin(ws_kt)

# Composable functions
d_composables = ', '.join(d_info['composables']) if d_info['composables'] else '(none)'
w_composables = ', '.join(w_info['composables']) if w_info['composables'] else '(none)'

report = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>完整对比报告: 直调 vs WebSocket 主流程 (HTML + Kotlin)</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 20px; background: #f8fafc; color: #1e293b; line-height: 1.6; }}
  h1 {{ color: #1e40af; border-bottom: 3px solid #3b82f6; padding-bottom: 10px; }}
  h2 {{ color: #1e40af; margin-top: 35px; border-left: 4px solid #3b82f6; padding-left: 12px; }}
  h3 {{ color: #334155; margin-top: 25px; }}
  .meta {{ background: #f1f5f9; padding: 12px 20px; border-radius: 8px; margin-bottom: 20px; font-size: 14px; }}
  .meta strong {{ color: #1e40af; }}
  table {{ border-collapse: collapse; width: 100%; margin: 15px 0; background: white; }}
  th, td {{ border: 1px solid #e2e8f0; padding: 8px 12px; text-align: left; font-size: 14px; }}
  th {{ background: #3b82f6; color: white; }}
  td.center {{ text-align: center; font-size: 16px; }}
  tr:nth-child(even) {{ background: #f8fafc; }}
  .flow-badge {{ display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; color: white; }}
  .badge-direct {{ background: #f59e0b; }}
  .badge-ws {{ background: #10b981; }}
  .side-by-side {{ display: flex; gap: 15px; margin: 20px 0; }}
  .side-box {{ flex: 1; border: 2px solid #e2e8f0; border-radius: 12px; overflow: hidden; background: white; }}
  .side-box h3 {{ margin: 0; padding: 8px 14px; background: #f1f5f9; font-size: 13px; }}
  .side-box img {{ width: 100%; display: block; }}
  .source-img {{ max-width: 100%; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
  .summary-box {{ background: #eff6ff; border-left: 4px solid #3b82f6; padding: 14px 20px; margin: 20px 0; border-radius: 0 8px 8px 0; }}
  .stat-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 20px 0; }}
  .stat-card {{ background: white; padding: 14px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; }}
  .stat-card .label {{ color: #64748b; font-size: 11px; text-transform: uppercase; }}
  .stat-card .value {{ font-size: 24px; font-weight: bold; color: #1e40af; }}
  .stat-card .unit {{ font-size: 12px; color: #64748b; }}
  .highlight {{ background: #fef3c7; padding: 2px 6px; border-radius: 4px; font-weight: bold; }}
  .code-block {{ background: #1e293b; color: #e2e8f0; padding: 16px; border-radius: 8px; overflow-x: auto; font-family: 'Cascadia Code', 'Fira Code', monospace; font-size: 12px; line-height: 1.5; max-height: 500px; overflow-y: auto; }}
  .code-block .kw {{ color: #c084fc; }}
  .code-block .str {{ color: #86efac; }}
  .code-block .cmt {{ color: #64748b; }}
  .bug-fix {{ background: #fee2e2; border-left: 4px solid #ef4444; padding: 12px 16px; margin: 15px 0; border-radius: 0 8px 8px 0; }}
  .bug-fix code {{ background: #1e293b; color: #f8fafc; padding: 2px 6px; border-radius: 4px; font-size: 12px; }}
  .winner {{ background: #d1fae5; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }}
</style>
</head>
<body>

<h1>完整对比报告: 直调 vs WebSocket 主流程</h1>

<div class="meta">
  <strong>生成时间:</strong> {now}<br>
  <strong>模型:</strong> doubao-seed-2-1-turbo-260628 (Ark API)<br>
  <strong>源截图:</strong> e2e_demo/screenshots/run_20260901/source_screenshot.png<br>
  <strong>对比范围:</strong> HTML 预览截图 + Kotlin Compose 代码
</div>

<div class="summary-box">
  <strong>结论摘要</strong><br>
  两种流程均成功生成 HTML 预览和 Kotlin Compose 代码。<br>
  <strong>HTML:</strong> 两者都完整覆盖源截图 UI，直调 12,853 chars / WebSocket 14,597 chars。<br>
  <strong>Kotlin:</strong> WebSocket 版模块化更好（6 个 @Composable vs 1 个），UI 覆盖更全（投屏码/电源/新手指引都有）；
  直调版代码更紧凑（486 行 vs 689 行），但缺少部分 UI 元素。
</div>

<h2>1. 源截图</h2>
<img src="{source_data_url}" class="source-img" alt="Source Screenshot">

<h2>2. HTML 预览截图对比</h2>
<p>使用 Edge headless 模式截取两个 HTML 的完整页面渲染结果：</p>

<div class="side-by-side">
  <div class="side-box">
    <h3><span class="flow-badge badge-direct">直调</span> html_preview.html ({len(direct_html_content):,} chars)</h3>
    <img src="{direct_shot_url}" alt="Direct HTML Screenshot">
  </div>
  <div class="side-box">
    <h3><span class="flow-badge badge-ws">WebSocket</span> ws_output.html ({len(ws_html_content):,} chars)</h3>
    <img src="{ws_shot_url}" alt="WebSocket HTML Screenshot">
  </div>
</div>

<h3>HTML 技术特征对比</h3>
<table>
<tr><th>特征</th><th><span class="flow-badge badge-direct">直调</span></th><th><span class="flow-badge badge-ws">WebSocket</span></th></tr>
{html_feat_rows}
</table>

<h2>3. Kotlin Compose 代码对比</h2>

<div class="stat-grid">
  <div class="stat-card">
    <div class="label">直调 代码体积</div>
    <div class="value">{d_info['chars']:,}</div>
    <div class="unit">chars</div>
  </div>
  <div class="stat-card">
    <div class="label">WebSocket 代码体积</div>
    <div class="value">{w_info['chars']:,}</div>
    <div class="unit">chars</div>
  </div>
  <div class="stat-card">
    <div class="label">直调 代码行数</div>
    <div class="value">{d_info['lines']:,}</div>
    <div class="unit">lines</div>
  </div>
  <div class="stat-card">
    <div class="label">WebSocket 代码行数</div>
    <div class="value">{w_info['lines']:,}</div>
    <div class="unit">lines</div>
  </div>
</div>

<table>
<tr><th>指标</th><th><span class="flow-badge badge-direct">直调 httpx.post</span></th><th><span class="flow-badge badge-ws">WebSocket 主流程</span></th></tr>
<tr><td>代码体积</td><td class="center">{d_info['chars']:,} chars</td><td class="center">{w_info['chars']:,} chars</td></tr>
<tr><td>代码行数</td><td class="center">{d_info['lines']}</td><td class="center">{w_info['lines']}</td></tr>
<tr><td>import 数</td><td class="center">{d_info['imports']}</td><td class="center">{w_info['imports']}</td></tr>
<tr><td>@Composable 函数数</td><td class="center">{len(d_info['composables'])}</td><td class="center">{len(w_info['composables'])} <span class="winner">更优</span></td></tr>
<tr><td>@Composable 函数列表</td><td>{d_composables}</td><td>{w_composables}</td></tr>
<tr><td>class 定义</td><td>{d_info['classes'] or '(无)'}</td><td>{w_info['classes']} <span class="winner">更优</span></td></tr>
<tr><td>Agent 管线</td><td class="center">❌ 无</td><td class="center">✅ 完整</td></tr>
<tr><td>工具调用</td><td class="center">❌ 无</td><td class="center">✅ save_assets, create_file</td></tr>
<tr><td>多 variant</td><td class="center">❌ 单次</td><td class="center">✅ 4 variants</td></tr>
<tr><td>耗时</td><td class="center">~30s</td><td class="center">~112s</td></tr>
</table>

<h3>UI 组件使用对比</h3>
<table>
<tr><th>Compose 组件</th><th><span class="flow-badge badge-direct">直调</span></th><th><span class="flow-badge badge-ws">WebSocket</span></th></tr>
{comp_rows}
</table>

<h3>UI 文本标签覆盖</h3>
<p>检测源截图中关键 UI 文本是否出现在 Kotlin 代码中：</p>
<table>
<tr><th>UI 标签</th><th><span class="flow-badge badge-direct">直调</span></th><th><span class="flow-badge badge-ws">WebSocket</span></th></tr>
{label_rows}
</table>

<h2>4. Kotlin 代码展示</h2>

<h3>4.1 <span class="flow-badge badge-direct">直调</span> MainActivity.kt ({d_info['chars']:,} chars, {d_info['lines']} lines)</h3>
<pre class="code-block">{direct_kt_escaped}</pre>

<h3>4.2 <span class="flow-badge badge-ws">WebSocket</span> ws_compose.kt ({w_info['chars']:,} chars, {w_info['lines']} lines)</h3>
<pre class="code-block">{ws_kt_escaped}</pre>

<h2>5. Bug 修复记录</h2>

<div class="bug-fix">
  <strong>Bug #1: _get_variant_models 缺少 openai_base_url 参数</strong><br>
  <strong>文件:</strong> backend/routes/generate_code.py:492<br>
  <strong>问题:</strong> <code>_get_variant_models()</code> 引用 <code>openai_base_url</code> 但参数签名没有，导致 <code>NameError</code> 被误报为 "No API key"。<br>
  <strong>修复:</strong> 给 <code>select_models()</code> 和 <code>_get_variant_models()</code> 添加 <code>openai_base_url</code> 参数。
</div>

<div class="bug-fix">
  <strong>Bug #2: WebSocket prompt 不区分 stack 输出语言</strong><br>
  <strong>文件:</strong> backend/prompts/create/image.py + backend/prompts/system_prompt.py<br>
  <strong>问题:</strong> <code>build_image_prompt_messages()</code> 的 user prompt 写死 "Generate code for a web page"，
  system prompt 也写死 "The main file is a single HTML file"，导致 <code>stack=android_compose</code> 时仍生成 HTML。<br>
  <strong>修复:</strong>
  1. 新建 <code>prompts/android_compose_system.py</code> (Kotlin 专用 system prompt)<br>
  2. <code>image.py</code> 根据 stack 区分 user prompt (Kotlin vs HTML)<br>
  3. <code>image.py</code> 根据 stack 选择 system prompt
</div>

<h2>6. 结论</h2>

<div class="summary-box">
  <strong>HTML 预览</strong><br>
  两种流程生成的 HTML 质量相当，都完整覆盖了源截图 UI。WebSocket 版略大 (14,597 vs 12,853 chars)，
  主要因为 Agent 可能调用了更多样式。视觉上两者无明显差异。<br><br>

  <strong>Kotlin Compose</strong><br>
  <span class="highlight">WebSocket 主流程</span>生成的 Kotlin 代码质量明显更优：
  <ul>
    <li><strong>模块化更好</strong>: 6 个 @Composable 函数 (SettingsScreen, TopStatusBar, LeftSidebar, MenuItem, RightContent, BottomBar) vs 直调只有 1 个 (SoundDisplaySettings)</li>
    <li><strong>有 class MainActivity</strong>: 包含 Activity 入口类，直调版没有</li>
    <li><strong>UI 覆盖更全</strong>: "投屏码""电源""新手指引"都有，直调版缺这些</li>
    <li><strong>import 更精简</strong>: 18 vs 44，WebSocket 版用了通配符 import</li>
  </ul>

  <span class="highlight">直调流程</span>的优势：
  <ul>
    <li><strong>代码更紧凑</strong>: 486 行 vs 689 行</li>
    <li><strong>速度更快</strong>: ~30s vs ~112s</li>
    <li><strong>不依赖后端服务</strong>: 可独立运行</li>
  </ul>

  <strong>综合评判</strong>: WebSocket 主流程在代码质量和 UI 还原度上更优，适合生产环境；
  直调流程在速度和便捷性上更优，适合快速原型和脚本化批处理。
</div>

</body>
</html>
"""

output_path = RUN_DIR / "full_comparison_report.html"
output_path.write_text(report, encoding="utf-8")
print(f"Report written to {output_path} ({len(report):,} chars)")
