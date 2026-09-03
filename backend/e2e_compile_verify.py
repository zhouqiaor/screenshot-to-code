"""
E2E compile/verify all 5 stacks from e2e_demo/run_20260901.

For each stack, attempt the deepest verification available on this machine:
1. validate_code (structural validation) — always
2. XML well-formedness (xml.etree.ElementTree) — for android_xml
3. JSONL line-by-line parse — for a2ui
4. HTML DOM parse (lxml/ElementTree) — for windows_html
5. Kotlin Compose: bracket balance + import check (no kotlinc available)
6. Qt QML: bracket/brace balance + import check (no qmlscene available)
7. HTML: Playwright headless render screenshot (if available)
"""
import sys
sys.path.insert(0, r'C:\Users\georgeslark\.workbuddy\binaries\python\envs\default\Lib\site-packages')
sys.path.insert(0, r'C:\Code\screenshot-to-code\backend\agent\tools')

import json
import os
import re
import time
import subprocess
from pathlib import Path
from xml.etree import ElementTree

from validate_code import validate_code

OUTPUT_DIR = Path(r'C:\Code\screenshot-to-code\e2e_demo\run_20260901')
NODE_BIN = r'C:\Users\georgeslark\.workbuddy\binaries\node\versions\22.22.2\node.exe'

results = {}


def check_bracket_balance(code: str, pairs: dict) -> list:
    """Check that brackets/braces/parens are balanced."""
    stack = []
    errors = []
    line = 1
    for i, ch in enumerate(code):
        if ch == '\n':
            line += 1
            continue
        if ch in pairs:
            stack.append((ch, line, i))
        elif ch in pairs.values():
            if not stack:
                errors.append(f"Line {line}: unexpected '{ch}' (no matching opener)")
            else:
                opener, open_line, _ = stack.pop()
                expected = {v: k for k, v in pairs.items()}[ch]
                if opener != expected:
                    errors.append(f"Line {line}: mismatched '{ch}' (expected closer for '{opener}' opened at line {open_line})")
    if stack:
        for opener, open_line, _ in stack:
            errors.append(f"Line {open_line}: unclosed '{opener}'")
    return errors


def verify_kotlin(code: str) -> dict:
    """Verify Kotlin Compose code."""
    checks = {}

    # 1. validate_code
    vr = validate_code("android_compose", code)
    checks["validate_code"] = {"ok": vr["ok"], "errors": vr["errors"], "warnings": vr["warnings"]}

    # 2. Bracket balance
    brace_errors = check_bracket_balance(code, {"{": "}", "(": ")", "[": "]"})
    checks["bracket_balance"] = {"ok": len(brace_errors) == 0, "errors": brace_errors}

    # 3. Import check
    imports = re.findall(r"^import\s+(\S+)", code, re.MULTILINE)
    required_imports = [
        "androidx.compose.runtime.Composable",
        "androidx.compose.material3",
        "androidx.compose.foundation.layout",
    ]
    missing = [imp for imp in required_imports if not any(imp in i for i in imports)]
    checks["imports"] = {"ok": len(missing) == 0, "missing": missing, "total_imports": len(imports)}

    # 4. @Composable annotation
    composable_count = len(re.findall(r"@Composable", code))
    checks["composable_annotations"] = {"count": composable_count, "ok": composable_count > 0}

    # 5. Function structure
    func_defs = re.findall(r"fun\s+(\w+)\s*\(", code)
    checks["functions"] = {"names": func_defs, "count": len(func_defs), "ok": len(func_defs) > 0}

    all_ok = all(v.get("ok", True) for v in checks.values())
    return {"ok": all_ok, "checks": checks}


def verify_android_xml(code: str) -> dict:
    """Verify Android XML layout."""
    checks = {}

    # 1. validate_code
    vr = validate_code("android_xml", code)
    checks["validate_code"] = {"ok": vr["ok"], "errors": vr["errors"], "warnings": vr["warnings"]}

    # 2. XML well-formedness (ElementTree)
    try:
        root = ElementTree.fromstring(code)
        checks["xml_parse"] = {"ok": True, "root_tag": root.tag, "attr_count": len(root.attrib)}
    except ElementTree.ParseError as e:
        checks["xml_parse"] = {"ok": False, "error": str(e)}

    # 3. Required namespaces
    ns_ok = "http://schemas.android.com/apk/res/android" in code
    checks["namespaces"] = {"ok": ns_ok}

    # 4. Element count
    try:
        tree = ElementTree.fromstring(code)
        elem_count = sum(1 for _ in tree.iter())
        checks["elements"] = {"count": elem_count, "ok": elem_count > 5}
    except Exception:
        checks["elements"] = {"ok": False, "error": "parse failed"}

    all_ok = all(v.get("ok", True) for v in checks.values())
    return {"ok": all_ok, "checks": checks}


