"""Image compression for multi-modal LLM token optimization (T1).

Compresses screenshots to 768px wide JPEG before sending to vision LLMs.
This reduces the base64 payload from ~872KB (PNG) to ~65KB (JPEG),
cutting image tokens by ~80% with minimal visual quality loss.

Design ref: design-docs/token-governance-design.md §T1
"""

from __future__ import annotations

import base64
import io
from typing import Optional

try:
    from PIL import Image  # type: ignore[import-not-found]
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


_MAX_WIDTH = 768
_JPEG_QUALITY = 85


def compress_image_data_url(
    image_data_url: str,
    max_width: int = _MAX_WIDTH,
    quality: int = _JPEG_QUALITY,
) -> str:
    """Compress a base64 data URL image to JPEG at max_width.

    If PIL is not available, returns the original URL unchanged (graceful
    degradation — the LLM still works, just costs more tokens).

    Args:
        image_data_url: A ``data:image/...;base64,...`` URL.
        max_width: Target maximum width in pixels. Height is scaled
            proportionally. Default 768px.
        quality: JPEG quality 1-100. Default 85.

    Returns:
        A ``data:image/jpeg;base64,...`` URL with the compressed image,
        or the original URL if compression is not possible.
    """
    if not _PIL_AVAILABLE:
        return image_data_url

    # Parse the data URL
    try:
        if "," not in image_data_url:
            return image_data_url
        header, b64_data = image_data_url.split(",", 1)
        if "base64" not in header:
            return image_data_url
        raw_bytes = base64.b64decode(b64_data)
    except Exception:
        return image_data_url

    try:
        img = Image.open(io.BytesIO(raw_bytes))
    except Exception:
        return image_data_url

    # Resize if wider than max_width
    orig_width, orig_height = img.size
    if orig_width > max_width:
        ratio = max_width / orig_width
        new_height = max(1, int(orig_height * ratio))
        img = img.resize((max_width, new_height), Image.LANCZOS)

    # Convert to RGB (JPEG doesn't support alpha)
    if img.mode in ("RGBA", "LA", "P"):
        # Composite onto white background for transparency
        bg = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        if img.mode in ("RGBA", "LA"):
            bg.paste(img, mask=img.split()[-1])
        else:
            bg.paste(img)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Save as JPEG
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    compressed_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    return f"data:image/jpeg;base64,{compressed_b64}"


def estimate_token_saving(original_size: int, compressed_size: int) -> float:
    """Estimate the percentage token saving from compression.

    Uses a simple byte-ratio heuristic: image tokens scale roughly
    linearly with base64 payload size for the same model.
    """
    if original_size <= 0:
        return 0.0
    return max(0.0, 1.0 - (compressed_size / original_size))
