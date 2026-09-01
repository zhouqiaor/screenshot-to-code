"""History image truncation for token optimization (T5).

Strips image data from older conversation history messages, keeping only
the most recent N images. This prevents token bloat when the user has
many back-and-forth edit rounds with screenshots.

Design ref: design-docs/token-governance-design.md §T5
"""

from __future__ import annotations

from prompts.prompt_types import PromptHistoryMessage

# Keep images in the most recent N user turns; strip from older turns.
# Each screenshot can cost 1K-2K image tokens, so stripping 5 old images
# saves 5K-10K tokens per request.
_KEEP_RECENT_IMAGE_TURNS = 2


def truncate_history_images(
    history: list[PromptHistoryMessage],
    keep_recent: int = _KEEP_RECENT_IMAGE_TURNS,
) -> list[PromptHistoryMessage]:
    """Remove image URLs from older history messages.

    Traverses the history in reverse, counting user turns that contain
    images. After ``keep_recent`` image-bearing turns, all subsequent
    older messages have their ``images`` list replaced with an empty list.

    The text content is preserved so the LLM retains conversational context.

    Args:
        history: List of prompt history messages (user/assistant turns).
        keep_recent: Number of recent image-bearing user turns to keep
            images for. Default 2.

    Returns:
        New list with the same message order, but older images stripped.
    """
    if not history:
        return history

    result = list(history)  # shallow copy
    image_turns_seen = 0

    for msg in reversed(result):
        if msg.get("role") != "user":
            continue
        images = msg.get("images", [])
        if not images:
            continue
        image_turns_seen += 1
        if image_turns_seen > keep_recent:
            # Replace with a copy that has empty images
            msg["images"] = []

    return result
