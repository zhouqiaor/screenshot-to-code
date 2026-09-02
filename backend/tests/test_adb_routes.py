"""Tests for ADB API routes (routes/adb.py) and pipeline orchestrator."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


class TestAdbDevicesEndpoint:
    """Tests for GET /api/adb/devices."""

    def test_list_devices_adb_not_found(self) -> None:
        """Should return 503 when adb is not on PATH."""
        from fastapi.testclient import TestClient
        from main import app

        with patch("shutil.which", return_value=None):
            client = TestClient(app)
            response = client.get("/api/adb/devices")
            assert response.status_code == 503
            assert "ADB not found" in response.json()["detail"]

    def test_list_devices_no_devices(self) -> None:
        """Should return empty list when no devices connected."""
        from fastapi.testclient import TestClient
        from main import app

        mock_result = MagicMock(returncode=0, stdout="List of devices attached\n")
        with (
            patch("shutil.which", return_value="/usr/bin/adb"),
            patch("subprocess.run", return_value=mock_result),
        ):
            client = TestClient(app)
            response = client.get("/api/adb/devices")
            assert response.status_code == 200
            data = response.json()
            assert data["devices"] == []

    def test_list_devices_with_devices(self) -> None:
        """Should return device list when devices connected."""
        from fastapi.testclient import TestClient
        from main import app

        mock_result = MagicMock(
            returncode=0,
            stdout=(
                "List of devices attached\n"
                "emulator-5554\tdevice\n"
                "192.168.1.100:5555\tdevice\n"
                "emulator-5556\toffline\n"
            ),
        )
        with (
            patch("shutil.which", return_value="/usr/bin/adb"),
            patch("subprocess.run", return_value=mock_result),
        ):
            client = TestClient(app)
            response = client.get("/api/adb/devices")
            assert response.status_code == 200
            devices = response.json()["devices"]
            assert len(devices) == 2  # only "device" state, not "offline"
            assert devices[0]["deviceId"] == "emulator-5554"
            assert devices[1]["deviceId"] == "192.168.1.100:5555"


class TestAdbCaptureEndpoint:
    """Tests for POST /api/adb/capture."""

    def test_capture_adb_not_found(self) -> None:
        """Should return 503 when adb is not on PATH."""
        from fastapi.testclient import TestClient
        from main import app

        with patch("shutil.which", return_value=None):
            client = TestClient(app)
            response = client.post(
                "/api/adb/capture",
                json={"deviceId": None},
            )
            assert response.status_code == 503

    def test_capture_success(self) -> None:
        """Should return screenshot + skeleton + theme on success."""
        from fastapi.testclient import TestClient
        from main import app

        mock_result = {
            "screenshot_data_url": "data:image/png;base64,iVBORw0KGgo=",
            "screenshot_path": "/tmp/screenshot.png",
            "skeleton": {"screen": {"width": 1080, "height": 2400}, "root": {}},
            "theme": {"colors": {"background": {"hex": "#FFFFFF"}}},
            "device_id": "emulator-5554",
        }

        with (
            patch("shutil.which", return_value="/usr/bin/adb"),
            patch("scripts.run_adb_pipeline.run_pipeline", return_value=mock_result),
            patch("tempfile.TemporaryDirectory", return_value=MagicMock()),
        ):
            client = TestClient(app)
            response = client.post(
                "/api/adb/capture",
                json={"deviceId": "emulator-5554"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["screenshotDataUrl"] == "data:image/png;base64,iVBORw0KGgo="
            assert data["deviceId"] == "emulator-5554"
            assert "skeleton" in data
            assert "theme" in data
            assert "designSystemBlock" in data
            assert "ADB Extracted Design Data" in data["designSystemBlock"]

    def test_capture_no_device_raises_503(self) -> None:
        """Should return 503 when no devices connected."""
        from fastapi.testclient import TestClient
        from main import app

        with (
            patch("shutil.which", return_value="/usr/bin/adb"),
            patch(
                "scripts.run_adb_pipeline.run_pipeline",
                side_effect=RuntimeError("No ADB devices connected"),
            ),
        ):
            client = TestClient(app)
            response = client.post("/api/adb/capture", json={"deviceId": None})
            assert response.status_code == 503


class TestRunAdbPipeline:
    """Tests for scripts.run_adb_pipeline.run_pipeline."""

    def test_pipeline_orchestrator_calls_all_steps(self, tmp_path: Path) -> None:
        """Verify pipeline calls capture → parse → extract in sequence."""
        from scripts.run_adb_pipeline import run_pipeline

        # Create a fake screenshot
        from PIL import Image

        screenshot_path = tmp_path / "screenshot.png"
        img = Image.new("RGB", (200, 100), (240, 240, 240))
        img.save(str(screenshot_path))

        # Create a fake ui_tree.xml
        ui_tree_path = tmp_path / "ui_tree.xml"
        ui_tree_path.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<hierarchy><node bounds="[0,0][200,100]" class="android.widget.FrameLayout">'
            '<node bounds="[10,10][100,30]" class="android.widget.TextView" text="Hello"/>'
            "</node></hierarchy>",
            encoding="utf-8",
        )

        with patch(
            "scripts.run_adb_pipeline.capture_device_ui",
            return_value={
                "screenshot": str(screenshot_path),
                "ui_tree": str(ui_tree_path),
                "device_id": "test-device",
            },
        ):
            result = run_pipeline(device_id="test-device", output_dir=str(tmp_path))

        assert result["device_id"] == "test-device"
        assert result["screenshot_data_url"].startswith("data:image/png;base64,")
        assert "skeleton" in result
        assert result["skeleton"]["screen"]["width"] == 200
        assert result["skeleton"]["screen"]["height"] == 100
        assert "theme" in result
        assert "colors" in result["theme"]
