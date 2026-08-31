"""Capture pipeline abstractions.

Exposes:
    - CaptureResult: dataclass returned by every pipeline implementation.
    - CapturePipeline: Protocol that all pipeline implementations must satisfy.
    - AdbCapturePipeline: wraps the existing ADB capture scripts.
    - WinUiaCapturePipeline: skeleton for Windows UI Automation capture (P2 fills in).
    - NoneCapturePipeline: no-op for stacks that do not support capture.

Pipelines are registered in CAPTURE_PIPELINES by id, matching the
``capture_pipeline_id`` field of StackConfig in stack_registry.py.
"""

from capture.result import CaptureResult
from capture.pipeline import (
    CAPTURE_PIPELINES,
    AdbCapturePipeline,
    CapturePipeline,
    NoneCapturePipeline,
    WinUiaCapturePipeline,
    get_pipeline,
)

__all__ = [
    "CAPTURE_PIPELINES",
    "AdbCapturePipeline",
    "CapturePipeline",
    "CaptureResult",
    "NoneCapturePipeline",
    "WinUiaCapturePipeline",
    "get_pipeline",
]
