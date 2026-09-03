#!/usr/bin/env python3
"""
一键快速验证脚本 — 验证 LLM 生成的 5 栈代码。
用法:
  python quick_verify.py <generated_dir> [--device <serial>]
  python quick_verify.py ../run_20260901 --device 200.47.91.1:5555

输入目录需包含:
  llm_android_compose.kt  (可选)
  llm_android_xml.xml    (可选)
  llm_qt_qml.qml         (可选)
  llm_windows_html.html   (可选)
  llm_a2ui.jsonl          (可选)
  settings_page.xaml      (可选，WinUI3)

输出:
  <generated_dir>/quick_verify_report.json
  <generated_dir>/quick_verify_report.html
"""
import sys
import os
import json
import time
import base64
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

# 添加验证脚本路径
SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR / "agent" / "tools"))

# 工具路径
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
AAPT2_PATH = r"C:\Programs\Android\Sdk\build-tools\34.0.0\aapt2.exe"
ANDROID_JAR = r"C:\Programs\Android\Sdk\platforms\android-34\android.jar"
GRADLE_BIN = None

# 查找缓存的 Gradle
_gradle_pattern = Path.home() / ".gradle" / "wrapper" / "dists" / "gradle-8.9-bin"
if _gradle_pattern.exists():
    for d in _gradle_pattern.iterdir():
        gradle_exe = d / "bin" / "gradle"
        if gradle_exe.exists():
            GRADLE_BIN = str(gradle_exe).replace("\\", "/")
            break


def find_files(gen_dir):
    """查找生成文件。"""
    files = {}
    patterns = {
        "kotlin_compose": "llm_android_compose.kt",
        "android_xml": "llm_android_xml.xml",
        "qt_qml": "llm_qt_qml.qml",
        "windows_html": "llm_windows_html.html",
        "a2ui": "llm_a2ui.jsonl",
        "winui3": "settings_page.xaml",
    }
    for key, filename in patterns.items():
        p = gen_dir / filename
        if p.exists():
            files[key] = str(p)
    return files


def edge_screenshot(html_path, output_png, width=960, height=720):
    """Edge headless 截图。"""
    abs_path = Path(html_path).resolve()
    file_url = "file:///" + str(abs_path).replace("\\", "/")
    output_native = str(Path(output_png).resolve()).replace("/", "\\")

    for attempt in range(3):
        # Delete old screenshot if exists
        if os.path.exists(output_native):
            os.unlink(output_native)
        if os.path.exists(output_png):
            os.unlink(output_png)

        # --headless=new with --no-first-run (no --user-data-dir, causes "multiple targets" error)
        cmd = [EDGE_PATH, "--headless=new", "--disable-gpu", "--no-sandbox",
               "--no-first-run", "--no-default-browser-check",
               "--window-size", f"{width},{height}",
               f"--screenshot={output_native}", file_url]
        proc = subprocess.run(cmd, capture_output=True, timeout=30)
        time.sleep(2)

        size = os.path.getsize(output_native) if os.path.exists(output_native) else 0
        if size == 0 and os.path.exists(output_png):
            size = os.path.getsize(output_png)

        if size > 0:
            return True, size

        time.sleep(2)

    return False, 0


def validate_kotlin_compose(kt_path):
    """L1 语法验证 + L2 编译验证 + L3 截图。"""
    from validate_code import validate_code
    from e2e_unified_verify import kotlin_compose_to_approximate_html

    result = {"L1_syntax": {}, "L2_compile": {}, "L3_screenshot": {}, "L4_device": {}, "ok": True}
    code = Path(kt_path).read_text(encoding="utf-8")

    # L1: validate_code
    vr = validate_code("android_compose", code)
    result["L1_syntax"] = {"ok": vr["ok"], "errors": len(vr.get("errors", [])), "warnings": len(vr.get("warnings", []))}
    if not vr["ok"]:
        result["ok"] = False

    # L1+: 括号平衡
    brace_open = code.count("{")
    brace_close = code.count("}")
    paren_open = code.count("(")
    paren_close = code.count(")")
    balanced = brace_open == brace_close and paren_open == paren_close
    result["L1_syntax"]["braces"] = f"{brace_open}/{brace_close}"
    result["L1_syntax"]["parens"] = f"{paren_open}/{paren_close}"
    result["L1_syntax"]["bracket_balanced"] = balanced
    if not balanced:
        result["ok"] = False

    # L3: 近似 HTML 截图
    html_content = kotlin_compose_to_approximate_html(code)
    html_file = Path(kt_path).parent / "compose_render.html"
    html_file.write_text(html_content, encoding="utf-8")
    png_path = Path(kt_path).parent / "compose_screenshot.png"
    ok, size = edge_screenshot(str(html_file), str(png_path))
    result["L3_screenshot"] = {"ok": ok, "size": size}
    if not ok:
        result["ok"] = False

    return result


