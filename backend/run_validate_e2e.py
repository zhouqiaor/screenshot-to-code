"""E2E validate_code runner — validates all 6 stacks against e2e_demo LLM output."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agent.tools.validate_code import validate_code, Stack

base = os.path.join(os.path.dirname(__file__), "..", "e2e_demo")

files: dict[str, tuple[str, Stack]] = {
    "android_xml":     ("llm_android_xml.xml", "android_xml"),  # type: ignore
    "android_compose": ("llm_android_compose.kt", "android_compose"),  # type: ignore
    "qt_qml":          ("llm_qt_qml.qml", "qt_qml"),  # type: ignore
    "html":            ("llm_windows_html.html", "html"),
    "windows_wpf":     ("llm_windows_wpf.xaml", "windows_wpf"),
    "a2ui":            ("llm_a2ui.jsonl", "a2ui"),
}

results = {}
for name, (fname, stack) in files.items():
    path = os.path.join(base, fname)
    if not os.path.exists(path):
        results[name] = {"error": f"File not found: {fname}", "ok": False}
        continue
    with open(path, "r", encoding="utf-8") as f:
        code = f.read()
    result = validate_code(stack, code)
    errors = result["errors"]
    warnings = result["warnings"]
    results[name] = {
        "stack": stack,
        "file": fname,
        "chars": len(code),
        "errors": len(errors),
        "warnings": len(warnings),
        "ok": result["ok"],
        "error_details": [{"line": e["line"], "col": e["col"], "message": e["message"]} for e in errors],
        "warning_details": [{"line": w["line"], "col": w["col"], "message": w["message"]} for w in warnings],
    }

print(json.dumps(results, indent=2, ensure_ascii=False))
passed = sum(1 for r in results.values() if r.get("ok"))
print(f"\n=== {passed}/{len(results)} stacks passed validate_code ===")

# Save to file
out_path = os.path.join(base, "validate_code_results.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
    f.write(f"\n{{\"summary\": \"{passed}/{len(results)} stacks passed\"}}\n")
print(f"Results saved to {out_path}")
