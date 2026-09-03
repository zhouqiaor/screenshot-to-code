"""Robust parser for Volcano Ark's ``<seed:tool_call>`` XML format.

The ``doubao-seed-evolving`` model (via the ``chat/completions`` endpoint, not
the Responses API) emits tool calls as inline XML instead of the standard
``tool_calls`` field. The XML has several observed variant attribute formats:

1. **Standard**:    ``<parameter name="content" string="true">...``
2. **Merged**:      ``<parameter name="content="true">...``  (the ``"`` and
   ``=true`` got merged into the name attribute)
3. **No string**:    ``<parameter name="content">...``
4. **Truncated**:    the closing ``</parameter>`` or ``</seed:tool_call>`` is
   missing because the response hit ``max_tokens``.

This module provides :func:`extract_seed_tool_calls` which tries all known
patterns and returns a list of dicts with ``name``, ``path`` and ``content``
keys. It also falls back to extracting content from markdown code blocks when
no ``<seed:tool_call>`` XML is found.
"""

import re
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Regex patterns — ordered from most-specific to most-permissive.
# ---------------------------------------------------------------------------

# Pattern 1: Full standard format with closing tags
_RE_STANDARD = re.compile(
    r'<seed:tool_call>\s*'
    r'<function\s+name="([^"]+)">\s*'
    r'(<parameter[^>]*>.*?</parameter>\s*)+'
    r'</function>\s*'
    r'</seed:tool_call>',
    re.DOTALL,
)

# Pattern 2: Individual parameter extraction — handles all attribute variants:
#   name="content" string="true"      (standard)
#   name="content="true"              (merged: name value absorbed ="true")
#   name="content"                     (no string attr)
#   name="content" string="true" other="stuff"   (extra attrs)
# The [^>]* after the name attribute absorbs any remaining attributes up to >.
_RE_PARAM = re.compile(
    r'<parameter\s+name="([^"]*?)"[^>]*>(.*?)(?:</parameter>|$)',
    re.DOTALL,
)

# Pattern 3: Function call without wrapping <seed:tool_call> tags
_RE_FUNCTION_LOOSE = re.compile(
    r'<function\s+name="([^"]+)">(.*?)(?:</function>|$)',
    re.DOTALL,
)

# Pattern 4: Markdown code block fallback
_RE_CODE_BLOCK = re.compile(
    r'```(?:kotlin|kt|html|xml|java|python|js|javascript|ts|typescript)?\s*\n(.*?)```',
    re.DOTALL,
)

# Known parameter name aliases for file path and file content
_PATH_KEYS = {"path", "file_path", "filepath", "filename"}
_CONTENT_KEYS = {"content", "code", "file_content", "body", "text"}


def _parse_parameters(inner_xml: str) -> Dict[str, str]:
    """Extract all ``<parameter name="...">value</parameter>`` pairs from the
    inner XML of a ``<function>`` element.

    Returns a dict mapping the normalised parameter name to its string value.
    """
    params: Dict[str, str] = {}
    for m in _RE_PARAM.finditer(inner_xml):
        raw_name = m.group(1).strip()
        value = m.group(2).strip()
        # Normalise merged format: name="content="true" -> "content"
        # This happens when the model merges the closing quote of name and the
        # opening of string= into the name attribute value.
        if raw_name.endswith('="true"'):
            raw_name = raw_name[:-len('="true"')]
        if raw_name.endswith("="):
            raw_name = raw_name[:-1]
        params[raw_name] = value
    return params


def _normalise_params(params: Dict[str, str]) -> Dict[str, str]:
    """Map known parameter name aliases to canonical ``path`` / ``content``."""
    result: Dict[str, str] = {}
    for key, val in params.items():
        lower_key = key.lower()
        if lower_key in _PATH_KEYS and "path" not in result:
            result["path"] = val
        elif lower_key in _CONTENT_KEYS and "content" not in result:
            result["content"] = val
        else:
            # Keep original key for anything else
            result[key] = val
    # If path wasn't found but there's a generic first param, use it
    if "path" not in result and "content" in result:
        for key, val in params.items():
            if key.lower() not in _CONTENT_KEYS:
                result["path"] = val
                break
    return result