def verify_qt_qml(code: str) -> dict:
    """Verify Qt QML code."""
    checks = {}

    # 1. validate_code
    vr = validate_code("qt_qml", code)
    checks["validate_code"] = {"ok": vr["ok"], "errors": vr["errors"], "warnings": vr["warnings"]}

    # 2. Brace balance
    brace_errors = check_bracket_balance(code, {"{": "}", "(": ")", "[": "]"})
    checks["brace_balance"] = {"ok": len(brace_errors) == 0, "errors": brace_errors}

    # 3. Import check
    imports = re.findall(r"^import\s+(\S+)", code, re.MULTILINE)
    checks["imports"] = {"total": len(imports), "list": imports}

    # 4. Root element
    has_app_window = "ApplicationWindow" in code
    checks["root_element"] = {"has_ApplicationWindow": has_app_window, "ok": has_app_window}

    # 5. Property assignments
    prop_count = len(re.findall(r"^\s*\w+\s*:\s*", code, re.MULTILINE))
    checks["properties"] = {"count": prop_count, "ok": prop_count > 5}

    all_ok = all(v.get("ok", True) for v in checks.values())
    return {"ok": all_ok, "checks": checks}


def verify_html(code: str) -> dict:
    """Verify HTML code."""
    checks = {}

    # 1. validate_code
    vr = validate_code("html", code)
    checks["validate_code"] = {"ok": vr["ok"], "errors": vr["errors"], "warnings": vr["warnings"]}

    # 2. DOCTYPE + structure
    has_doctype = code.strip().lower().startswith("<!doctype html>")
    has_html_tag = "<html" in code.lower()
    has_head = "<head" in code.lower()
    has_body = "<body" in code.lower()
    has_style = "<style" in code.lower()
    checks["structure"] = {
        "doctype": has_doctype, "html": has_html_tag, "head": has_head,
        "body": has_body, "style": has_style,
        "ok": all([has_doctype, has_html_tag, has_head, has_body])
    }

    # 3. Self-contained check (no external file refs except CDN)
    external_refs = re.findall(r'(?:src|href)=["\'](?!https?://|//|data:|#)([^"\']+)', code)
    checks["self_contained"] = {
        "external_refs": external_refs[:10],
        "ok": len(external_refs) == 0
    }

    # 4. CSS completeness
    css_rules = len(re.findall(r"[^{}]+\{[^{}]*\}", code))
    checks["css"] = {"rule_count": css_rules, "ok": css_rules > 5}

    # 5. Interactive elements
    inputs = len(re.findall(r"<input", code, re.IGNORECASE))
    buttons = len(re.findall(r"<button", code, re.IGNORECASE))
    checks["interactive_elements"] = {"inputs": inputs, "buttons": buttons}

    all_ok = all(v.get("ok", True) for v in checks.values())
    return {"ok": all_ok, "checks": checks}


