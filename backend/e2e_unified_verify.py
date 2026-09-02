"""
E2E Unified Verification Script — 5 Stack Demo

Implements the ScreenshotRenderer protocol from e2e-verification-projects.md.
For each stack, runs the deepest verification available on this machine:

1. Syntax validation (validate_code)           — all 5 stacks
2. Structural checks (brackets/imports/etc.)    — per stack
3. Compile-level checks (aapt2 for Android XML)  — when tool available
4. Screenshot rendering (Edge headless)         — HTML + A2UI directly;
   QML/XML/Compose → approximate HTML render → Edge screenshot
5. Visual metrics (image size, pixel count)     — all rendered screenshots

Output:
  - e2e_unified_report.json    (machine-readable)
  - e2e_unified_report.html    (human-readable, self-contained, with screenshots)
  - render_*.png               (screenshots per stack)

Environment notes:
  - Edge:        C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe  (FOUND)
  - aapt2:       C:\\Programs\\Android\\Sdk\\build-tools\\34.0.0\\aapt2.exe         (FOUND)
  - Qt/dotnet:   NOT FOUND — QML/WinUI3 use degraded HTML approximation
  - Python 3.13 + lxml/jsonschema/pillow available
"""
import sys
import os
import json
import re
import time
import base64
import subprocess
import shutil
from pathlib import Path
from xml.etree import ElementTree
from typing import Any, Dict, List, Optional, Protocol

# --- Path setup ---
sys.path.insert(0, str(Path(__file__).parent / "agent" / "tools"))
from validate_code import validate_code  # type: ignore

# --- Constants ---
RUN_DIR = Path(r"C:\Code\screenshot-to-code\e2e_demo\run_20260901")
OUTPUT_DIR = RUN_DIR  # output alongside source files
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
AAPT2_PATH = r"C:\Programs\Android\Sdk\build-tools\34.0.0\aapt2.exe"
ANDROID_JAR = None  # will try to find

# Find android.jar
for bt in ["34.0.0", "35.0.0", "33.0.1"]:
    p = Path(r"C:\Programs\Android\Sdk\platforms") / f"android-{bt.split('.')[0]}" / "android.jar"
    if p.exists():
        ANDROID_JAR = str(p)
        break


# ============================================================
# Part 1: ScreenshotRenderer Protocol + Implementations
# ============================================================

class ScreenshotRenderer(Protocol):
    """Unified screenshot interface per e2e-verification-projects.md."""
    def render(self, source_file: str, output_png: str) -> Dict[str, Any]:
        """Render source file to PNG. Returns {ok, method, output, size_bytes, error?}."""
        ...


