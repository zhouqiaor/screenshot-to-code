"""Tests for ADB data collection scripts: skeleton_parser, theme_extractor, adb_capture, and policies."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

# Ensure backend dir is on path for imports
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


# ---------------------------------------------------------------------------
# skeleton_parser tests
# ---------------------------------------------------------------------------


class TestSkeletonParser:
    """Tests for scripts.skeleton_parser."""

    def test_parse_bounds_valid(self) -> None:
        from scripts.skeleton_parser import parse_bounds

        assert parse_bounds("[0,0][1080,2280]") == [0, 0, 1080, 2280]
        assert parse_bounds("[100,200][300,400]") == [100, 200, 300, 400]

    def test_parse_bounds_empty(self) -> None:
        from scripts.skeleton_parser import parse_bounds

        assert parse_bounds("") == [0, 0, 0, 0]
        assert parse_bounds("invalid") == [0, 0, 0, 0]

    def test_infer_component_type_switch(self) -> None:
        from scripts.skeleton_parser import infer_component_type

        assert infer_component_type("android.widget.Switch") == "switch"
        assert infer_component_type("android.widget.SeekBar") == "seekbar"
        assert infer_component_type("android.widget.TextView") == "text"
        assert infer_component_type("android.widget.Button") == "button"
        assert infer_component_type("android.widget.RecyclerView") == "list"
        assert infer_component_type("com.example.CustomView") == "unknown"

    def test_calculate_fill_ratio_no_children(self) -> None:
        from scripts.skeleton_parser import calculate_fill_ratio

        assert calculate_fill_ratio([0, 0, 100, 100], []) == 0.0

    def test_calculate_fill_ratio_full(self) -> None:
        from scripts.skeleton_parser import calculate_fill_ratio

        children = [{"bounds_device": [0, 0, 100, 100]}]
        ratio = calculate_fill_ratio([0, 0, 100, 100], children)
        assert ratio == 1.0

    def test_calculate_fill_ratio_partial(self) -> None:
        from scripts.skeleton_parser import calculate_fill_ratio

        # Child covers half the parent
        children = [{"bounds_device": [0, 0, 50, 100]}]
        ratio = calculate_fill_ratio([0, 0, 100, 100], children)
        assert 0.49 <= ratio <= 0.51

    def test_compute_visual_bounds_root(self) -> None:
        from scripts.skeleton_parser import compute_visual_bounds

        bounds = [100, 200, 300, 400]
        assert compute_visual_bounds(bounds, None) == bounds

    def test_compute_visual_bounds_nested(self) -> None:
        from scripts.skeleton_parser import compute_visual_bounds

        parent = [100, 200, 500, 600]
        child = [150, 250, 300, 400]
        result = compute_visual_bounds(child, parent)
        assert result == [50, 50, 200, 200]

    def test_parse_ui_tree_minimal(self, tmp_path: Path) -> None:
        from scripts.skeleton_parser import parse_ui_tree

        xml_content = """<?xml version='1.0' encoding='UTF-8'?>
<hierarchy>
  <node bounds="[0,0][1080,2400]" class="android.widget.FrameLayout" resource-id="" text="">
    <node bounds="[0,100][1080,300]" class="android.widget.TextView" text="Settings" resource-id="title"/>
    <node bounds="[0,400][1080,624]" class="android.widget.Switch" text="" resource-id="switch1" checked="true"/>
  </node>
</hierarchy>"""
        xml_path = tmp_path / "ui_tree.xml"
        xml_path.write_text(xml_content, encoding="utf-8")

        result = parse_ui_tree(str(xml_path))
        assert result["screen"]["width"] == 1080
        assert result["screen"]["height"] == 2400

        root = result["root"]
        assert root["class"] == "android.widget.FrameLayout"
        assert root["component_type"] == "container"
        assert len(root["children"]) == 2

        text_child = root["children"][0]
        assert text_child["component_type"] == "text"
        assert text_child["text"] == "Settings"

        switch_child = root["children"][1]
        assert switch_child["component_type"] == "switch"
        assert switch_child["state"] == "on"

    def test_parse_ui_tree_fill_ratio(self, tmp_path: Path) -> None:
        from scripts.skeleton_parser import parse_ui_tree

        xml_content = """<?xml version='1.0' encoding='UTF-8'?>
<hierarchy>
  <node bounds="[0,0][1080,2400]" class="android.widget.FrameLayout">
    <node bounds="[0,0][100,100]" class="android.widget.TextView" text="Small"/>
  </node>