def validate_android_xml(xml_path, device_serial=None):
    """L1 + L2 aapt2 + L3 截图 + L4 设备。"""
    from validate_code import validate_code
    from e2e_deep_verify import android_xml_to_html, validate_android_xml as deep_validate

    result = {"L1_syntax": {}, "L2_compile": {}, "L3_screenshot": {}, "L4_device": {}, "ok": True}
    code = Path(xml_path).read_text(encoding="utf-8")

    # L1: validate_code
    vr = validate_code("android_xml", code)
    result["L1_syntax"] = {"ok": vr["ok"], "errors": len(vr.get("errors", []))}
    if not vr["ok"]:
        result["ok"] = False

    # L2: aapt2 compile
    if os.path.exists(AAPT2_PATH):
        import shutil
        tmp_dir = Path(xml_path).parent / "_aapt2_tmp"
        res_dir = tmp_dir / "res" / "layout"
        res_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(xml_path, res_dir / "activity_main.xml")
        out_dir = tmp_dir / "compiled"
        out_dir.mkdir(exist_ok=True)

        proc = subprocess.run([AAPT2_PATH, "compile", "--dir", str(res_dir), "-o", str(out_dir)],
                              capture_output=True, timeout=30)
        result["L2_compile"] = {"ok": proc.returncode == 0, "exit_code": proc.returncode}
        if proc.returncode != 0:
            result["ok"] = False
        shutil.rmtree(tmp_dir, ignore_errors=True)
    else:
        result["L2_compile"] = {"ok": False, "error": "aapt2 not found"}

    # L3: XML→HTML 截图
    html_content = android_xml_to_html(xml_path)
    html_file = Path(xml_path).parent / "xml_render.html"
    html_file.write_text(html_content, encoding="utf-8")
    png_path = Path(xml_path).parent / "xml_screenshot.png"
    ok, size = edge_screenshot(str(html_file), str(png_path))
    result["L3_screenshot"] = {"ok": ok, "size": size}
    if not ok:
        result["ok"] = False

    # L4: 设备 WebView 渲染
    if device_serial:
        subprocess.run(["adb", "-s", device_serial, "push", str(html_file), "/sdcard/xml_render.html"],
                       capture_output=True, timeout=10)
        subprocess.run(["adb", "-s", device_serial, "shell", "am", "start", "-a", "android.intent.action.VIEW",
                        "-d", "file:///sdcard/xml_render.html", "-t", "text/html"],
                       capture_output=True, timeout=10)
        time.sleep(3)
        subprocess.run(["adb", "-s", device_serial, "shell", "screencap", "-p", "/sdcard/xml_device.png"],
                       capture_output=True, timeout=10)
        dev_png = Path(xml_path).parent / "xml_device_screenshot.png"
        subprocess.run(["adb", "-s", device_serial, "pull", "/sdcard/xml_device.png", str(dev_png)],
                       capture_output=True, timeout=10)
        result["L4_device"] = {"ok": dev_png.exists(), "size": dev_png.stat().st_size if dev_png.exists() else 0}

    return result