class EdgeHeadlessRenderer:
    """Render HTML files via Microsoft Edge headless --screenshot."""

    def __init__(self, edge_path: str = EDGE_PATH):
        self.edge_path = edge_path
        self._available = os.path.exists(edge_path)

    def render(self, source_file: str, output_png: str, width: int = 960, height: int = 720) -> Dict[str, Any]:
        if not self._available:
            return {"ok": False, "error": f"Edge not found at {self.edge_path}"}
        if not os.path.exists(source_file):
            return {"ok": False, "error": f"Source not found: {source_file}"}

        file_url = f"file:///{Path(source_file).resolve().as_posix()}"
        cmd = [
            self.edge_path,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            f"--window-size={width},{height}",
            f"--screenshot={output_png}",
            file_url,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=30, text=True)
            if os.path.exists(output_png):
                size = os.path.getsize(output_png)
                return {"ok": True, "method": "Edge headless --screenshot", "output": output_png, "size_bytes": size}
            return {"ok": False, "error": f"Edge exited with code {result.returncode}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}


# ============================================================
# Part 2: Per-stack verifiers
# ============================================================

def check_bracket_balance(code: str, pairs: dict) -> list:
    stack: List[tuple] = []
    errors = []
    line = 1
    for i, ch in enumerate(code):
        if ch == "\n":
            line += 1
        if ch in pairs:
            stack.append((ch, line, i))
        elif ch in pairs.values():
            if not stack:
                errors.append(f"Line {line}: unexpected '{ch}'")
            else:
                opener, open_line, _ = stack.pop()
                rev = {v: k for k, v in pairs.items()}
                if opener != rev.get(ch, ""):
                    errors.append(f"Line {line}: mismatched '{ch}' (expected '{pairs[opener]}')")
    if stack:
        for opener, open_line, _ in stack:
            errors.append(f"Line {open_line}: unclosed '{opener}'")
    return errors


def verify_kotlin(code: str) -> Dict:
    checks = {}
    vr = validate_code("android_compose", code)
    checks["validate_code"] = {"ok": vr["ok"], "errors": vr["errors"], "warnings": vr["warnings"]}

    brace_errors = check_bracket_balance(code, {"{": "}", "(": ")", "[": "]"})
    checks["bracket_balance"] = {"ok": len(brace_errors) == 0, "errors": brace_errors}

    imports = re.findall(r"^import\s+(\S+)", code, re.MULTILINE)
    required = ["androidx.compose.runtime.Composable", "androidx.compose.material3", "androidx.compose.foundation.layout"]
    missing = [imp for imp in required if not any(imp in i for i in imports)]
    checks["imports"] = {"ok": len(missing) == 0, "missing": missing, "total_imports": len(imports)}

    composable_count = len(re.findall(r"@Composable", code))
    checks["composable_annotations"] = {"count": composable_count, "ok": composable_count > 0}

    funcs = re.findall(r"fun\s+(\w+)\s*\(", code)
    checks["functions"] = {"names": funcs, "count": len(funcs), "ok": len(funcs) > 0}

    all_ok = all(v.get("ok", True) for v in checks.values())
    return {"ok": all_ok, "checks": checks}


def verify_android_xml(code: str) -> Dict:
    checks = {}
    vr = validate_code("android_xml", code)
    checks["validate_code"] = {"ok": vr["ok"], "errors": vr["errors"], "warnings": vr["warnings"]}

    try:
        root = ElementTree.fromstring(code)
        checks["xml_parse"] = {"ok": True, "root_tag": root.tag, "attr_count": len(root.attrib)}
    except ElementTree.ParseError as e:
        checks["xml_parse"] = {"ok": False, "error": str(e)}

    checks["namespaces"] = {"ok": "http://schemas.android.com/apk/res/android" in code}

    try:
        tree = ElementTree.fromstring(code)
        elem_count = sum(1 for _ in tree.iter())
        checks["elements"] = {"count": elem_count, "ok": elem_count > 5}
    except Exception:
        checks["elements"] = {"ok": False, "error": "parse failed"}

    # aapt2 compile check (if available)
    if os.path.exists(AAPT2_PATH):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            xml_file = Path(tmpdir) / "layout.xml"
            xml_file.write_text(code, encoding="utf-8")
            out_dir = Path(tmpdir) / "compiled"
            out_dir.mkdir()
            try:
                result = subprocess.run(
                    [AAPT2_PATH, "compile", "-o", str(out_dir), "--dir", str(tmpdir)],
                    capture_output=True, timeout=15, text=True
                )
                compiled_files = list(out_dir.glob("*.flat"))
                checks["aapt2_compile"] = {
                    "ok": result.returncode == 0 or len(compiled_files) > 0,
                    "exit_code": result.returncode,
                    "output_files": [f.name for f in compiled_files],
                    "stderr": result.stderr[:500] if result.stderr else "",
                }
            except Exception as e:
                checks["aapt2_compile"] = {"ok": False, "error": str(e)}
    else:
        checks["aapt2_compile"] = {"ok": False, "error": "aapt2 not found", "skipped": True}

    all_ok = all(v.get("ok", True) and not v.get("skipped") for v in checks.values() if not v.get("skipped"))
    # Don't let skipped checks fail overall
    for v in checks.values():
        if v.get("skipped"):
            continue
        if not v.get("ok", True):
            all_ok = False
            break
    return {"ok": all_ok, "checks": checks}


def verify_qt_qml(code: str) -> Dict:
    checks = {}
    vr = validate_code("qt_qml", code)
    checks["validate_code"] = {"ok": vr["ok"], "errors": vr["errors"], "warnings": vr["warnings"]}

    brace_errors = check_bracket_balance(code, {"{": "}", "(": ")", "[": "]"})
    checks["brace_balance"] = {"ok": len(brace_errors) == 0, "errors": brace_errors}

    imports = re.findall(r"^import\s+(\S+)", code, re.MULTILINE)
    checks["imports"] = {"total": len(imports), "list": imports, "ok": len(imports) >= 3}

    checks["root_element"] = {"has_ApplicationWindow": "ApplicationWindow" in code, "ok": "ApplicationWindow" in code}

    prop_count = len(re.findall(r"^\s*\w+\s*:\s*", code, re.MULTILINE))
    checks["properties"] = {"count": prop_count, "ok": prop_count > 5}

    all_ok = all(v.get("ok", True) for v in checks.values())
    return {"ok": all_ok, "checks": checks}


def verify_html(code: str) -> Dict:
    checks = {}
    vr = validate_code("html", code)
    checks["validate_code"] = {"ok": vr["ok"], "errors": vr["errors"], "warnings": vr["warnings"]}

    has_doctype = code.strip().lower().startswith("<!doctype html>")
    has_html = "<html" in code.lower()
    has_head = "<head" in code.lower()
    has_body = "<body" in code.lower()
    has_style = "<style" in code.lower()
    checks["structure"] = {
        "doctype": has_doctype, "html": has_html, "head": has_head,
        "body": has_body, "style": has_style,
        "ok": all([has_doctype, has_html, has_head, has_body])
    }

    external_refs = re.findall(r'(?:src|href)=["\'](?!https?://|//|data:|#)([^"\']+)', code)
    checks["self_contained"] = {"external_refs": external_refs[:10], "ok": len(external_refs) == 0}

    css_rules = len(re.findall(r"[^{}]+\{[^{}]*\}", code))
    checks["css"] = {"rule_count": css_rules, "ok": css_rules > 5}

    inputs = len(re.findall(r"<input", code, re.IGNORECASE))
    buttons = len(re.findall(r"<button", code, re.IGNORECASE))
    checks["interactive_elements"] = {"inputs": inputs, "buttons": buttons}

    all_ok = all(v.get("ok", True) for v in checks.values())
    return {"ok": all_ok, "checks": checks}


def verify_a2ui(code: str) -> Dict:
    checks = {}
    vr = validate_code("a2ui", code)
    checks["validate_code"] = {"ok": vr["ok"], "errors": vr["errors"], "warnings": vr["warnings"]}

    lines = [l for l in code.strip().split("\n") if l.strip()]
    valid_types = {"button", "card", "column", "container", "image", "input", "list", "row", "stack", "text"}
    json_errors = []
    type_usage = set()
    parsed_count = 0

    for i, line in enumerate(lines, 1):
        line = line.strip()
        try:
            obj = json.loads(line)
            parsed_count += 1
            t = obj.get("type", "")
            type_usage.add(t)
            if t and t not in valid_types:
                json_errors.append(f"Line {i}: unknown type '{t}'")
            if not obj.get("id"):
                json_errors.append(f"Line {i}: missing 'id'")
        except json.JSONDecodeError as e:
            json_errors.append(f"Line {i}: JSON parse error: {e}")

    checks["json_parse"] = {"total_lines": len(lines), "parsed_count": parsed_count, "errors": json_errors, "ok": len(json_errors) == 0}
    checks["type_coverage"] = {"types_used": sorted(type_usage), "count": len(type_usage), "ok": len(type_usage) >= 3}

    ids = set()
    parents = set()
    for line in lines:
        try:
            obj = json.loads(line.strip())
            if obj.get("id"):
                ids.add(obj["id"])
            if obj.get("parent"):
                parents.add(obj["parent"])
        except json.JSONDecodeError:
            pass
    orphan_parents = parents - ids - {None}
    checks["parent_chain"] = {"total_ids": len(ids), "orphan_parents": list(orphan_parents), "ok": len(orphan_parents) == 0}

    all_ok = all(v.get("ok", True) for v in checks.values())
    return {"ok": all_ok, "checks": checks}


# ============================================================
# Part 3: Fallback renderers — approximate HTML for non-HTML stacks
# ============================================================

def qml_to_approximate_html(qml_code: str) -> str:
    """Convert QML to an approximate HTML visual preview."""
    # Extract key structural elements from QML
    title_match = re.search(r'title:\s*"([^"]+)"', qml_code)
    title = title_match.group(1) if title_match else "QML Preview"
    width_match = re.search(r'width:\s*(\d+)', qml_code)
    height_match = re.search(r'height:\s*(\d+)', qml_code)
    win_w = width_match.group(1) if width_match else "900"
    win_h = height_match.group(1) if height_match else "600"

    # Extract Material colors
    primary_match = re.search(r'Material\.primary:\s*"([^"]+)"', qml_code)
    primary_color = primary_match.group(1) if primary_match else "#1677ff"

    # Extract buttons, switches, sliders, text
    buttons = re.findall(r'Button\s*\{[^}]*?text:\s*"([^"]+)"', qml_code, re.DOTALL)
    switch_texts = re.findall(r'Switch\s*\{[^}]*?text:\s*"([^"]+)"', qml_code, re.DOTALL)
    slider_texts = re.findall(r'Slider\s*\{[^}]*?text:\s*"([^"]+)"', qml_code, re.DOTALL)
    labels = re.findall(r'Label\s*\{[^}]*?text:\s*"([^"]+)"', qml_code, re.DOTALL)
    all_texts = [t for t in (buttons + switch_texts + slider_texts + labels) if t and t != "\\u00d7"]

    # Build HTML
    items_html = ""
    for text in all_texts:
        if text in ["×", "\\u00d7"]:
            continue
        items_html += f'<div class="setting-row"><span>{text}</span></div>\n'

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} (QML Approximate)</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: "Segoe UI", Roboto, "Microsoft YaHei", sans-serif; background: #f5f5f5; display: flex; justify-content: center; padding: 20px; }}
.qml-window {{ width: {win_w}px; max-width: 100%; background: #f5f5f5; border-radius: 8px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); overflow: hidden; }}
.titlebar {{ background: {primary_color}; color: white; padding: 12px 20px; display: flex; justify-content: space-between; align-items: center; }}
.titlebar h1 {{ font-size: 16px; font-weight: 500; }}
.close-btn {{ background: transparent; border: none; color: white; font-size: 24px; cursor: pointer; }}
.content {{ padding: 24px; }}
.setting-row {{ display: flex; justify-content: space-between; align-items: center; padding: 14px 0; border-bottom: 1px solid #e8e8e8; }}
.setting-row span {{ font-size: 14px; color: #212121; }}
.note {{ padding: 8px 12px; background: #fff3e0; border-left: 3px solid #ff9800; font-size: 12px; color: #666; margin-bottom: 16px; }}
</style></head>
<body>
<div class="qml-window">
  <div class="titlebar"><h1>{title}</h1><button class="close-btn">×</button></div>
  <div class="note">QML approximate render — structural preview only (no Qt runtime)</div>
  <div class="content">{items_html or '<div class="setting-row"><span>No settings items extracted</span></div>'}</div>
</div>
</body></html>"""


def android_xml_to_approximate_html(xml_code: str) -> str:
    """Convert Android XML layout to an approximate HTML visual preview."""
    root = ElementTree.fromstring(xml_code)
    ns = {"android": "http://schemas.android.com/apk/res/android"}

    def parse_element(elem, depth=0):
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        text = elem.get("{http://schemas.android.com/apk/res/android}text", "")
        bg = elem.get("{http://schemas.android.com/apk/res/android}background", "")
        w = elem.get("{http://schemas.android.com/apk/res/android}layout_width", "")

        # Map common Android views to HTML
        if tag in ("Button", "androidx.appcompat.widget.AppCompatButton"):
            return f'<button class="android-btn">{text}</button>'
        elif tag == "TextView":
            return f'<span class="android-text">{text}</span>'
        elif tag == "EditText":
            hint = elem.get("{http://schemas.android.com/apk/res/android}hint", "")
            return f'<input class="android-input" placeholder="{hint}" />'
        elif tag == "CheckBox":
            checked = elem.get("{http://schemas.android.com/apk/res/android}checked", "false")
            checked_attr = "checked" if checked == "true" else ""
            return f'<label class="android-checkbox"><input type="checkbox" {checked_attr}/> {text}</label>'
        elif tag == "SeekBar":
            return f'<input type="range" class="android-seekbar" />'
        elif tag == "Switch":
            return f'<label class="android-switch"><input type="checkbox"/> {text}</label>'
        elif tag in ("LinearLayout", "RelativeLayout", "ConstraintLayout"):
            children_html = ""
            for child in elem:
                children_html += parse_element(child, depth + 1)
            orientation = elem.get("{http://schemas.android.com/apk/res/android}orientation", "vertical")
            flex_dir = "row" if orientation == "horizontal" else "column"
            return f'<div class="android-layout" style="flex-direction:{flex_dir}">{children_html}</div>'
        elif tag == "ScrollView":
            children_html = "".join(parse_element(c, depth + 1) for c in elem)
            return f'<div class="android-scroll">{children_html}</div>'
        elif tag == "CardView":
            children_html = "".join(parse_element(c, depth + 1) for c in elem)
            return f'<div class="android-card">{children_html}</div>'
        else:
            children_html = "".join(parse_element(c, depth + 1) for c in elem)
            if children_html:
                return f'<div class="android-generic">{children_html}</div>'
            return f'<span>{text}</span>' if text else ""

    content_html = parse_element(root)

    # Extract title from first TextView
    title = "Android XML Preview"
    title_elem = root.find(".//*[@android:text]", ns)
    if title_elem is not None:
        t = title_elem.get("{http://schemas.android.com/apk/res/android}text", "")
        if t and t != "×":
            title = t

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} (Android XML Approximate)</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: "Segoe UI", Roboto, "Microsoft YaHei", sans-serif; background: #f5f5f5; display: flex; justify-content: center; padding: 20px; }}
.android-window {{ width: 900px; max-width: 100%; background: #f5f5f5; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); overflow: hidden; }}
.note {{ padding: 8px 12px; background: #fff3e0; border-left: 3px solid #ff9800; font-size: 12px; color: #666; }}
.android-layout {{ display: flex; padding: 16px; gap: 12px; }}
.android-text {{ font-size: 14px; color: #212121; padding: 4px 0; }}
.android-btn {{ padding: 8px 24px; background: #1677ff; color: white; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; }}
.android-input {{ padding: 8px 12px; border: 1px solid #d9d9d9; border-radius: 6px; font-size: 14px; width: 100%; }}
.android-checkbox, .android-switch {{ display: flex; align-items: center; gap: 8px; font-size: 14px; padding: 8px 0; }}
.android-seekbar {{ width: 100%; }}
.android-card {{ background: white; border-radius: 12px; padding: 16px; margin: 8px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
.android-scroll {{ max-height: 400px; overflow-y: auto; }}
.android-generic {{ padding: 8px; }}
</style></head>
<body>
<div class="android-window">
  <div class="note">Android XML approximate render — structural preview only (no Android runtime)</div>
  {content_html}
</div>
</body></html>"""


def kotlin_compose_to_approximate_html(kt_code: str) -> str:
    """Extract Composable structure and render as approximate HTML."""
    # Extract @Composable function name
    func_match = re.search(r"fun\s+(\w+)\s*\(", kt_code)
    func_name = func_match.group(1) if func_match else "ComposablePreview"

    # Extract Text() calls
    texts = re.findall(r'Text\s*\(\s*(?:text\s*=\s*)?"([^"]+)"', kt_code)
    # Extract Switch() calls with label
    switches = re.findall(r'Switch\s*\(', kt_code)
    # Extract Slider() calls
    sliders = re.findall(r'Slider\s*\(', kt_code)
    # Extract Button() calls
    buttons = re.findall(r'Button\s*\(\s*\{[^}]*\}\s*\)\s*\{[^}]*?Text\s*\(\s*"([^"]+)"', kt_code)

    items_html = ""
    for text in texts:
        if text in ["×", "\\u00d7"]:
            continue
        items_html += f'<div class="setting-row"><span>{text}</span></div>\n'
    for _ in switches:
        items_html += '<div class="setting-row"><span>Switch</span><label class="toggle"><input type="checkbox" checked/><span class="slider"></span></label></div>\n'
    for _ in sliders:
        items_html += '<div class="setting-row"><span>Volume</span><input type="range" style="flex:1"/></div>\n'
    for btn_text in buttons:
        items_html += f'<div class="setting-row"><button class="btn">{btn_text}</button></div>\n'

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{func_name} (Compose Approximate)</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: "Segoe UI", Roboto, "Microsoft YaHei", sans-serif; background: #f5f5f5; display: flex; justify-content: center; padding: 20px; }}
.compose-window {{ width: 900px; max-width: 100%; background: #f5f5f5; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); overflow: hidden; }}
.note {{ padding: 8px 12px; background: #e3f2fd; border-left: 3px solid #1677ff; font-size: 12px; color: #666; }}
.content {{ padding: 24px; }}
.setting-row {{ display: flex; justify-content: space-between; align-items: center; padding: 14px 20px; background: white; border-radius: 12px; margin-bottom: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }}
.setting-row span {{ font-size: 14px; color: #212121; }}
.btn {{ padding: 8px 24px; background: #1677ff; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; }}
.toggle {{ position: relative; width: 44px; height: 22px; }}
.toggle input {{ opacity: 0; width: 0; height: 0; }}
.slider {{ position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background: #1677ff; border-radius: 11px; }}
</style></head>
<body>
<div class="compose-window">
  <div class="note">Jetpack Compose approximate render — structural preview only (no Compose runtime)</div>
  <div class="content">{items_html or '<div class="setting-row"><span>No items extracted</span></div>'}</div>
</div>
</body></html>"""


# ============================================================
# Part 4: Main verification pipeline
# ============================================================

def run_all():
    print("=" * 70)
    print("E2E Unified 5-Stack Verification Demo")
    print("=" * 70)

    edge = EdgeHeadlessRenderer()
    results = {}

    stacks_config = [
        ("Kotlin Compose", "llm_android_compose.kt", "kt", verify_kotlin, "compose"),
        ("Android XML", "llm_android_xml.xml", "xml", verify_android_xml, "xml"),
        ("Qt QML", "llm_qt_qml.qml", "qml", verify_qt_qml, "qml"),
        ("Windows HTML", "llm_windows_html.html", "html", verify_html, "html"),
        ("A2UI JSONL", "llm_a2ui.jsonl", "a2ui", verify_a2ui, "a2ui"),
    ]

    for name, filename, ext, verify_fn, render_type in stacks_config:
        filepath = RUN_DIR / filename
        print(f"\n{'=' * 70}")
        print(f"  {name} ({filename})")
        print(f"{'=' * 70}")

        code = filepath.read_text(encoding="utf-8")
        print(f"  Size: {len(code)} chars, {code.count(chr(10))} lines")

        # --- Step 1: Syntax + structural verification ---
        result = verify_fn(code)
        results[name] = result
        status = "PASS" if result["ok"] else "FAIL"
        print(f"  Verification: {status}")
        for cn, cr in result["checks"].items():
            ok = cr.get("ok", True)
            skipped = cr.get("skipped", False)
            icon = "SKIP" if skipped else ("OK" if ok else "FAIL")
            detail = ""
            if "count" in cr:
                detail = f" (count={cr['count']})"
            elif "total" in cr:
                detail = f" (total={cr['total']})"
            elif cr.get("errors"):
                detail = f" ({len(cr['errors'])} errors)"
            print(f"    {cn:25s} {icon:5s}{detail}")

        # --- Step 2: Screenshot rendering ---
        print(f"\n  Rendering screenshot...")
        png_name = f"unified_{ext}_screenshot.png"
        png_path = str(OUTPUT_DIR / png_name)

        if render_type == "html":
            # Direct Edge screenshot of HTML
            render_result = edge.render(str(filepath), png_path)
        elif render_type == "a2ui":
            # Use existing a2ui_preview.html
            preview_html = RUN_DIR / "a2ui_preview.html"
            if preview_html.exists():
                render_result = edge.render(str(preview_html), png_path)
            else:
                render_result = {"ok": False, "error": "a2ui_preview.html not found"}
        elif render_type == "qml":
            # Generate approximate HTML → Edge screenshot
            approx_html = OUTPUT_DIR / "qml_approximate.html"
            approx_html.write_text(qml_to_approximate_html(code), encoding="utf-8")
            render_result = edge.render(str(approx_html), png_path)
        elif render_type == "xml":
            # Generate approximate HTML → Edge screenshot
            approx_html = OUTPUT_DIR / "xml_approximate.html"
            approx_html.write_text(android_xml_to_approximate_html(code), encoding="utf-8")
            render_result = edge.render(str(approx_html), png_path)
        elif render_type == "compose":
            # Generate approximate HTML → Edge screenshot
            approx_html = OUTPUT_DIR / "compose_approximate.html"
            approx_html.write_text(kotlin_compose_to_approximate_html(code), encoding="utf-8")
            render_result = edge.render(str(approx_html), png_path)
        else:
            render_result = {"ok": False, "error": "unknown render type"}

        results[name]["screenshot"] = render_result
        if render_result.get("ok"):
            print(f"    Screenshot: {png_name} ({render_result.get('size_bytes', 0):,} bytes)")
        else:
            print(f"    Screenshot: FAILED — {render_result.get('error', 'unknown')}")

    # --- Summary ---
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    all_pass = True
    for name, result in results.items():
        v_ok = result.get("ok", False)
        s_ok = result.get("screenshot", {}).get("ok", False)
        v_icon = "PASS" if v_ok else "FAIL"
        s_icon = "PASS" if s_ok else "FAIL"
        if not v_ok:
            all_pass = False
        print(f"  {name:25s}  Verify: {v_icon:5s}  Screenshot: {s_icon:5s}")

    print(f"\n  Overall: {'ALL PASS' if all_pass else 'SOME FAILED'}")

    # --- Save JSON report ---
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "all_pass": all_pass,
        "environment": {
            "edge": os.path.exists(EDGE_PATH),
            "aapt2": os.path.exists(AAPT2_PATH),
            "android_jar": ANDROID_JAR is not None,
            "qt": False,  # not installed
            "dotnet": False,  # not installed
        },
        "stacks": results,
    }
    report_path = OUTPUT_DIR / "e2e_unified_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  JSON Report: {report_path}")

    return report


# ============================================================
# Part 5: HTML visual report
# ============================================================

def generate_html_report(report: dict, output_path: Path):
    """Generate a self-contained HTML report with screenshots embedded as base64."""
    from PIL import Image
    import io

    def img_to_base64(path: str, max_width: int = 400) -> str:
        if not os.path.exists(path):
            return ""
        try:
            img = Image.open(path)
            # Resize to max_width keeping aspect ratio
            if img.width > max_width:
                ratio = max_width / img.width
                img = img.resize((max_width, int(img.height * ratio)))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode()
            return f"data:image/png;base64,{b64}"
        except Exception as e:
            return f"<p style='color:red'>Error: {e}</p>"

    def img_to_base64_jpeg(path: str, max_width: int = 400) -> str:
        if not os.path.exists(path):
            return ""
        try:
            img = Image.open(path)
            if img.width > max_width:
                ratio = max_width / img.width
                img = img.resize((max_width, int(img.height * ratio)))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            b64 = base64.b64encode(buf.getvalue()).decode()
            return f"data:image/jpeg;base64,{b64}"
        except Exception:
            return ""

    # Source screenshot
    source_png = str(RUN_DIR / "screenshots" / "run_20260901" / "source_screenshot_768.jpg")
    source_b64 = img_to_base64_jpeg(source_png, 400)

    stacks_html = ""
    stack_files = {
        "Kotlin Compose": ("llm_android_compose.kt", "unified_kt_screenshot.png"),
        "Android XML": ("llm_android_xml.xml", "unified_xml_screenshot.png"),
        "Qt QML": ("llm_qt_qml.qml", "unified_qml_screenshot.png"),
        "Windows HTML": ("llm_windows_html.html", "unified_html_screenshot.png"),
        "A2UI JSONL": ("llm_a2ui.jsonl", "unified_a2ui_screenshot.png"),
    }

    for name, (source_file, screenshot_file) in stack_files.items():
        stack_data = report["stacks"].get(name, {})
        v_ok = stack_data.get("ok", False)
        screenshot_data = stack_data.get("screenshot", {})
        s_ok = screenshot_data.get("ok", False)

        screenshot_path = str(RUN_DIR / screenshot_file)
        screenshot_b64 = img_to_base64_jpeg(screenshot_path, 350)

        # Checks table
        checks_html = ""
        for cn, cr in stack_data.get("checks", {}).items():
            ok = cr.get("ok", True)
            skipped = cr.get("skipped", False)
            icon = "⚠ SKIP" if skipped else ("✓ PASS" if ok else "✗ FAIL")
            color = "#f0ad4e" if skipped else ("#28a745" if ok else "#dc3545")
            detail = ""
            for key in ["count", "total", "total_lines", "parsed_count", "root_tag", "exit_code"]:
                if key in cr:
                    detail = f"{key}={cr[key]}"
                    break
            if cr.get("errors"):
                detail = f"{len(cr['errors'])} errors"
            checks_html += f"""
            <tr>
              <td style="padding:6px 12px;border-bottom:1px solid #eee;font-family:monospace;font-size:12px">{cn}</td>
              <td style="padding:6px 12px;border-bottom:1px solid #eee;color:{color};font-weight:600">{icon}</td>
              <td style="padding:6px 12px;border-bottom:1px solid #eee;font-size:12px;color:#666">{detail}</td>
            </tr>"""

        v_color = "#28a745" if v_ok else "#dc3545"
        s_color = "#28a745" if s_ok else "#dc3545"

        stacks_html += f"""
        <div style="margin-bottom:32px;border:1px solid #e0e0e0;border-radius:12px;overflow:hidden;background:white">
          <div style="padding:16px 20px;background:#f8f9fa;border-bottom:1px solid #e0e0e0;display:flex;justify-content:space-between;align-items:center">
            <h3 style="margin:0;font-size:16px">{name}</h3>
            <div style="display:flex;gap:12px;font-size:12px">
              <span style="padding:4px 10px;border-radius:4px;background:{v_color};color:white">Verify: {'PASS' if v_ok else 'FAIL'}</span>
              <span style="padding:4px 10px;border-radius:4px;background:{s_color};color:white">Screenshot: {'PASS' if s_ok else 'FAIL'}</span>
            </div>
          </div>
          <div style="padding:16px 20px">
            <div style="display:flex;gap:20px;flex-wrap:wrap">
              <div style="flex:1;min-width:300px">
                <table style="width:100%;border-collapse:collapse;font-size:13px">
                  <thead><tr style="background:#f5f5f5">
                    <th style="padding:6px 12px;text-align:left;border-bottom:2px solid #ddd">Check</th>
                    <th style="padding:6px 12px;text-align:left;border-bottom:2px solid #ddd">Result</th>
                    <th style="padding:6px 12px;text-align:left;border-bottom:2px solid #ddd">Detail</th>
                  </tr></thead>
                  <tbody>{checks_html}</tbody>
                </table>
              </div>
              <div style="flex:0 0 auto;text-align:center">
                <div style="font-size:12px;color:#666;margin-bottom:8px">Screenshot ({screenshot_data.get('method', 'N/A')})</div>
                {f'<img src="{screenshot_b64}" style="border:1px solid #ddd;border-radius:8px;max-width:350px" />' if screenshot_b64 else '<div style="width:350px;height:200px;background:#f0f0f0;display:flex;align-items:center;justify-content:center;border-radius:8px;color:#999">No screenshot</div>'}
                {f'<div style="font-size:11px;color:#999;margin-top:4px">{screenshot_data.get("size_bytes",0):,} bytes</div>' if screenshot_b64 else ''}
              </div>
            </div>
            <div style="margin-top:12px;padding:8px 12px;background:#f8f9fa;border-radius:6px;font-family:monospace;font-size:11px;color:#666">
              {source_file} · {screenshot_file}
            </div>
          </div>
        </div>"""

    env = report.get("environment", {})
    env_html = f"""
    <div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:20px;padding:12px 16px;background:#f8f9fa;border-radius:8px;font-size:13px">
      <span>Edge: <b style="color:{'#28a745' if env.get('edge') else '#dc3545'}">{'✓' if env.get('edge') else '✗'}</b></span>
      <span>aapt2: <b style="color:{'#28a745' if env.get('aapt2') else '#dc3545'}">{'✓' if env.get('aapt2') else '✗'}</b></span>
      <span>android.jar: <b style="color:{'#28a745' if env.get('android_jar') else '#dc3545'}">{'✓' if env.get('android_jar') else '✗'}</b></span>
      <span>Qt: <b style="color:#dc3545">✗</b></span>
      <span>dotnet: <b style="color:#dc3545">✗</b></span>
    </div>"""

    all_pass = report.get("all_pass", False)
    overall_color = "#28a745" if all_pass else "#dc3545"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>E2E Unified 5-Stack Verification Report</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Microsoft YaHei", sans-serif; background: #f5f5f5; color: #212121; padding: 24px; }}
.container {{ max-width: 1200px; margin: 0 auto; }}
h1 {{ font-size: 24px; margin-bottom: 8px; }}
h2 {{ font-size: 18px; margin: 24px 0 12px; }}
.meta {{ font-size: 13px; color: #666; margin-bottom: 16px; }}
.overall {{ display:inline-block; padding: 8px 20px; border-radius: 6px; background: {overall_color}; color: white; font-weight: 600; font-size: 16px; margin-bottom: 20px; }}
.source-preview {{ margin-bottom: 20px; text-align: center; }}
.source-preview img {{ border: 1px solid #ddd; border-radius: 8px; max-width: 400px; }}
</style></head>
<body><div class="container">
  <h1>E2E Unified 5-Stack Verification Report</h1>
  <div class="meta">Generated: {report.get('timestamp', 'N/A')}</div>
  <div class="overall">Overall: {'ALL PASS' if all_pass else 'SOME FAILED'}</div>

  <h2>Source Screenshot</h2>
  <div class="source-preview">
    {f'<img src="{source_b64}" />' if source_b64 else '<p>Source screenshot not found</p>'}
    <div style="font-size:12px;color:#999;margin-top:4px">Original screenshot sent to LLM for code generation</div>
  </div>

  <h2>Environment</h2>
  {env_html}

  <h2>Per-Stack Verification</h2>
  {stacks_html}

  <div style="margin-top:32px;padding:16px;background:#f8f9fa;border-radius:8px;font-size:12px;color:#666">
    <p><b>Rendering strategy:</b> HTML & A2UI → direct Edge headless screenshot · QML/XML/Compose → approximate HTML render → Edge screenshot</p>
    <p><b>Verification depth:</b> Syntax (validate_code) → Structural (brackets/imports) → Compile (aapt2 for XML) → Screenshot (Edge headless)</p>
    <p><b>Stacks without native runtime:</b> QML (no Qt), Compose (no Gradle), WinUI3 (no dotnet) — degraded to approximate HTML preview</p>
  </div>
</div></body></html>"""

    output_path.write_text(html, encoding="utf-8")
    print(f"  HTML Report: {output_path}")


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    report = run_all()
    generate_html_report(report, OUTPUT_DIR / "e2e_unified_report.html")
    print(f"\n{'=' * 70}")
    print("Done!")
    print(f"{'=' * 70}")