</hierarchy>"""
        xml_path = tmp_path / "ui_tree.xml"
        xml_path.write_text(xml_content, encoding="utf-8")

        result = parse_ui_tree(str(xml_path))
        root = result["root"]
        # Child covers 100*100 / 1080*2400 ≈ 0.004 → fill_ratio very low
        assert root["fill_ratio"] < 0.1


# ---------------------------------------------------------------------------
# theme_extractor tests
# ---------------------------------------------------------------------------


class TestThemeExtractor:
    """Tests for scripts.theme_extractor."""

    def test_luminance_white(self) -> None:
        from scripts.theme_extractor import luminance

        assert luminance((255, 255, 255)) > 250
        assert luminance((0, 0, 0)) < 10

    def test_luminance_red(self) -> None:
        from scripts.theme_extractor import luminance

        # Red pixel: 0.299*255 ≈ 76
        assert 70 < luminance((255, 0, 0)) < 80

    def test_rgb_to_hex(self) -> None:
        from scripts.theme_extractor import _rgb_to_hex

        assert _rgb_to_hex(255, 255, 255) == "#FFFFFF"
        assert _rgb_to_hex(0, 0, 0) == "#000000"
        assert _rgb_to_hex(127, 82, 255) == "#7F52FF"

    def test_extract_text_color_dark_text_on_light_bg(self, tmp_path: Path) -> None:
        from scripts.theme_extractor import extract_text_color

        # Create a white image with dark text region
        img = Image.new("RGB", (200, 50), (255, 255, 255))
        # Draw dark text region
        for x in range(50, 150):
            for y in range(10, 40):
                img.putpixel((x, y), (30, 30, 30))

        result = extract_text_color(img, [0, 0, 200, 50])
        assert result is not None
        assert result.startswith("#")
        # Should be close to (30, 30, 30)
        r = int(result[1:3], 16)
        g = int(result[3:5], 16)
        b = int(result[5:7], 16)
        assert abs(r - 30) < 15
        assert abs(g - 30) < 15
        assert abs(b - 30) < 15

    def test_extract_text_color_all_white(self) -> None:
        from scripts.theme_extractor import extract_text_color

        img = Image.new("RGB", (100, 100), (255, 255, 255))
        result = extract_text_color(img, [0, 0, 100, 100])
        # No dark pixels → returns None
        assert result is None

    def test_extract_bg_color(self) -> None:
        from scripts.theme_extractor import extract_bg_color

        img = Image.new("RGB", (100, 100), (100, 150, 200))
        result = extract_bg_color(img, [0, 0, 100, 100])
        assert result == "#6496C8"

    def test_extract_bg_color_zero_bounds(self) -> None:
        from scripts.theme_extractor import extract_bg_color

        img = Image.new("RGB", (100, 100), (200, 200, 200))
        # Zero area → falls back to corner
        result = extract_bg_color(img, [0, 0, 0, 0])
        assert result.startswith("#")

    def test_extract_theme_basic(self, tmp_path: Path) -> None:
        from scripts.theme_extractor import extract_theme

        # Create a screenshot: blue background with white text
        img = Image.new("RGB", (1080, 2400), (240, 240, 240))
        # Draw some dark text
        for x in range(100, 400):
            for y in range(100, 150):
                img.putpixel((x, y), (50, 50, 50))
        screenshot_path = tmp_path / "screenshot.png"
        img.save(str(screenshot_path))

        skeleton = {
            "screen": {"width": 1080, "height": 2400},
            "root": {
                "class": "android.widget.FrameLayout",
                "component_type": "container",
                "bounds_device": [0, 0, 1080, 2400],
                "visual_bounds": [0, 0, 1080, 2400],
                "text": "",
                "children": [
                    {
                        "class": "android.widget.TextView",
                        "component_type": "text",
                        "bounds_device": [100, 100, 400, 150],
                        "text": "Settings",
                        "children": [],
                    },
                ],
            },
        }

        theme = extract_theme(str(screenshot_path), skeleton)
        assert "colors" in theme
        assert "background" in theme["colors"]
        assert theme["colors"]["background"]["hex"].startswith("#")
        assert theme["colors"]["background"]["method"] == "corner_sample"
        assert len(theme["colors"]["text_colors"]) >= 1
        assert theme["colors"]["text_colors"][0]["method"] == "dark_pixel_scan"
        assert "typography" in theme
        assert "borderRadius" in theme


# ---------------------------------------------------------------------------
# adb_capture tests (mocked subprocess)
# ---------------------------------------------------------------------------


class TestAdbCapture:
    """Tests for scripts.adb_capture."""

    def test_list_devices_with_devices(self) -> None:
        from scripts.adb_capture import list_devices

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="List of devices attached\nemulator-5554\tdevice\n192.168.1.100:5555\tdevice\n",
                returncode=0,
            )
            devices = list_devices()
            assert len(devices) == 2
            assert "emulator-5554" in devices
            assert "192.168.1.100:5555" in devices

    def test_list_devices_no_devices(self) -> None:
        from scripts.adb_capture import list_devices

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="List of devices attached\n",
                returncode=0,
            )
            devices = list_devices()
            assert len(devices) == 0

    def test_capture_device_ui_with_device_id(self, tmp_path: Path) -> None:
        from scripts.adb_capture import capture_device_ui

        with patch("scripts.adb_capture._run_adb") as mock_adb:
            mock_adb.return_value = MagicMock(returncode=0)
            result = capture_device_ui(
                device_id="emulator-5554",
                output_dir=str(tmp_path),
            )
            assert result["device_id"] == "emulator-5554"
            assert "screenshot" in result
            assert "ui_tree" in result
            # Should have called: screencap + pull + uiautomator dump + pull + cleanup rm = 5
            assert mock_adb.call_count == 5

    def test_capture_device_ui_no_device_raises(self, tmp_path: Path) -> None:
        from scripts.adb_capture import capture_device_ui

        with (
            patch("scripts.adb_capture.list_devices", return_value=[]),
            pytest.raises(RuntimeError, match="No ADB devices"),
        ):
            capture_device_ui(device_id=None, output_dir=str(tmp_path))


# ---------------------------------------------------------------------------
# policies (build_adb_data_policy) tests
# ---------------------------------------------------------------------------


class TestBuildAdbDataPolicy:
    """Tests for prompts.policies.build_adb_data_policy."""

    def test_both_none_returns_empty(self) -> None:
        from prompts.policies import build_adb_data_policy

        assert build_adb_data_policy(None, None) == ""
        assert build_adb_data_policy("", "") == ""

    def test_theme_only(self) -> None:
        from prompts.policies import build_adb_data_policy

        theme = json.dumps({"colors": {"background": "#FFFFFF"}})
        result = build_adb_data_policy(theme, None)
        assert "ADB Extracted Design Data" in result
        assert "theme.json" in result
        assert "skeleton.json" not in result

    def test_skeleton_only(self) -> None:
        from prompts.policies import build_adb_data_policy

        skeleton = json.dumps({"root": {"component_type": "container"}})
        result = build_adb_data_policy(None, skeleton)
        assert "ADB Extracted Design Data" in result
        assert "skeleton.json" in result
        # theme.json JSON block should not appear (only skeleton block)
        assert "### theme.json" not in result
        assert "### skeleton.json" in result
        assert "fill_ratio" in result

    def test_both_present(self) -> None:
        from prompts.policies import build_adb_data_policy

        theme = json.dumps({"colors": {}})
        skeleton = json.dumps({"root": {}})
        result = build_adb_data_policy(theme, skeleton)
        assert "theme.json" in result
        assert "skeleton.json" in result
        assert "fill_ratio < 0.5" in result
        assert "transparent" in result
        assert "bounds_device" in result
        assert "component_type" in result

    def test_includes_key_constraints(self) -> None:
        from prompts.policies import build_adb_data_policy

        skeleton = json.dumps({"root": {}})
        result = build_adb_data_policy(None, skeleton)
        # Verify all key constraints are present
        assert "fill_ratio < 0.5" in result
        assert "transparent" in result
        assert "hex codes" in result
        assert "bounds_device" in result
        assert "component_type" in result
        assert "state" in result


# ---------------------------------------------------------------------------
# adb_traversal blacklist tests
# ---------------------------------------------------------------------------


class TestTraversalBlacklist:
    """Fastbot-style widget + app blacklist behavior."""

    def test_is_blacklisted_pkg_substring(self) -> None:
        from scripts.adb_traversal import _is_blacklisted_pkg

        pkgs = ["com.device.meeting", "com.device.cp", "com.device.connect",
                "com.device.cloudlink.smartrooms", "org.chromium.chrome"]
        assert _is_blacklisted_pkg("com.device.cp", pkgs) is True
        assert _is_blacklisted_pkg("com.device.connect", pkgs) is True
        assert _is_blacklisted_pkg("com.device.cloudlink.smartrooms", pkgs) is True
        # target apps must NOT be blacklisted
        assert _is_blacklisted_pkg("com.device.settings", pkgs) is False
        assert _is_blacklisted_pkg("com.device.fileexplore", pkgs) is False
        assert _is_blacklisted_pkg("com.device.launcheridea", pkgs) is False
        # empty / partial substring guards
        assert _is_blacklisted_pkg("", pkgs) is False
        assert _is_blacklisted_pkg(None, pkgs) is False  # type: ignore[arg-type]

    def test_extract_actions_skips_blacklisted_launcher_tiles(self) -> None:
        from scripts.adb_traversal import _main_window, extract_actions, TraversalConfig
        import xml.etree.ElementTree as ET

        dump = Path("runs/adb_traversal/200_47_94_166-5555_20260903_003528/states/"
                    "000_9fab4613/ui_tree.xml")
        if not dump.exists():
            pytest.skip("recorded launcher dump not present")
        root = ET.parse(dump).getroot()
        cfg = TraversalConfig(blacklist="云会议,白板,投屏,智能管家,浏览器".split(","))
        acts = extract_actions(root, (3840, 2160), cfg)
        labels = {a.text for a in acts}
        assert "白板" not in labels
        assert "云会议" not in labels
        assert "投屏" not in labels
        # the real target tile survives
        assert any("setting" in (a.resource_id or "") for a in acts)
