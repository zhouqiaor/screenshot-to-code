"""CapturePipeline Protocol and concrete implementations.

The Protocol decouples capture logic (screenshot + skeleton + theme
extraction) from any specific platform (ADB, Windows UIA, etc.).  Each
stack's ``capture_pipeline_id`` in stack_registry.py maps to one entry in
``CAPTURE_PIPELINES`` below.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable

from capture.result import CaptureResult

logger = logging.getLogger(__name__)


@runtime_checkable
class CapturePipeline(Protocol):
    """Protocol every capture pipeline must implement.

    Implementations may be classes or modules; the only requirement is that
    they expose a ``capture`` method with this signature.
    """

    def capture(
        self,
        target_id: Optional[str] = None,
        **kwargs: Any,
    ) -> CaptureResult:
        """Run the capture pipeline and return a normalized CaptureResult.

        Args:
            target_id: Platform-specific target identifier (ADB device id,
                window handle, etc.).  ``None`` means auto-detect.
            **kwargs: Pipeline-specific options passed through by the caller.

        Raises:
            RuntimeError: When the required tool / device is unavailable.
        """
        ...


# ---------------------------------------------------------------------------
# NoneCapturePipeline — no-op for stacks that do not support capture
# ---------------------------------------------------------------------------


class NoneCapturePipeline:
    """No-op pipeline for stacks without capture support.

    Returns an empty CaptureResult.  Used by html stacks and a2ui.
    """

    def capture(
        self,
        target_id: Optional[str] = None,
        **kwargs: Any,
    ) -> CaptureResult:
        return CaptureResult()


# ---------------------------------------------------------------------------
# AdbCapturePipeline — wraps the existing ADB scripts
# ---------------------------------------------------------------------------


class AdbCapturePipeline:
    """ADB capture pipeline for Android devices.

    Delegates to ``scripts.run_adb_pipeline.run_pipeline`` which runs:
    screencap → uiautomator dump → skeleton parse → theme extraction.
    """

    pipeline_id = "adb"

    def capture(
        self,
        target_id: Optional[str] = None,
        **kwargs: Any,
    ) -> CaptureResult:
        import shutil
        import tempfile

        if shutil.which("adb") is None:
            raise RuntimeError(
                "ADB not found. Install Android Platform Tools and ensure "
                "'adb' is on PATH."
            )

        try:
            from scripts.run_adb_pipeline import run_pipeline
        except ImportError as e:
            raise RuntimeError(
                "ADB pipeline script not found. Ensure "
                "'scripts/run_adb_pipeline.py' exists and is importable."
            ) from e

        output_dir = kwargs.get("output_dir")
        if output_dir is None:
            tmp = tempfile.TemporaryDirectory(prefix="adb_capture_")
            output_dir = tmp.name
        else:
            tmp = None

        try:
            result = run_pipeline(device_id=target_id, output_dir=str(output_dir))
        finally:
            if tmp is not None:
                tmp.cleanup()

        return CaptureResult(
            screenshot_data_url=result.get("screenshot_data_url", ""),
            skeleton=result.get("skeleton", {}),
            theme=result.get("theme", {}),
            target_id=result.get("device_id", target_id or ""),
        )


# ---------------------------------------------------------------------------
# WinUiaCapturePipeline — skeleton for Windows UI Automation (P2 fills in)
# ---------------------------------------------------------------------------


class WinUiaCapturePipeline:
    """Windows UI Automation capture pipeline.

    Delegates to ``capture.win_uia.capture_window_ui`` which runs:
    screenshot → UIA tree dump → skeleton parse → theme extraction.

    Falls back to mock mode when ``MOCK_WIN_UIA=1`` is set or the real
    UIA toolchain is unavailable.
    """

    pipeline_id = "win_uia"

    def capture(
        self,
        target_id: Optional[str] = None,
        **kwargs: Any,
    ) -> CaptureResult:
        import tempfile

        from capture.win_uia import capture_window_ui

        output_dir = kwargs.get("output_dir")
        if output_dir is None:
            tmp = tempfile.TemporaryDirectory(prefix="win_uia_capture_")
            output_dir = tmp.name
        else:
            tmp = None

        try:
            window_title = target_id if target_id else None
            result = capture_window_ui(
                output_dir=str(output_dir),
                window_title=window_title,
            )

            screenshot_path = result.get("screenshot", "")
            ui_tree_path = result.get("ui_tree", "")

            # Parse skeleton from UIA XML (prefer win_skeleton_parser, fall
            # back to the shared skeleton_parser).
            skeleton: dict[str, Any] = {}
            if ui_tree_path and Path(ui_tree_path).exists():
                try:
                    from scripts.skeleton_parser import parse_ui_tree
                    skeleton = parse_ui_tree(ui_tree_path)
                except Exception:
                    logger.warning("skeleton_parser failed, skeleton will be empty", exc_info=True)

            # Extract theme from screenshot (requires skeleton).
            theme: dict[str, Any] = {}
            if screenshot_path and Path(screenshot_path).exists() and skeleton:
                try:
                    from scripts.theme_extractor import extract_theme
                    theme = extract_theme(screenshot_path, skeleton)
                except Exception:
                    logger.warning("theme_extractor failed, theme will be empty", exc_info=True)

            # Convert screenshot to data URL.
            screenshot_data_url = ""
            if screenshot_path and Path(screenshot_path).exists():
                try:
                    from capture.win_uia import screenshot_to_data_url
                    screenshot_data_url = screenshot_to_data_url(screenshot_path)
                except Exception:
                    logger.warning("screenshot_to_data_url failed", exc_info=True)
                    screenshot_data_url = ""

            return CaptureResult(
                screenshot_data_url=screenshot_data_url,
                skeleton=skeleton,
                theme=theme,
                target_id=result.get("window_title", target_id or ""),
            )
        finally:
            if tmp is not None:
                tmp.cleanup()


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

CAPTURE_PIPELINES: dict[str, CapturePipeline] = {
    "adb": AdbCapturePipeline(),
    "win_uia": WinUiaCapturePipeline(),
    "none": NoneCapturePipeline(),
}


def get_pipeline(pipeline_id: Optional[str]) -> CapturePipeline:
    """Return the pipeline for *pipeline_id*, or NoneCapturePipeline when None.

    Raises ValueError for unknown pipeline ids.
    """
    if pipeline_id is None:
        return NoneCapturePipeline()
    if pipeline_id not in CAPTURE_PIPELINES:
        raise ValueError(
            f"Unknown capture pipeline id: {pipeline_id!r}. "
            f"Available: {sorted(CAPTURE_PIPELINES.keys())}"
        )
    return CAPTURE_PIPELINES[pipeline_id]