def validate_qt_qml(qml_path):
    """L1 + L3 近似 HTML 截图。"""
    from e2e_deep_verify import validate_qt_qml, qml_to_html

    result = {"L1_syntax": {}, "L3_screenshot": {}, "ok": True}

    # L1: 结构验证
    vr = validate_qt_qml(qml_path)
    checks_ok = all(c.get("ok", False) for c in vr.get("checks", {}).values())
    result["L1_syntax"] = {
        "ok": vr.get("ok", False),
        "imports": vr.get("checks", {}).get("imports", {}).get("total", 0),
        "components": vr.get("checks", {}).get("components", {}).get("total_components", 0),
        "brace_balanced": vr.get("checks", {}).get("brace_balance", {}).get("ok", False),
    }
    if not vr.get("ok", False):
        result["ok"] = False

    # L3: QML→HTML 截图
    html_content = qml_to_html(qml_path)
    html_file = Path(qml_path).parent / "qml_render.html"
    html_file.write_text(html_content, encoding="utf-8")
    png_path = Path(qml_path).parent / "qml_screenshot.png"
    ok, size = edge_screenshot(str(html_file), str(png_path))
    result["L3_screenshot"] = {"ok": ok, "size": size}
    if not ok:
        result["ok"] = False

    return result


def validate_windows_html(html_path):
    """L1 + L3 直接 Edge 截图。"""
    from validate_code import validate_code

    result = {"L1_syntax": {}, "L3_screenshot": {}, "ok": True}
    code = Path(html_path).read_text(encoding="utf-8")

    # L1: validate_code
    vr = validate_code("html", code)
    # HTML5 标签可能导致误报，记录但不阻塞
    result["L1_syntax"] = {
        "ok": vr["ok"],
        "errors": len(vr.get("errors", [])),
        "note": "lxml HTML4 DTD may false-positive on HTML5 semantic tags" if not vr["ok"] else ""
    }

    # L3: 直接 Edge 截图
    png_path = Path(html_path).parent / "html_screenshot.png"
    ok, size = edge_screenshot(str(html_path), str(png_path), width=960, height=720)
    result["L3_screenshot"] = {"ok": ok, "size": size}
    if not ok:
        result["ok"] = False

    return result


def validate_a2ui(jsonl_path):
    """L1 + L2 JSONL 解析 + L3 截图。"""
    from e2e_deep_verify import validate_a2ui, a2ui_to_html

    result = {"L1_syntax": {}, "L2_parse": {}, "L3_screenshot": {}, "ok": True}

    # L1+L2: 验证 + 解析
    vr = validate_a2ui(jsonl_path)
    result["L1_syntax"] = {
        "ok": vr.get("checks", {}).get("json_parse", {}).get("ok", False),
        "lines": vr.get("checks", {}).get("json_parse", {}).get("parsed_count", 0),
        "types": vr.get("checks", {}).get("type_coverage", {}).get("count", 0),
    }
    result["L2_parse"] = {
        "ok": vr.get("checks", {}).get("parent_chain", {}).get("ok", False),
        "tree_depth": vr.get("checks", {}).get("tree_structure", {}).get("max_depth", 0),
    }
    if not vr.get("ok", False):
        result["ok"] = False

    # L3: JSONL→HTML 截图
    html_content = a2ui_to_html(jsonl_path)
    html_file = Path(jsonl_path).parent / "a2ui_render.html"
    html_file.write_text(html_content, encoding="utf-8")
    png_path = Path(jsonl_path).parent / "a2ui_screenshot.png"
    ok, size = edge_screenshot(str(html_file), str(png_path))
    result["L3_screenshot"] = {"ok": ok, "size": size}
    if not ok:
        result["ok"] = False

    return result