def verify_a2ui(code: str) -> dict:
    """Verify A2UI JSONL code."""
    checks = {}

    # 1. validate_code
    vr = validate_code("a2ui", code)
    checks["validate_code"] = {"ok": vr["ok"], "errors": vr["errors"], "warnings": vr["warnings"]}

    # 2. Line-by-line JSON parse
    lines = code.strip().split("\n")
    valid_types = {"button", "card", "column", "container", "image", "input", "list", "row", "stack", "text"}
    json_errors = []
    type_usage = set()
    parsed_count = 0

    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            parsed_count += 1
            t = obj.get("type", "")
            type_usage.add(t)
            if t and t not in valid_types:
                json_errors.append(f"Line {i}: unknown type '{t}'")
            if not obj.get("id"):
                json_errors.append(f"Line {i}: missing 'id' field")
        except json.JSONDecodeError as e:
            json_errors.append(f"Line {i}: JSON parse error: {e}")

    checks["json_parse"] = {
        "total_lines": len(lines),
        "parsed_count": parsed_count,
        "errors": json_errors,
        "ok": len(json_errors) == 0
    }

    # 3. Type coverage
    checks["type_coverage"] = {
        "types_used": sorted(type_usage),
        "count": len(type_usage),
        "ok": len(type_usage) >= 3
    }

    # 4. Parent chain integrity
    ids = set()
    parents = set()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if obj.get("id"):
                ids.add(obj["id"])
            if obj.get("parent"):
                parents.add(obj["parent"])
        except json.JSONDecodeError:
            pass

    orphan_parents = parents - ids - {None}
    checks["parent_chain"] = {
        "total_ids": len(ids),
        "orphan_parents": list(orphan_parents),
        "ok": len(orphan_parents) == 0
    }

    all_ok = all(v.get("ok", True) for v in checks.values())
    return {"ok": all_ok, "checks": checks}


def render_html_screenshot(html_path: str, output_png: str) -> dict:
    """Try to render HTML with Playwright and capture screenshot."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 960, "height": 720})
            page.goto(f"file:///{html_path.replace(os.sep, '/')}")
            page.screenshot(path=output_png)
            browser.close()
        return {"ok": True, "screenshot": output_png}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ===== Run all verifications =====
print("=" * 70)
print("E2E Compile Verification - 5 Stacks")
print("=" * 70)

stacks_config = [
    ("Kotlin Compose", "llm_android_compose.kt", verify_kotlin),
    ("Android XML", "llm_android_xml.xml", verify_android_xml),
    ("Qt QML", "llm_qt_qml.qml", verify_qt_qml),
    ("Windows HTML", "llm_windows_html.html", verify_html),
    ("A2UI JSONL", "llm_a2ui.jsonl", verify_a2ui),
]

for name, filename, verify_fn in stacks_config:
    filepath = OUTPUT_DIR / filename
    print(f"\n{'=' * 70}")
    print(f"  {name} ({filename})")
    print(f"{'=' * 70}")

    code = filepath.read_text(encoding="utf-8")
    print(f"  Size: {len(code)} chars, {code.count(chr(10))} lines")

    result = verify_fn(code)
    results[name] = result

    status = "PASS" if result["ok"] else "FAIL"
    print(f"  Overall: {status}")

    for check_name, check_result in result["checks"].items():
        ok = check_result.get("ok", True)
        status_icon = "OK" if ok else "FAIL"
        detail = ""
        if "errors" in check_result and check_result["errors"]:
            detail = f" ({len(check_result['errors'])} errors)"
        elif "count" in check_result:
            detail = f" (count={check_result['count']})"
        elif "total" in check_result:
            detail = f" (total={check_result['total']})"
        print(f"    {check_name:25s} {status_icon:5s} {detail}")

        # Print errors
        if not ok and "errors" in check_result:
            for err in check_result["errors"][:5]:
                print(f"      - {err}")

# HTML screenshot
print(f"\n{'=' * 70}")
print("  HTML Screenshot Render (Playwright)")
print(f"{'=' * 70}")

html_path = str(OUTPUT_DIR / "llm_windows_html.html")
png_path = str(OUTPUT_DIR / "render_html_screenshot.png")
render_result = render_html_screenshot(html_path, png_path)
results["HTML Screenshot"] = render_result
if render_result["ok"]:
    print(f"    Screenshot saved: {png_path}")
else:
    print(f"    Skipped: {render_result.get('error', 'unknown')}")

# Summary
print(f"\n{'=' * 70}")
print("SUMMARY")
print(f"{'=' * 70}")
all_pass = True
for name, result in results.items():
    ok = result.get("ok", False)
    status = "PASS" if ok else "FAIL"
    if not ok:
        all_pass = False
    print(f"  {name:25s} {status}")

print(f"\n  Overall: {'ALL PASS' if all_pass else 'SOME FAILED'}")
print(f"{'=' * 70}")

# Save report
report = {
    "timestamp": f"2026-09-01T{time.strftime('%H:%M:%S')}+08:00",
    "all_pass": all_pass,
    "stacks": results,
}
report_path = OUTPUT_DIR / "e2e_compile_report.json"
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False, default=str)
print(f"\nReport: {report_path}")
