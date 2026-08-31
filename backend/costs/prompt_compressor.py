"""Skeleton JSON truncation to keep prompt size bounded.

Complex UI skeletons can reach 20K+ tokens (4 variants x 30 steps x 20K =
2.4M tokens per generation). This module caps the skeleton to ~2000 tokens
(~8K characters) using a simple character-count heuristic.

The truncation produces an incomplete JSON string with a marker comment;
callers should not attempt to parse the truncated output as valid JSON.
Instead, the LLM treats it as context text.
"""

from __future__ import annotations

# 1 token ~= 4 chars (English/JSON); 2000 tokens ~= 8000 chars
_MAX_SKELETON_CHARS = 8000
_TRUNCATION_NOTICE = ' /* truncated for brevity */'


def truncate_skeleton(skeleton_json: str, max_chars: int = _MAX_SKELETON_CHARS) -> str:
    """Truncate skeleton JSON to max_chars, appending a truncation notice.

    The output is intentionally not valid JSON — it is a prefix of the
    original string with a marker appended. The LLM consumes it as context
    text, not as a parseable document.
    """
    if len(skeleton_json) <= max_chars:
        return skeleton_json

    cut = max_chars - len(_TRUNCATION_NOTICE)
    if cut <= 0:
        return skeleton_json[:max_chars]

    return skeleton_json[:cut] + _TRUNCATION_NOTICE