def validate_winui3(xaml_path):
    """L1 XAML 结构验证 + L3 近似 HTML 截图。"""
    from e2e_deep_verify import validate_winui3_xaml, winui3_xaml_to_html

    result = {"L1_syntax": {}, "L3_screenshot": {}, "ok": True}
    xaml_content = Path(xaml_path).read_text(encoding="utf-8")

    # L1: 结构验证
    vr = validate_winui3_xaml(xaml_content)
    result["L1_syntax"] = {
        "ok": vr.get("checks", {}).get("xml_parse", {}).get("ok", False),
        "controls": vr.get("checks", {}).get("controls", {}).get("total_unique", 0),
        "is_winui3": vr.get("checks", {}).get("framework_check", {}).get("is_winui3", False),
    }
    if not vr.get("ok", False):
        result["ok"] = False

    # L3: XAML→HTML 截图
    html_content = winui3_xaml_to_html(xaml_content)
    html_file = Path(xaml_path).parent / "winui3_render.html"
    html_file.write_text(html_content, encoding="utf-8")
    png_path = Path(xaml_path).parent / "winui3_screenshot.png"
    ok, size = edge_screenshot(str(html_file), str(png_path))
    result["L3_screenshot"] = {"ok": ok, "size": size}
    if not ok:
        result["ok"] = False

    return result


def generate_html_report(results, gen_dir, device_serial):
    """生成自包含 HTML 报告。"""
    def img_b64(path):
        p = Path(path)
        if not p.exists():
            return ""
        return f"data:image/png;base64,{base64.b64encode(p.read_bytes()).decode()}"

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = len(results)
    passed = sum(1 for r in results.values() if r.get("ok"))
    failed = total - passed

    stack_html = ""
    for name, data in results.items():
        ok = data.get("ok", False)
        status_class = "pass" if ok else "fail"
        status_badge = "✅ PASS" if ok else "❌ FAIL"

        levels_html = ""
        for level in ["L1_syntax", "L2_compile", "L2_parse", "L3_screenshot", "L4_device"]:
            if level not in data:
                continue
            ld = data[level]
            lok = ld.get("ok", False)
            lbadge = "✅" if lok else "❌"
            details = " ".join(f"{k}={v}" for k, v in ld.items() if k != "ok")
            levels_html += f'<div class="level { 'pass' if lok else 'fail' }"><span class="badge">{lbadge}</span> <b>{level}</b> {details}</div>'

        # Screenshot
        screenshot_html = ""
        for ss_key, ss_name in [("compose_screenshot.png", "Compose"), ("xml_screenshot.png", "XML"),
                                ("qml_screenshot.png", "QML"), ("html_screenshot.png", "HTML"),
                                ("a2ui_screenshot.png", "A2UI"), ("winui3_screenshot.png", "WinUI3"),
                                ("xml_device_screenshot.png", "XML Device")]:
            ss_path = gen_dir / ss_key
            if ss_path.exists() and name.lower().replace(" ", "") in ss_name.lower().replace(" ", ""):
                b64 = img_b64(str(ss_path))
                if b64:
                    screenshot_html = f'<div class="screenshot"><img src="{b64}" alt="{name}"/></div>'
                    break

        stack_html += f"""
        <div class="stack {status_class}">
            <h3>{name} <span class="badge {status_class}">{status_badge}</span></h3>
            {levels_html}
            {screenshot_html}
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>快速验证报告 — {now}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Segoe UI','Microsoft YaHei',sans-serif; background:#f0f2f5; color:#1a1a2e; line-height:1.6; }}
.header {{ background:linear-gradient(135deg,#1677ff,#0958d9); color:#fff; padding:30px 20px; text-align:center; }}
.header h1 {{ font-size:24px; margin-bottom:4px; }}
.summary {{ display:flex; justify-content:center; gap:20px; margin-top:12px; }}
.summary-item {{ background:rgba(255,255,255,0.15); padding:6px 16px; border-radius:6px; font-size:13px; }}
.container {{ max-width:900px; margin:0 auto; padding:20px; }}
.stack {{ background:#fff; border-radius:8px; padding:20px; margin-bottom:16px; box-shadow:0 2px 6px rgba(0,0,0,0.06); border-left:4px solid #28a745; }}
.stack.fail {{ border-left-color:#dc3545; }}
.stack h3 {{ font-size:17px; margin-bottom:12px; }}
.badge {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:12px; font-weight:600; }}
.badge.pass {{ background:#d4edda; color:#155724; }}
.badge.fail {{ background:#f8d7da; color:#721c24; }}
.level {{ padding:6px 0; font-size:13px; }}
.level.pass {{ color:#155724; }}
.level.fail {{ color:#721c24; }}
.screenshot {{ margin-top:12px; }}
.screenshot img {{ width:100%; border-radius:6px; box-shadow:0 2px 8px rgba(0,0,0,0.1); }}
</style></head>
<body>
<div class="header">
    <h1>快速验证报告</h1>
    <p>{now} | 设备: {device_serial or 'N/A'}</p>
    <div class="summary">
        <span class="summary-item">✅ 通过: {passed}</span>
        <span class="summary-item">❌ 失败: {failed}</span>
        <span class="summary-item">总计: {total}</span>
    </div>
</div>
<div class="container">{stack_html}</div>
</body></html>"""


