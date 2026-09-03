"""One-click generation CLI for the screenshot-to-code fork.

Usage:
    python -m e2e.cli --image shot.png --stacks android_compose,android_xml,qt_qml,windows_html,a2ui
    python -m e2e.cli --image shot.png --stacks a2ui --dry      # verify wiring, no API call

Pipeline:  image --(1 vision)--> ui_desc --(N text)--> code/* --(inject)--> code/<stack>.<ext>
All outputs land in e2e_runs/<run_id>/ with a manifest.json. No hardcoded RUN_DIR.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .common import ALL_STACKS, make_run_dir
from .generate.core import describe_image, generate_stacks
from .inject import inject_run


def _mock_generate(ui_desc: str, stacks: list[str]) -> dict:
    """Stand-in for ``generate_stacks`` used by --dry (no network)."""
    return {
        s: {"code": f"// MOCK {s} code\n// ui_desc was {len(ui_desc)} chars\n", "chars": 40, "ok": True}
        for s in stacks
    }


def run(args: argparse.Namespace) -> int:
    image = Path(args.image)
    if not image.exists():
        print(f"ERROR: image not found: {image}")
        return 2

    stacks = [s.strip() for s in args.stacks.split(",") if s.strip()]
    unknown = [s for s in stacks if s not in ALL_STACKS]
    if unknown:
        print(f"ERROR: unknown stack(s): {unknown}. Valid: {ALL_STACKS}")
        return 2

    run_dir = make_run_dir(args.model)
    print(f"Run dir: {run_dir}")

    # Phase 1 — vision -> ui_description
    if args.dry:
        ui_desc = "MOCK ui description for dry run"
        print("[dry] skip vision call")
    else:
        print("Phase 1: vision -> ui_description ...")
        ui_desc = describe_image(image, args.model)
    (run_dir / "inputs" / "ui_description.json").write_text(
        json.dumps({"text": ui_desc}, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Phase 2 — generate per stack
    print(f"Phase 2: generating {len(stacks)} stack(s) ...")
    results = _mock_generate(ui_desc, stacks) if args.dry else generate_stacks(ui_desc, stacks, args.model)

    # Phase 3 — inject (fixed script places code into canonical paths)
    generated = {s: r["code"] for s, r in results.items() if r.get("ok")}
    mapping = inject_run(run_dir, generated)

    # manifest
    manifest = {
        "run_id": run_dir.name,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": args.model,
        "image": str(image),
        "stacks": stacks,
        "code": mapping,
        "generation": {s: {"ok": r["ok"], "chars": r["chars"], "error": r.get("error")} for s, r in results.items()},
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    ok = sum(1 for r in results.values() if r["ok"])
    print(f"Done: {ok}/{len(stacks)} stacks generated.")
    print(f"  code:   {', '.join(mapping.keys())}")
    print(f"  manifest: {run_dir / 'manifest.json'}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="One-click multi-stack code generation")
    p.add_argument("--image", required=True, help="screenshot path")
    p.add_argument("--stacks", required=True,
                   help=f"comma-separated stacks, e.g. {','.join(ALL_STACKS[:4])}")
    p.add_argument("--model", default="doubao-seed-2-1-turbo-260628",
                   help="model slug ( Volcano Ark / DashScope / OpenAI-compatible )")
    p.add_argument("--dry", action="store_true", help="verify wiring without any API call")
    return run(p.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
