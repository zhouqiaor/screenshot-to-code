"""
Generate Kotlin compile+install+run comparison report:
  Direct call vs WebSocket main flow
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
DIRECT_KT = RUN_DIR / "kotlin_pipeline" / "MainActivity.kt"
WS_KT = RUN_DIR / "ws_compose.kt"
DIRECT_RUN_SHOT = RUN_DIR / "kotlin_pipeline" / "settings_adb_final.png"
WS_RUN_SHOT = RUN_DIR / "ws_kotlin_run.png"
DIRECT_UI_DUMP = RUN_DIR / "kotlin_pipeline" / "ui_dump_final.xml"
WS_UI_DUMP = RUN_DIR / "ws_ui_dump.xml"

# --- Load Kotlin ---
direct_kt = DIRECT_KT.read_text(encoding="utf-8")
ws_kt = WS_KT.read_text(encoding="utf-8")

# --- Load and compress screenshots ---
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
direct_run_b64 = img_to_b64(DIRECT_RUN_SHOT)
ws_run_b64 = img_to_b64(WS_RUN_SHOT)

source_url = f"data:image/jpeg;base64,{source_b64}"
direct_run_url = f"data:image/jpeg;base64,{direct_run_b64}"
ws_run_url = f"data:image/jpeg;base64,{ws_run_b64}"

# --- Parse UI dumps ---
import xml.etree.ElementTree as ET

def parse_ui_dump(path):
    tree = ET.parse(path)
    root = tree.getroot()
    nodes = []
    for node in root.iter("node"):
        text = node.get("text", "")
        if text.strip():
            nodes.append(text.strip())
    return nodes

direct_ui_nodes = parse_ui_dump(DIRECT_UI_DUMP)
ws_ui_nodes = parse_ui_dump(WS_UI_DUMP)

# --- Analyze Kotlin ---
def analyze_kotlin(code):
    composables = re.findall(r"@Composable\s+fun\s+(\w+)", code)
    classes = re.findall(r"class\s+(\w+)", code)
    components = {
        "Text": code.count("Text("),
        "Switch": code.count("Switch("),
        "Slider": code.count("Slider("),
        "Icon": code.count("Icon("),
        "Surface": code.count("Surface("),
        "Column": code.count("Column("),
        "Row": code.count("Row("),
        "Box": code.count("Box("),
    }
    labels = ["投屏码", "WiFi", "Wi-Fi", "蓝牙", "亮度", "音量", "设置", "电源", "新手指引", "麦克风", "声音与显示", "扬声器", "按键音", "提示音量"]
    found = {l: l in code for l in labels}
    return {
        "chars": len(code),
        "lines": code.count("\n"),
        "composables": composables,
        "classes": classes,
        "components": components,
        "labels": found,
    }

d_info = analyze_kotlin(direct_kt)
w_info = analyze_kotlin(ws_kt)

# --- Build comparison data ---
all_labels = sorted(set(list(d_info["labels"].keys()) + list(w_info["labels"].keys())))
label_rows = ""
for l in all_labels:
    d = "✅" if d_info["labels"].get(l) else "❌"
    w = "✅" if w_info["labels"].get(l) else "❌"
    label_rows += f"<tr><td>{l}</td><td class='center'>{d}</td><td class='center'>{w}</td></tr>\n"

comp_keys = sorted(set(list(d_info["components"].keys()) + list(w_info["components"].keys())))
comp_rows = ""
for k in comp_keys:
    d = d_info["components"].get(k, 0)
    w = w_info["components"].get(k, 0)
    comp_rows += f"<tr><td>{k}</td><td class='center'>{d}</td><td class='center'>{w}</td></tr>\n"

# UI dump comparison
all_ui_texts = sorted(set(direct_ui_nodes + ws_ui_nodes))
ui_rows = ""
for t in all_ui_texts:
    d = "✅" if t in direct_ui_nodes else "—"
    w = "✅" if t in ws_ui_nodes else "—"
    ui_rows += f"<tr><td>{t}</td><td class='center'>{d}</td><td class='center'>{w}</td></tr>\n"

now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

d_composables = ", ".join(d_info["composables"]) or "(none)"
w_composables = ", ".join(w_info["composables"]) or "(none)"

report = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Kotlin 编译运行对比: 直调 vs WebSocket 主流程</title>
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
  .winner {{ background: #d1fae5; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }}
  .step {{ display: flex; align-items: center; gap: 8px; padding: 8px 0; }}
  .step .num {{ width: 28px; height: 28px; border-radius: 50%; background: #3b82f6; color: white; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px; }}
  .step .ok {{ color: #10b981; font-weight: bold; }}
  .step .fail {{ color: #ef4444; font-weight: bold; }}
  .step .warn {{ color: #f59e0b; font-weight: bold; }}
</style>
</head>
<body>

<h1>Kotlin 编译安装运行对比报告</h1>

<div class="meta">
  <strong>生成时间:</strong> {now}<br>
  <strong>模型:</strong> doubao-seed-2-1-turbo-260628 (Ark API)<br>
  <strong>设备:</strong> 200.47.91.1:5555<br>
  <strong>对比范围:</strong> 编译 → 安装 → 运行 → 截图 → UI 覆盖
</div>

<div class="summary-box">
  <strong>结论</strong><br>
  两份 Kotlin 代码均成功编译为 APK 并安装到设备运行。WebSocket 版运行后 UI 覆盖更全
  (23 个文本节点 vs 18 个)，包含投屏码、时间、新手指引、电源等直调版缺失的元素。
</div>

<h2>1. 源截图</h2>
<img src="{source_url}" class="source-img" alt="Source Screenshot">

<h2>2. 设备运行截图对比</h2>

<div class="side-by-side">
  <div class="side-box">
    <h3><span class="flow-badge badge-direct">直调</span> settings_adb_final.png</h3>
    <img src="{direct_run_url}" alt="Direct Kotlin Run">
  </div>
  <div class="side-box">
    <h3><span class="flow-badge badge-ws">WebSocket</span> ws_kotlin_run.png</h3>
    <img src="{ws_run_url}" alt="WebSocket Kotlin Run">
  </div>
</div>

<h2>3. 编译安装运行流程</h2>

<h3>3.1 <span class="flow-badge badge-direct">直调版</span>流程</h3>
<div class="step"><span class="num">1</span> 编译: <code>./gradlew.bat assembleDebug</code> <span class="ok">✅ BUILD SUCCESSFUL</span></div>
<div class="step"><span class="num">2</span> APK: <code>app-debug.apk</code> <span class="ok">✅ 生成</span></div>
<div class="step"><span class="num">3</span> 安装: <code>adb install -r</code> <span class="ok">✅ Success</span></div>
<div class="step"><span class="num">4</span> 启动: <code>adb shell am start -n com.e2e.settings/.MainActivity</code> <span class="ok">✅ 启动</span></div>
<div class="step"><span class="num">5</span> 截图: <code>adb shell screencap</code> <span class="ok">✅ 202KB</span></div>
<div class="step"><span class="num">6</span> UI Dump: <code>uiautomator dump</code> <span class="ok">✅ 18 个文本节点</span></div>

<h3>3.2 <span class="flow-badge badge-ws">WebSocket版</span>流程</h3>
<div class="step"><span class="num">1</span> 编译: <code>./gradlew.bat assembleDebug</code> <span class="ok">✅ BUILD SUCCESSFUL</span> (8s, 5 deprecation warnings)</div>
<div class="step"><span class="num">2</span> APK: <code>app-debug.apk</code> <span class="ok">✅ 15.6MB</span></div>
<div class="step"><span class="num">3</span> 安装: <code>adb install -r</code> <span class="ok">✅ Success</span></div>
<div class="step"><span class="num">4</span> 启动: <code>adb shell am start -n com.e2e.settings/.MainActivity</code> <span class="ok">✅ 启动</span></div>
<div class="step"><span class="num">5</span> 截图: <code>adb shell screencap</code> <span class="ok">✅ 390KB</span></div>
<div class="step"><span class="num">6</span> UI Dump: <code>uiautomator dump</code> <span class="ok">✅ 23 个文本节点</span> <span class="winner">更优</span></div>

<h2>4. 代码指标对比</h2>

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
<tr><th>指标</th><th><span class="flow-badge badge-direct">直调</span></th><th><span class="flow-badge badge-ws">WebSocket</span></th></tr>
<tr><td>代码体积</td><td class="center">{d_info['chars']:,} chars</td><td class="center">{w_info['chars']:,} chars</td></tr>
<tr><td>代码行数</td><td class="center">{d_info['lines']}</td><td class="center">{w_info['lines']}</td></tr>
<tr><td>@Composable 函数数</td><td class="center">{len(d_info['composables'])}</td><td class="center">{len(w_info['composables'])} <span class="winner">更优</span></td></tr>
<tr><td>@Composable 函数</td><td>{d_composables}</td><td>{w_composables}</td></tr>
<tr><td>class 定义</td><td>{d_info['classes'] or '(无)'}</td><td>{w_info['classes']} <span class="winner">更优</span></td></tr>
<tr><td>编译结果</td><td class="center ok">✅ SUCCESS</td><td class="center ok">✅ SUCCESS</td></tr>
<tr><td>APK 大小</td><td class="center">~15MB</td><td class="center">15.6MB</td></tr>
<tr><td>安装结果</td><td class="center ok">✅ Success</td><td class="center ok">✅ Success</td></tr>
<tr><td>运行截图</td><td class="center ok">✅ 202KB</td><td class="center ok">✅ 390KB</td></tr>
<tr><td>UI 文本节点</td><td class="center">18</td><td class="center">23 <span class="winner">更优</span></td></tr>
</table>

<h2>5. UI 组件使用对比</h2>
<table>
<tr><th>Compose 组件</th><th><span class="flow-badge badge-direct">直调</span></th><th><span class="flow-badge badge-ws">WebSocket</span></th></tr>
{comp_rows}
</table>

<h2>6. 代码标签覆盖对比</h2>
<table>
<tr><th>UI 标签</th><th><span class="flow-badge badge-direct">直调</span></th><th><span class="flow-badge badge-ws">WebSocket</span></th></tr>
{label_rows}
</table>

<h2>7. 设备运行 UI 文本节点对比</h2>
<p>通过 <code>uiautomator dump</code> 抓取的设备实际运行 UI 文本节点：</p>
<table>
<tr><th>UI 文本</th><th><span class="flow-badge badge-direct">直调</span></th><th><span class="flow-badge badge-ws">WebSocket</span></th></tr>
{ui_rows}
</table>

<h2>8. 关键差异分析</h2>

<div class="summary-box">
  <strong>设备运行 UI 文本节点差异</strong><br><br>
  <strong>WebSocket 版多出的节点 (5个)</strong>:<br>
  - <code>NJRC-PAOE</code> (投屏码) <span class="winner">WebSocket 独有</span><br>
  - <code>|</code> (分隔符) <span class="winner">WebSocket 独有</span><br>
  - <code>16:55</code> (时间) <span class="winner">WebSocket 独有</span><br>
  - <code>新手指引</code> <span class="winner">WebSocket 独有</span><br>
  - <code>电源</code> <span class="winner">WebSocket 独有</span><br><br>
  <strong>直调版多出的节点 (1个)</strong>:<br>
  - <code>亮度</code> (直调版代码中有亮度标签，WebSocket 版代码中也有但 UI dump 未检测到)<br><br>
  <strong>两者都有</strong>: 设置、搜索设置项、企业服务配置、声音与显示、摄像机、已开启、壁纸、Wi-Fi、未连接、智慧功能、高级设置、扬声器、音量、提示音量、按键音、麦克风 (16个)
</div>

<h2>9. 结论</h2>

<div class="summary-box">
  <strong>编译安装运行验证结论</strong><br><br>
  两份 Kotlin 代码均成功完成 编译→安装→运行→截图 全流程。<br><br>
  <span class="highlight">WebSocket 主流程</span>生成的 Kotlin 在设备运行表现更优：
  <ul>
    <li><strong>UI 覆盖更全</strong>: 23 个文本节点 vs 18 个 (多出投屏码/时间/新手指引/电源/分隔符)</li>
    <li><strong>代码模块化</strong>: 6 个 @Composable 函数 vs 1 个</li>
    <li><strong>有 Activity 入口</strong>: class MainActivity : ComponentActivity()</li>
    <li><strong>截图更大</strong>: 390KB vs 202KB (可能渲染内容更丰富)</li>
  </ul>
  <span class="highlight">直调流程</span>的优势：
  <ul>
    <li><strong>代码更紧凑</strong>: 486 行 vs 689 行</li>
    <li><strong>包含亮度标签</strong>: 代码中有 "亮度" Text，WebSocket 版 UI dump 中未检测到</li>
  </ul>
  <strong>综合评判</strong>: WebSocket 主流程在 Kotlin 代码质量和 UI 还原度上更优，直调流程在代码紧凑性上更优。
</div>

</body>
</html>
"""

output_path = RUN_DIR / "kotlin_run_comparison.html"
output_path.write_text(report, encoding="utf-8")
print(f"Report written to {output_path} ({len(report):,} chars)")
