"""
Validate all 5 generated stacks using the backend's validate_code module.
"""
import sys
sys.path.insert(0, r'C:\Users\georgeslark\.workbuddy\binaries\python\envs\default\Lib\site-packages')
sys.path.insert(0, r'C:\Code\screenshot-to-code\backend\agent\tools')

import json
from pathlib import Path

from validate_code import validate_code, Stack

OUTPUT_DIR = Path(r'C:\Code\screenshot-to-code\e2e_demo\run_20260901')

stacks = [
    ("Kotlin Compose", "llm_android_compose.kt", "android_compose"),
    ("Android XML", "llm_android_xml.xml", "android_xml"),
    ("Qt QML", "llm_qt_qml.qml", "qt_qml"),
    ("Windows HTML", "llm_windows_html.html", "html"),
    ("A2UI JSONL", "llm_a2ui.jsonl", "a2ui"),
]

print()
print("=" * 70)
print("5-Stack Validation Results")
print("=" * 70)
print(f"{'Stack':<20} {'File':<30} {'Valid':<8} {'Errors':<10} {'Warnings':<10}")
print("-" * 80)

all_valid = True
results = []

for name, filename, stack_type in stacks:
    filepath = OUTPUT_DIR / filename
    if not filepath.exists():
        print(f"{name:<20} {filename:<30} {'N/A':<8} {'file missing'}")
        results.append({"stack": name, "valid": False, "errors": ["file missing"]})
        all_valid = False
        continue

    code = filepath.read_text(encoding="utf-8")
    try:
        result = validate_code(stack=stack_type, code=code)
        ok = result.get("ok", False)
        errors = result.get("errors", [])
        warnings = result.get("warnings", [])
        status = "PASS" if ok else "FAIL"
        print(f"{name:<20} {filename:<30} {status:<8} {len(errors):<10} {len(warnings):<10}")
        if errors:
            for err in errors[:3]:
                msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                print(f"  ERROR: {msg}")
        if warnings:
            for warn in warnings[:3]:
                msg = warn.get("message", str(warn)) if isinstance(warn, dict) else str(warn)
                print(f"  WARN:  {msg}")
        results.append({"stack": name, "valid": ok, "errors": errors, "warnings": warnings})
        if not ok:
            all_valid = False
    except Exception as e:
        print(f"{name:<20} {filename:<30} {'ERROR':<8} {str(e)[:30]}")
        results.append({"stack": name, "valid": False, "errors": [str(e)]})
        all_valid = False

print()
print("=" * 70)
print(f"Overall: {'ALL PASS' if all_valid else 'SOME FAILED'}")
print("=" * 70)

report = {
    "total_stacks": len(stacks),
    "valid": sum(1 for r in results if r["valid"]),
    "failed": sum(1 for r in results if not r["valid"]),
    "results": results,
}
with open(OUTPUT_DIR / "validation_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False, default=str)
print(f"Report saved: {OUTPUT_DIR / 'validation_report.json'}")
