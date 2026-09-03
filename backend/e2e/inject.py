"""Injector: place generated stack code into canonical run locations.

Per the confirmed plan (decision #1), the pipeline currently only drops code
into ``<run>/code/<stack>.<ext>`` (no engineering scaffold injection yet). The
``STACK_TARGETS`` table is the single place to later point a stack at a real
framework target (e.g. ``android_compose`` -> ``android_project/MainActivity.kt``)
without touching the generation core.
"""
from __future__ import annotations

from pathlib import Path

from .common import STACKS, code_filename

# stack -> relative target inside the run dir (extend for real scaffolds later)
STACK_TARGETS: dict[str, str] = {
    stack: f"code/{code_filename(stack)}" for stack in STACKS
}


def place_stack(run_dir: Path, stack: str, code: str) -> Path:
    """Write ``code`` for ``stack`` to its canonical target path.

    Returns the written path. Falls back to ``code/<stack>.<ext>`` if the stack
    is unknown.
    """
    rel = STACK_TARGETS.get(stack, f"code/{code_filename(stack)}")
    dst = run_dir / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(code, encoding="utf-8")
    return dst


def inject_run(run_dir: Path, generated: dict[str, str]) -> dict[str, str]:
    """Place all generated stacks. ``generated`` maps stack -> code text.

    Returns {stack: relative_target_path}.
    """
    mapping: dict[str, str] = {}
    for stack, code in generated.items():
        dst = place_stack(run_dir, stack, code)
        mapping[stack] = str(dst.relative_to(run_dir))
    return mapping
