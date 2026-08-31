"""Orchestrate the full ADB capture pipeline: capture → parse → extract.

Runs adb_capture → skeleton_parser → theme_extractor in sequence,
returns combined JSON result for the API endpoint.

Usage:
    python -m scripts.run_adb_pipeline --device <device_id> --output <dir>
    python backend/scripts/run_adb_pipeline.py --device emulator-5554 --output /tmp/adb
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path
from typing import Any

from scripts.adb_capture import capture_device_ui
from scripts.skeleton_parser import parse_ui_tree
from scripts.theme_extractor import extract_theme


def run_pipeline(device_id: str | None = None, output_dir: str = "./adb_output") -> dict[str, Any]:
    """Run the full ADB capture pipeline.

    Steps:
        1. adb_capture: screenshot.png + ui_tree.xml
        2. skeleton_parser: ui_tree.xml → skeleton.json
        3. theme_extractor: screenshot.png + skeleton.json → theme.json

    Args:
        device_id: ADB device serial or "host:port". None = auto-detect.
        output_dir: Working directory for intermediate files.

    Returns:
        {
            "screenshot_data_url": "data:image/png;base64,...",
            "screenshot_path": "/path/to/screenshot.png",
            "skeleton": {...},
            "theme": {...},
            "device_id": "emulator-5554",
        }
    """
    # Step 1: Capture screenshot + UI tree
    capture_result = capture_device_ui(device_id=device_id, output_dir=output_dir)
    screenshot_path = capture_result["screenshot"]
    ui_tree_path = capture_result["ui_tree"]
    device_id = capture_result["device_id"]

    # Step 2: Parse UI tree → skeleton.json
    skeleton = parse_ui_tree(ui_tree_path)

    # Step 3: Extract theme → theme.json
    theme = extract_theme(screenshot_path, skeleton)

    # Step 4: Read screenshot as data URL for frontend preview
    screenshot_bytes = Path(screenshot_path).read_bytes()
    screenshot_data_url = (
        f"data:image/png;base64,{base64.b64encode(screenshot_bytes).decode('utf-8')}"
    )

    return {
        "screenshot_data_url": screenshot_data_url,
        "screenshot_path": screenshot_path,
        "skeleton": skeleton,
        "theme": theme,
        "device_id": device_id,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full ADB capture pipeline")
    parser.add_argument("--device", "-d", default=None, help="ADB device ID")
    parser.add_argument("--output", "-o", default="./adb_output", help="Output directory")
    args = parser.parse_args()

    try:
        result = run_pipeline(device_id=args.device, output_dir=args.output)
        # Don't print screenshot_data_url (too long), just the metadata
        output = {k: v for k, v in result.items() if k != "screenshot_data_url"}
        output["screenshot_data_url_length"] = len(result.get("screenshot_data_url", ""))
        print(json.dumps(output, indent=2, ensure_ascii=False, default=str))
        return 0
    except Exception as e:
        print(f"Pipeline error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
