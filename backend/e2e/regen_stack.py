"""Regenerate a single failed stack into an existing run dir (reuses ui_description).

Usage (from backend/):
    poetry run python e2e/regen_stack.py <run_dir> <stack> [model]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from e2e.generate.core import generate_stacks  # noqa: E402
from e2e.inject import inject_run  # noqa: E402


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: python e2e/regen_stack.py <run_dir> <stack> [model]", file=sys.stderr)
        return 2
    run_dir = Path(sys.argv[1])
    stack = sys.argv[2]
    model = sys.argv[3] if len(sys.argv) > 3 else "doubao-seed-2-1-turbo-260628"

    ui_path = run_dir / "inputs" / "ui_description.json"
    if not ui_path.exists():
        print(f"ERROR: {ui_path} missing", file=sys.stderr)
        return 2
    ui_desc = json.loads(ui_path.read_text(encoding="utf-8"))["text"]

    results = generate_stacks(ui_desc, [stack], model)
    r = results[stack]
    if not r["ok"]:
        print(f"FAIL {stack}: {r.get('error')}")
        return 1

    mapping = inject_run(run_dir, {stack: r["code"]})

    manifest_path = run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.setdefault("code", {})[stack] = mapping[stack]
    gen = manifest.setdefault("generation", {})
    gen[stack] = {
        "ok": True,
        "chars": r["chars"],
        "error": None,
        "truncated": r.get("truncated", False),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK {stack}: {r['chars']} chars, truncated={r.get('truncated', False)}")
    print(f"manifest updated: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