def extract_seed_tool_calls(content: str) -> List[Dict[str, str]]:
    """Extract all ``<seed:tool_call>`` invocations from model output.

    Returns a list of dicts, each with keys:
        - ``name``: the function name (e.g. ``"create_file"``)
        - ``path``: the file path (if found)
        - ``content``: the file content (if found)
        - ``raw_params``: all parsed parameters dict

    The list is empty if no tool calls are found.
    """
    if not content or not content.strip():
        return []

    results: List[Dict[str, Any]] = []

    # --- Strategy 1: Full <seed:tool_call>...</seed:tool_call> blocks ---
    for m in _RE_STANDARD.finditer(content):
        func_name = m.group(1)
        inner = m.group(2) if m.lastindex and m.lastindex >= 2 else ""
        # m.group(2) captures the first <parameter> group due to the (...)
        # capture inside the pattern; we need the full inner content instead.
        # Re-extract from the original match span.
        full_match = m.group(0)
        # Extract the <function ...>...</function> part
        func_match = re.search(
            r'<function\s+name="[^"]+">(.*?)</function>',
            full_match,
            re.DOTALL,
        )
        inner_xml = func_match.group(1) if func_match else inner

        params = _parse_parameters(inner_xml)
        normalised = _normalise_params(params)
        results.append({
            "name": func_name,
            "path": normalised.get("path", ""),
            "content": normalised.get("content", ""),
            "raw_params": params,
        })

    if results:
        return results

    # --- Strategy 2: Loose <function name="...">...</function> without
    # <seed:tool_call> wrapper (sometimes the model omits the outer tags) ---
    for m in _RE_FUNCTION_LOOSE.finditer(content):
        func_name = m.group(1)
        inner_xml = m.group(2)
        # Skip if this is just XML the user sent (not a tool call)
        if func_name in ("create_file", "edit_file", "write_file", "create_directory"):
            params = _parse_parameters(inner_xml)
            normalised = _normalise_params(params)
            results.append({
                "name": func_name,
                "path": normalised.get("path", ""),
                "content": normalised.get("content", ""),
                "raw_params": params,
            })

    if results:
        return results

    # --- Strategy 3: Raw <parameter> tags without function wrapper ---
    params = _parse_parameters(content)
    if params:
        normalised = _normalise_params(params)
        if normalised.get("content"):
            results.append({
                "name": "create_file",  # assumed
                "path": normalised.get("path", ""),
                "content": normalised.get("content", ""),
                "raw_params": params,
            })

    return results


def extract_first_file(content: str) -> Optional[Dict[str, str]]:
    """Convenience: extract the first file (path + content) from model output.

    Tries ``<seed:tool_call>`` XML first, then falls back to markdown code
    blocks. Returns ``{"path": ..., "content": ...}`` or ``None``.
    """
    # Try seed:tool_call extraction
    calls = extract_seed_tool_calls(content)
    if calls:
        first = calls[0]
        if first.get("content"):
            path = first.get("path") or "MainActivity.kt"
            return {"path": path, "content": first["content"]}

    # Fallback: markdown code block
    code_match = _RE_CODE_BLOCK.search(content)
    if code_match:
        code = code_match.group(1).strip()
        # Guess file name from content
        path = "MainActivity.kt"
        if "<!DOCTYPE html" in code[:200].lower() or "<html" in code[:200].lower():
            path = "preview.html"
        elif "package " in code[:100]:
            path = "MainActivity.kt"
        return {"path": path, "content": code}

    # Last resort: try to find raw Kotlin/HTML
    kt_match = re.search(r'(package\s+\w+.*?)(?:```|\Z)', content, re.DOTALL)
    if kt_match:
        return {"path": "MainActivity.kt", "content": kt_match.group(1).strip()}

    html_match = re.search(
        r'(<!DOCTYPE html>.*?</html>)',
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if html_match:
        return {"path": "preview.html", "content": html_match.group(1)}

    html_match2 = re.search(
        r'(<html.*?</html>)',
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if html_match2:
        return {"path": "preview.html", "content": html_match2.group(1)}

    return None


def parse_seed_tool_call_content(
    raw_content: str,
) -> List[Dict[str, Any]]:
    """Parse ``<seed:tool_call>`` XML into tool-call dicts compatible with
    the existing :class:`ToolCall` infrastructure.

    Each dict has keys: ``id``, ``name``, ``arguments`` (a dict).
    """
    calls = extract_seed_tool_calls(raw_content)
    tool_calls: List[Dict[str, Any]] = []
    for i, call in enumerate(calls):
        args: Dict[str, Any] = {}
        if call.get("path"):
            args["path"] = call["path"]
        if call.get("content"):
            args["content"] = call["content"]
        # Include any other raw params
        raw_params = call.get("raw_params", {})
        if isinstance(raw_params, dict):
            for k, v in raw_params.items():
                if k not in args:
                    args[k] = v
        tool_calls.append({
            "id": f"seed-call-{i:04d}",
            "name": call.get("name") or "create_file",
            "arguments": args,
        })
    return tool_calls
