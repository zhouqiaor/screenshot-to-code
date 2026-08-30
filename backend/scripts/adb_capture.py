"""ADB data capture: screenshot + uiautomator dump from a connected Android device.

Usage:
    python -m scripts.adb_capture --device <device_id> --output <output_dir>
    python backend/scripts/adb_capture.py --device 192.168.1.100:5555 --output /tmp/adb_test

If no --device is given, uses the first device from `adb devices`.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any


def _run_adb(args: list[str], device_id: str | None = None) -> subprocess.CompletedProcess:
    """Run an adb command, raising on failure."""
    cmd = ["adb"]
    if device_id:
        cmd += ["-s", device_id]
    cmd += args
    return subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=30)


def list_devices() -> list[str]:
    """Return list of connected device IDs (excluding emulator header lines)."""
    try:
        result = subprocess.run(
            ["adb", "devices"], capture_output=True, text=True, check=True, timeout=10
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"adb devices failed: {e}") from e
    except subprocess.TimeoutExpired:
        raise RuntimeError("adb devices timed out (10s)")
    devices = []
    for line in result.stdout.strip().splitlines()[1:]:  # skip "List of devices"
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    return devices


def capture_device_ui(device_id: str | None = None, output_dir: str = ".") -> dict[str, Any]:
    """Capture screenshot + UI hierarchy from a connected ADB device.

    Args:
        device_id: Device serial or "host:port" for network ADB. If None, auto-detect.
        output_dir: Directory to write screenshot.png and ui_tree.xml.

    Returns:
        {"screenshot": str, "ui_tree": str, "device_id": str}
    """
    if device_id is None:
        devices = list_devices()
        if not devices:
            raise RuntimeError("No ADB devices connected. Connect a device or start adb server.")
        device_id = devices[0]

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Use unique filenames to avoid concurrent capture races on the same device
    uid = uuid.uuid4().hex[:8]
    device_screenshot = f"/sdcard/capture_{uid}.png"
    device_ui_tree = f"/sdcard/ui_tree_{uid}.xml"

    try:
        # Screenshot: screencap to device, then pull
        _run_adb(["shell", "screencap", "-p", device_screenshot], device_id)
        screenshot_path = out / "screenshot.png"
        _run_adb(["pull", device_screenshot, str(screenshot_path)], device_id)

        # UI hierarchy: uiautomator dump to device, then pull
        _run_adb(["shell", "uiautomator", "dump", device_ui_tree], device_id)
        ui_tree_path = out / "ui_tree.xml"
        _run_adb(["pull", device_ui_tree, str(ui_tree_path)], device_id)
    finally:
        # Clean up temp files on the device
        _run_adb(["shell", "rm", "-f", device_screenshot, device_ui_tree], device_id)

    return {
        "screenshot": str(screenshot_path),
        "ui_tree": str(ui_tree_path),
        "device_id": device_id,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture Android device UI via ADB")
    parser.add_argument("--device", "-d", default=None, help="ADB device ID (serial or host:port)")
    parser.add_argument("--output", "-o", default="./adb_output", help="Output directory")
    args = parser.parse_args()

    if shutil.which("adb") is None:
        print("Error: 'adb' not found on PATH. Install Android Platform Tools.", file=sys.stderr)
        return 1

    try:
        result = capture_device_ui(device_id=args.device, output_dir=args.output)
        print(json.dumps(result, indent=2))
        return 0
    except subprocess.CalledProcessError as e:
        print(f"ADB command failed: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
