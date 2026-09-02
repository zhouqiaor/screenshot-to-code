"""CaptureResult dataclass shared by all capture pipeline implementations."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CaptureResult:
    """Normalized output of a capture pipeline run.

    Fields:
        screenshot_data_url: ``data:image/png;base64,...`` string for the
            captured screenshot, or empty string when no screenshot is
            available (e.g., NoneCapturePipeline).
        skeleton: Parsed UI hierarchy dict (component tree with bounds).
            Empty dict when not applicable.
        theme: Extracted design tokens dict (colors, typography, etc.).
            Empty dict when not applicable.
        target_id: Identifier of the captured target (device id, window
            handle, etc.).  Empty string when not applicable.
    """

    screenshot_data_url: str = ""
    skeleton: dict[str, Any] = field(default_factory=dict)
    theme: dict[str, Any] = field(default_factory=dict)
    target_id: str = ""
