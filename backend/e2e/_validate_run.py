"""Validate generated stack code for a given run dir using agent.tools.validate_code."""
from __future__ import annotations

import json
import os
import sys

# allow running from backend/ via `poetry run python e2e/_validate_run.py`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.tools.validate_code import validate_code  # noqa: E402

RUN = sys.argv[1] if len(sys.argv) > 1 else None
if not RUN:
    print("usage: python e2e/_validate_run.py <run_dir>", file=sys.stderr)
    sys.exit(2)

code_dir = os.path.join(RUN, "code")
report_dir = os.path.join(RUN, "reports")
os.makedirs(report_dir, exist_ok=True)

manifest_path = os.path.join(RUN, "manifest.json")
with open(manifest_path, encoding="utf-8") as f:
    manifest = json.load(f)

code_map = manifest.get("code", {})
results = {}
all_ok = True
summary_lines = []

for stack, rel in code_map.items():
    path = os.path.join(RUN, rel)
    if not os.path.exists(path):
        summary_lines.append(f"[SKIP] {stack}: file not found: {path}")
        continue
    with open(path, encoding="utf-8") as f:
        code = f.read()
    res = validate_code(stack, code)  # type: ignore[arg-type]
    results[stack] = res
    ok = res["ok"]
    all_ok = all_ok and ok
    n_err = len(res["errors"])
    n_warn = len(res["warnings"])
    summary_lines.append(
        f"[{'PASS' if ok else 'FAIL'}] {stack}: {n_err} error(s), {n_warn} warning(s)"
    )
    # write per-stack report
    report_path = os.path.join(report_dir, f"{stack}.json")
    with open(report_path, "w", encoding="utf-8") as rf:
        json.dump(res, rf, indent=2, ensure_ascii=False)

overall = {
    "run_id": manifest.get("run_id"),
    "all_ok": all_ok,
    "stacks": {s: r["ok"] for s, r in results.items()},
}
with open(os.path.join(report_dir, "summary.json"), "w", encoding="utf-8") as f:
    json.dump(overall, f, indent=2, ensure_ascii=False)

print("\n".join(summary_lines))
print(f"\nOVERALL: {'ALL PASS' if all_ok else 'HAS FAILURES'}")
print(f"Reports -> {report_dir}")
sys.exit(0 if all_ok else 1)