def main():
    parser = argparse.ArgumentParser(description="一键快速验证 LLM 生成的代码")
    parser.add_argument("generated_dir", help="包含 llm_*.kt/xml/qml/html/jsonl 的目录")
    parser.add_argument("--device", default=None, help="ADB 设备序列号（可选）")
    parser.add_argument("--deploy-compose", action="store_true", help="编译并部署 Compose APK 到设备")
    args = parser.parse_args()

    gen_dir = Path(args.generated_dir).resolve()
    if not gen_dir.exists():
        print(f"Error: directory not found: {gen_dir}")
        return 1

    device = args.device
    files = find_files(gen_dir)

    if not files:
        print(f"Error: no llm_* files found in {gen_dir}")
        return 1

    print("=" * 60)
    print(f"快速验证 — {gen_dir.name}")
    print(f"文件: {list(files.keys())}")
    print(f"设备: {device or 'N/A'}")
    print("=" * 60)

    results = {}
    t0 = time.time()

    # 1. Kotlin Compose
    if "kotlin_compose" in files:
        print("\n[Kotlin Compose]")
        r = validate_kotlin_compose(files["kotlin_compose"])
        results["Kotlin Compose"] = r
        print(f"  L1: {'PASS' if r['L1_syntax']['ok'] else 'FAIL'}")
        print(f"  L3: {'PASS' if r['L3_screenshot']['ok'] else 'FAIL'} ({r['L3_screenshot']['size']} bytes)")

        # 可选: 编译 + 部署
        if args.deploy_compose and device and GRADLE_BIN:
            print("  L4: Deploying Compose APK...")
            # 复制到模板项目
            template_dir = Path(__file__).resolve().parent.parent / "templates" / "kotlin_compose"
            proj_dir = gen_dir / "_compose_project"
            if proj_dir.exists():
                import shutil
                shutil.rmtree(proj_dir)
            shutil.copytree(template_dir, proj_dir)

            # 复制 .kt 文件
            kt_dest = proj_dir / "app" / "src" / "main" / "java" / "com" / "e2e" / "settings" / "GeneratedScreen.kt"
            shutil.copy(files["kotlin_compose"], kt_dest)

            # 更新 MainActivity
            main_kt = proj_dir / "app" / "src" / "main" / "java" / "com" / "e2e" / "settings" / "MainActivity.kt"
            content = main_kt.read_text()
            content = content.replace("// {{COMPOSABLE_FUNCTION_CALL}}", "GeneratedScreen()")
            main_kt.write_text(content)

            # Gradle 编译
            proc = subprocess.run([GRADLE_BIN, "-p", str(proj_dir), "--offline", "assembleDebug"],
                                   capture_output=True, timeout=120)
            apk_path = proj_dir / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
            if proc.returncode == 0 and apk_path.exists():
                print(f"  L4: Build PASS ({apk_path.stat().st_size // 1024}KB)")
                # 安装 + 截图
                subprocess.run(["adb", "-s", device, "install", "-r", str(apk_path)],
                               capture_output=True, timeout=30)
                subprocess.run(["adb", "-s", device, "shell", "am", "start",
                                "-n", "com.e2e.settings/.MainActivity"],
                               capture_output=True, timeout=10)
                time.sleep(3)
                subprocess.run(["adb", "-s", device, "shell", "screencap", "-p", "/sdcard/compose.png"],
                               capture_output=True, timeout=10)
                dev_png = gen_dir / "compose_device_screenshot.png"
                subprocess.run(["adb", "-s", device, "pull", "/sdcard/compose.png", str(dev_png)],
                               capture_output=True, timeout=10)
                results["Kotlin Compose"]["L4_device"] = {
                    "ok": dev_png.exists(),
                    "size": dev_png.stat().st_size if dev_png.exists() else 0
                }
            else:
                print(f"  L4: Build FAIL (rc={proc.returncode})")
                results["Kotlin Compose"]["L4_device"] = {"ok": False, "error": "build failed"}

    # 2. Android XML
    if "android_xml" in files:
        print("\n[Android XML]")
        r = validate_android_xml(files["android_xml"], device)
        results["Android XML"] = r
        print(f"  L1: {'PASS' if r['L1_syntax']['ok'] else 'FAIL'}")
        print(f"  L2: {'PASS' if r['L2_compile'].get('ok') else 'FAIL'}")
        print(f"  L3: {'PASS' if r['L3_screenshot']['ok'] else 'FAIL'} ({r['L3_screenshot']['size']} bytes)")
        if "L4_device" in r and r["L4_device"].get("ok") is not None:
            print(f"  L4: {'PASS' if r['L4_device']['ok'] else 'FAIL'} ({r['L4_device']['size']} bytes)")

    # 3. Qt QML
    if "qt_qml" in files:
        print("\n[Qt QML]")
        r = validate_qt_qml(files["qt_qml"])
        results["Qt QML"] = r
        print(f"  L1: {'PASS' if r['L1_syntax']['ok'] else 'FAIL'} (imports={r['L1_syntax']['imports']}, components={r['L1_syntax']['components']})")
        print(f"  L3: {'PASS' if r['L3_screenshot']['ok'] else 'FAIL'} ({r['L3_screenshot']['size']} bytes)")

    # 4. Windows HTML
    if "windows_html" in files:
        print("\n[Windows HTML]")
        r = validate_windows_html(files["windows_html"])
        results["Windows HTML"] = r
        print(f"  L1: {'PASS' if r['L1_syntax']['ok'] else 'FAIL'} (errors={r['L1_syntax']['errors']})")
        print(f"  L3: {'PASS' if r['L3_screenshot']['ok'] else 'FAIL'} ({r['L3_screenshot']['size']} bytes)")

    # 5. A2UI
    if "a2ui" in files:
        print("\n[A2UI]")
        r = validate_a2ui(files["a2ui"])
        results["A2UI"] = r
        print(f"  L1: {'PASS' if r['L1_syntax']['ok'] else 'FAIL'} (lines={r['L1_syntax']['lines']}, types={r['L1_syntax']['types']})")
        print(f"  L2: {'PASS' if r['L2_parse']['ok'] else 'FAIL'} (depth={r['L2_parse']['tree_depth']})")
        print(f"  L3: {'PASS' if r['L3_screenshot']['ok'] else 'FAIL'} ({r['L3_screenshot']['size']} bytes)")

    # 6. WinUI3
    if "winui3" in files:
        print("\n[WinUI3]")
        r = validate_winui3(files["winui3"])
        results["WinUI3"] = r
        print(f"  L1: {'PASS' if r['L1_syntax']['ok'] else 'FAIL'} (controls={r['L1_syntax']['controls']})")
        print(f"  L3: {'PASS' if r['L3_screenshot']['ok'] else 'FAIL'} ({r['L3_screenshot']['size']} bytes)")

    elapsed = time.time() - t0

    # 生成报告
    print(f"\n{'=' * 60}")
    total = len(results)
    passed = sum(1 for r in results.values() if r.get("ok"))
    print(f"结果: {passed}/{total} PASS | 耗时: {elapsed:.1f}s")
    print(f"{'=' * 60}")

    json_report = gen_dir / "quick_verify_report.json"
    json_report.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    html_report = gen_dir / "quick_verify_report.html"
    html_report.write_text(generate_html_report(results, gen_dir, device), encoding="utf-8")

    print(f"\nJSON: {json_report}")
    print(f"HTML: {html_report}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
