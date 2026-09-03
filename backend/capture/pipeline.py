"""CapturePipeline Protocol and concrete implementations.

The Protocol decouples capture logic (screenshot + skeleton + theme
extraction) from any specific platform (ADB, Windows UIA, etc.).  Each
stack's ``capture_pipeline_id`` in stack_registry.py maps to one entry in
``CAPTURE_PIPELINES`` below.
"""
from __future__ import annotations

import json
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
                try:
                    tmp.cleanup()
                except OSError:
                    logger.warning("Failed to clean up temp dir: %s", output_dir, exc_info=True)

        return CaptureResult(
            screenshot_data_url=result.get("screenshot_data_url", ""),
            skeleton=result.get("skeleton", {}),
            theme=result.get("theme", {}),
            target_id=result.get("device_id", target_id or ""),
        )


# ---------------------------------------------------------------------------
# AdbTraversalPipeline — multi-screen traversal (batch dataset capture)
# ---------------------------------------------------------------------------


class AdbTraversalPipeline:
    """Multi-screen ADB traversal pipeline.

    Walks the device UI (D-Pad or touch) and records a dataset of
    ``(screenshot, ui_tree.xml, skeleton.json)`` triples — one per distinct
    screen state — plus a state-transition graph (UTG).

    Unlike :class:`AdbCapturePipeline` (single screen), this is a **batch**
    pipeline: ``capture()`` returns an aggregated result whose ``skeleton``
    carries both the first screen's tree (backwards compatible with
    single-screen consumers) and a ``traversal`` block describing every state.

    Extra ``**kwargs``: ``package``, ``out_dir``, ``nav_mode``, ``max_depth``,
    ``max_states``, ``max_steps``, ``exclude_bottom_px``.

    See ``design-docs/adb-ui-traversal-design.md``.
    """

    pipeline_id = "adb_traversal"

    def capture(
        self,
        target_id: Optional[str] = None,
        **kwargs: Any,
    ) -> CaptureResult:
        import base64
        import shutil

        if shutil.which("adb") is None:
            raise RuntimeError(
                "ADB not found. Install Android Platform Tools and ensure "
                "'adb' is on PATH."
            )

        try:
            from scripts.adb_traversal import TraversalConfig, run_traversal
        except ImportError as e:
            raise RuntimeError(
                "Traversal script not found. Ensure "
                "'scripts/adb_traversal.py' exists and is importable."
            ) from e

        cfg = TraversalConfig(
            device=target_id,
            package=kwargs.get("package"),
            out_dir=kwargs.get("out_dir", "runs/adb_traversal"),
            nav_mode=kwargs.get("nav_mode", "auto"),
            max_depth=int(kwargs.get("max_depth", 3)),
            max_states=int(kwargs.get("max_states", 20)),
            max_steps=int(kwargs.get("max_steps", 120)),
            exclude_bottom_px=int(kwargs.get("exclude_bottom_px", 0)),
        )

        summary = run_traversal(cfg)
        run_dir = Path(summary["run_dir"])
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        graph = json.loads((run_dir / "graph.json").read_text(encoding="utf-8"))

        # Representative preview: the first recorded screen.
        screenshot_data_url = ""
        first_skeleton: dict[str, Any] = {}
        state_dirs = sorted(run_dir.glob("states/*"))
        if state_dirs:
            png = state_dirs[0] / "screenshot.png"
            if png.exists():
                encoded = base64.b64encode(png.read_bytes()).decode("utf-8")
                screenshot_data_url = f"data:image/png;base64,{encoded}"
            skel_path = state_dirs[0] / "skeleton.json"
            if skel_path.exists():
                first_skeleton = json.loads(skel_path.read_text(encoding="utf-8"))

        states: list[dict[str, Any]] = []
        for st in graph["states"]:
            d = run_dir / "states" / f"{st['index']:03d}_{st['id'][:8]}"
            states.append(
                {
                    **st,
                    "skeleton_path": str(d / "skeleton.json"),
                    "screenshot_path": str(d / "screenshot.png"),
                    "preview_path": str(d / "screenshot_768.jpg"),
                    "ui_tree_path": str(d / "ui_tree.xml"),
                }
            )

        return CaptureResult(
            screenshot_data_url=screenshot_data_url,
            skeleton={
                **first_skeleton,
                "traversal": {
                    "run_dir": str(run_dir),
                    "num_states": summary["states"],
                    "num_edges": summary["edges"],
                    "nav_mode": summary["nav_mode"],
                    "states": states,
                    "edges": graph["edges"],
                    "device_info": manifest.get("device_info", {}),
                },
            },
            theme={},
            target_id=target_id or "",
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
            mock = kwargs.get("mock")
            result = capture_window_ui(
                output_dir=str(output_dir),
                window_title=window_title,
                mock=mock,
            )

            screenshot_path = result.get("screenshot", "")
            ui_tree_path = result.get("ui_tree", "")

            # Parse skeleton from UIA XML using the shared skeleton_parser.
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
                try:
                    tmp.cleanup()
                except OSError:
                    logger.warning("Failed to clean up temp dir: %s", output_dir, exc_info=True)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

CAPTURE_PIPELINES: dict[str, CapturePipeline] = {
    "adb": AdbCapturePipeline(),
    "adb_traversal": AdbTraversalPipeline(),
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
