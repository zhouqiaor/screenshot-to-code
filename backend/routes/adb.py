"""ADB capture API endpoint for Android Compose stack.

Provides:
    POST /api/adb/capture  — runs full ADB pipeline, returns screenshot + theme + skeleton
    GET  /api/adb/devices  — lists connected ADB devices

The frontend calls /api/adb/capture when the user clicks "ADB Capture" in the UI.
The returned theme.json + skeleton.json are formatted by build_adb_data_policy()
and injected into the designSystem field for the code generation request.
"""
from __future__ import annotations

import json
import re
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

# deviceId format validation: allow serial, IP:port, but block path traversal / injection
_DEVICE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9._:-]+$")
# Reject device IDs that could be interpreted as adb flags (start with -)
_DEVICE_ID_FORBIDDEN_PREFIX = "-"


class AdbCaptureRequest(BaseModel):
    deviceId: str | None = Field(
        default=None,
        pattern=r"^[a-zA-Z0-9._:-]+$",
        description="ADB device serial or host:port",
    )


class AdbCaptureResponse(BaseModel):
    screenshotDataUrl: str
    skeleton: dict[str, Any]
    theme: dict[str, Any]
    designSystemBlock: str
    deviceId: str


class AdbDeviceInfo(BaseModel):
    deviceId: str
    state: str


class AdbDevicesResponse(BaseModel):
    devices: list[AdbDeviceInfo]


def _list_devices_raw() -> list[dict[str, str]]:
    """List ADB devices without importing scripts module (which requires adb on PATH)."""
    import subprocess

    try:
        result = subprocess.run(
            ["adb", "devices"], capture_output=True, text=True, check=False, timeout=10
        )
    except subprocess.TimeoutExpired:
        return []
    if result.returncode != 0:
        return []

    devices: list[dict[str, str]] = []
    for line in result.stdout.strip().splitlines()[1:]:  # skip header
        parts = line.split()
        if len(parts) >= 2:
            devices.append({"deviceId": parts[0], "state": parts[1]})
    return devices


@router.get("/api/adb/devices", response_model=AdbDevicesResponse)
def list_adb_devices() -> AdbDevicesResponse:
    """List connected ADB devices."""
    import shutil

    if shutil.which("adb") is None:
        raise HTTPException(
            status_code=503,
            detail="ADB not found. Install Android Platform Tools and ensure 'adb' is on PATH.",
        )

    devices = _list_devices_raw()
    return AdbDevicesResponse(
        devices=[AdbDeviceInfo(**d) for d in devices if d["state"] == "device"]
    )


@router.post("/api/adb/capture", response_model=AdbCaptureResponse)
def adb_capture(request: AdbCaptureRequest) -> AdbCaptureResponse:
    """Run full ADB capture pipeline: screenshot + skeleton + theme extraction.

    Returns screenshot as data URL, parsed skeleton.json, extracted theme.json,
    and a pre-formatted designSystemBlock string ready for injection into the
    code generation request's designSystem field.
    """
    import shutil
    import subprocess
    import tempfile

    if shutil.which("adb") is None:
        raise HTTPException(
            status_code=503,
            detail="ADB not found. Install Android Platform Tools and ensure 'adb' is on PATH.",
        )

    # Validate deviceId format (defense in depth, complements Pydantic pattern)
    device_id = request.deviceId
    if device_id and _DEVICE_ID_FORBIDDEN_PREFIX in device_id[0]:
        raise HTTPException(
            status_code=400,
            detail="Invalid deviceId format.",
        )

    try:
        from scripts.run_adb_pipeline import run_pipeline
        from prompts.policies import build_adb_data_policy

        with tempfile.TemporaryDirectory(prefix="adb_capture_") as tmpdir:
            result = run_pipeline(device_id=device_id, output_dir=tmpdir)

        # Format ADB data as designSystem injection block
        theme_json = json.dumps(result["theme"], ensure_ascii=False)
        skeleton_json = json.dumps(result["skeleton"], ensure_ascii=False)
        design_system_block = build_adb_data_policy(theme_json, skeleton_json)

        return AdbCaptureResponse(
            screenshotDataUrl=result["screenshot_data_url"],
            skeleton=result["skeleton"],
            theme=result["theme"],
            designSystemBlock=design_system_block,
            deviceId=result["device_id"],
        )
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=503, detail=f"ADB command failed: {e}") from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="ADB capture failed.") from e
