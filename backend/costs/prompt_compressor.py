"""Skeleton JSON truncation to keep prompt size bounded.

Complex UI skeletons can reach 20K+ tokens (4 variants × 30 steps × 20K =
2.4M tokens per generation). This module caps the skeleton to ~2000 tokens
(≈8K characters) using a simple character-count heuristic with a JSON-safe
truncation marker.
"""

from __future__ import annotations

# 1 token ≈ 4 chars (English/JSON); 2000 tokens ≈ 8000 chars
_MAX_SKELETON_CHARS = 8000
_TRUNCATION_MARKER = ',{"_truncated":true}]'


def truncate_skeleton(skeleton_json: str, max_chars: int = _MAX_SKELETON_CHARS) -> str:
    """Truncate skeleton JSON to max_chars, closing the JSON cleanly.

    If the input is already short, return it unchanged. Otherwise, find the
    last complete '}' that keeps us under the limit and append a marker
    so downstream consumers know truncation happened.
    """
    if len(skeleton_json) <= max_chars:
        return skeleton_json

    # Reserve space for the truncation marker
    cut_budget = max_chars - len(_TRUNCATION_MARKER)
    if cut_budget <= 0:
        # Edge case: very small max_chars — just hard cut
        return skeleton_json[:max_chars]

    truncated = skeleton_json[:cut_budget]
    last_brace = truncated.rfind("}")
    if last_brace >= 0:
        return truncated[: last_brace + 1] + _TRUNCATION_MARKER
    # No closing brace found — hard cut
    return truncated + _TRUNCATION_MARKER
