"""Windows UI Automation (UIA) capture: screenshot + accessibility tree.

Mirrors the ADB capture flow (adb_capture.py) but targets Windows desktop
applications via the Windows UI Automation API.  The actual UIA calls are
performed by an external PowerShell script (see scripts/win_capture.py)
which shells out to the .NET UIAutomationClient assembly.

This module provides a pure-Python orchestrator that:
1. Takes a screenshot of the desktop / foreground window.
2. Dumps the UIA tree to XML.
3. Returns file paths for downstream parsing (skeleton_parser).

When the Windows UIA toolchain is unavailable, callers can use the mock
mode (``MOCK_WIN_UIA=1`` env var or ``mock=True`` kwarg) to return a
synthetic tree for testing.

Usage:
    python -m capture.win_uia --output ./win_output
    python backend/capture/win_uia.py --output ./win_output
"""
from __future__ import annotations

import base64
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Path to the companion PowerShell capture script
_PS_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "win_capture.py"


def is_windows() -> bool:
    """Return True when running on a Windows host."""
    return platform.system() == "Windows"


def is_powershell_available() -> bool:
    """Return True when PowerShell (powershell.exe or pwsh) is on PATH."""
    return shutil.which("powershell") is not None or shutil.which("pwsh") is not None


def is_uia_available() -> bool:
    """Return True when the full UIA toolchain (Windows + PowerShell + script) is available."""
    return is_windows() and is_powershell_available() and _PS_SCRIPT.exists()


def _run_capture_script(output_dir: str, window_title: str | None = None) -> dict[str, Any]:
    """Run the PowerShell capture script via `python scripts/win_capture.py`.

    The script writes screenshot.png and ui_tree.xml to *output_dir*.
    """
    cmd: list[str] = [
        sys.executable,
        str(_PS_SCRIPT),
        "--output",
        output_dir,
    ]
    if window_title:
        cmd += ["--window-title", window_title]

    if not _PS_SCRIPT.exists():
        raise RuntimeError(
            f"Windows UIA capture script not found at {_PS_SCRIPT}. "
            f"Ensure 'scripts/win_capture.py' exists."
        )

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"Windows UIA capture script failed (exit {exc.returncode}): "
            f"{exc.stderr.strip() or exc.stdout.strip()}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Windows UIA capture script timed out (60s).") from exc

    try:
        payload = json.loads(result.stdout)
        if not isinstance(payload, dict):
            raise TypeError(
                f"Expected JSON object from capture script, got {type(payload).__name__}"
            )
        return payload
    except (json.JSONDecodeError, TypeError):
        logger.warning(
            "Capture script output was not valid JSON; falling back to default file paths. "
            "stdout: %.200s", result.stdout,
        )
        return {"screenshot": str(Path(output_dir) / "screenshot.png"),
                "ui_tree": str(Path(output_dir) / "ui_tree.xml")}


def _mock_capture(output_dir: str) -> dict[str, Any]:
    """Return a synthetic screenshot + UIA tree for testing.

    The mock tree mirrors the shape produced by the real PowerShell script
    so downstream parsers can be developed without a Windows host.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Minimal 1x1 PNG (transparent) so downstream code that opens the image
    # via PIL doesn't blow up when running tests.
    _PNG_1x1 = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4"
        b"\x89\x00\x00\x00\nIDATx\x9cb\x00\x01\x00\x00\x05\x00\x01"
        b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    screenshot_path = out / "screenshot.png"
    screenshot_path.write_bytes(_PNG_1x1)

    ui_tree_path = out / "ui_tree.xml"
    ui_tree_path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<hierarchy>"
        '<node bounds="[0,0][800,600]" class="Window" name="MockWindow" automation_id="mock">'
        '<node bounds="[20,20][780,60]" class="Text" name="Title" automation_id="title">'
        '<property name="text">Mock Window</property>'
        "</node>"
        '<node bounds="[20,80][200,110]" class="Button" name="OK" automation_id="okButton">'
        '<property name="text">OK</property>'
        "</node>"
        '<node bounds="[220,80][400,110]" class="Edit" name="Input" automation_id="inputField"/>'
        "</node>"
        "</hierarchy>",
        encoding="utf-8",
    )

    return {
        "screenshot": str(screenshot_path),
        "ui_tree": str(ui_tree_path),
        "window_title": "MockWindow",
        "mock": True,
    }


def capture_window_ui(
    output_dir: str = ".",
    window_title: str | None = None,
    mock: bool | None = None,
) -> dict[str, Any]:
    """Capture screenshot + UIA tree from the active Windows window.

    Args:
        output_dir: Directory to write screenshot.png and ui_tree.xml.
        window_title: Optional window title substring to target. If None,
            captures the foreground window.
        mock: When True, return synthetic data (for tests). When None,
            falls back to the ``MOCK_WIN_UIA`` environment variable.

    Returns:
        ``{"screenshot": str, "ui_tree": str, "window_title": str | None}``

    Raises:
        RuntimeError: When UIA is unavailable and mock is False/None.
    """
    if mock is None:
        mock = os.environ.get("MOCK_WIN_UIA", "").lower() in ("1", "true", "yes")

    if mock:
        return _mock_capture(output_dir)

    if not is_uia_available():
        raise RuntimeError(
            "Windows UIA capture requires Windows + PowerShell. "
            "Set MOCK_WIN_UIA=1 to use the mock capture for testing."
        )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    result = _run_capture_script(output_dir, window_title)
    screenshot_path = result.get("screenshot") or str(out / "screenshot.png")
    ui_tree_path = result.get("ui_tree") or str(out / "ui_tree.xml")

    return {
        "screenshot": screenshot_path,
        "ui_tree": ui_tree_path,
        "window_title": result.get("window_title", window_title),
    }


def screenshot_to_data_url(screenshot_path: str) -> str:
    """Read a screenshot file and return a ``data:image/png;base64,...`` URL."""
    data = Path(screenshot_path).read_bytes()
    return f"data:image/png;base64,{base64.b64encode(data).decode('utf-8')}"


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Capture Windows UI via UI Automation")
    parser.add_argument("--output", "-o", default="./win_output", help="Output directory")
    parser.add_argument("--window-title", "-w", default=None, help="Window title substring")
    parser.add_argument("--mock", action="store_true", help="Use mock capture (for testing)")
    args = parser.parse_args()

    try:
        result = capture_window_ui(
            output_dir=args.output,
            window_title=args.window_title,
            mock=args.mock,
        )
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
