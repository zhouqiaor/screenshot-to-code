"""Tests for the <seed:tool_call> XML parser.

Validates that the parser handles all known variant attribute formats
produced by the doubao-seed-evolving model via the Volcano Ark
chat/completions endpoint.
"""
import pytest

from agent.tools.seed_tool_call import (
    extract_first_file,
    extract_seed_tool_calls,
    parse_seed_tool_call_content,
)


_STANDARD = (
    '<seed:tool_call><function name="create_file">'
    '<parameter name="path" string="true">MainActivity.kt</parameter>'
    '<parameter name="content" string="true">package com.test</parameter>'
    '</function></seed:tool_call>'
)

_MERGED = (
    '<seed:tool_call><function name="create_file">'
    '<parameter name="path" string="true">MainActivity.kt</parameter>'
    '<parameter name="content="true">package com.test2</parameter>'
    '</function></seed:tool_call>'
)

_NO_STRING = (
    '<seed:tool_call><function name="create_file">'
    '<parameter name="path">MainActivity.kt</parameter>'
    '<parameter name="content">package com.test3</parameter>'
    '</function></seed:tool_call>'
)

_TRUNCATED = (
    '<seed:tool_call><function name="create_file">'
    '<parameter name="path" string="true">MainActivity.kt</parameter>'
    '<parameter name="content" string="true">package com.test4'
)

_MULTI = (
    '<seed:tool_call><function name="create_file">'
    '<parameter name="path" string="true">First.kt</parameter>'
    '<parameter name="content" string="true">package com.first</parameter>'
    '</function></seed:tool_call>'
    '<seed:tool_call><function name="create_file">'
    '<parameter name="path" string="true">Second.kt</parameter>'
    '<parameter name="content" string="true">package com.second</parameter>'
    '</function></seed:tool_call>'
)


def test_extract_standard_format() -> None:
    r = extract_first_file(_STANDARD)
    assert r is not None
    assert r["path"] == "MainActivity.kt"
    assert r["content"] == "package com.test"


def test_extract_merged_format() -> None:
    r = extract_first_file(_MERGED)
    assert r is not None
    assert r["content"] == "package com.test2"


def test_extract_no_string_attr() -> None:
    r = extract_first_file(_NO_STRING)
    assert r is not None
    assert r["content"] == "package com.test3"


def test_extract_truncated() -> None:
    r = extract_first_file(_TRUNCATED)
    assert r is not None
    assert r["content"] == "package com.test4"


def test_extract_multiple_calls() -> None:
    calls = extract_seed_tool_calls(_MULTI)
    assert len(calls) == 2
    assert calls[0]["path"] == "First.kt"
    assert calls[1]["path"] == "Second.kt"


def test_markdown_fallback() -> None:
    content = "Here is the code:\n```kotlin\npackage com.test5\nclass MainActivity\n```\n"
    r = extract_first_file(content)
    assert r is not None
    assert "package com.test5" in r["content"]


def test_html_fallback() -> None:
    content = "Some text <!DOCTYPE html><html><head></head><body></body></html> more text"
    r = extract_first_file(content)
    assert r is not None
    assert r["path"] == "preview.html"


def test_parse_seed_tool_call_content() -> None:
    calls = parse_seed_tool_call_content(_STANDARD)
    assert len(calls) == 1
    assert calls[0]["name"] == "create_file"
    assert calls[0]["arguments"]["path"] == "MainActivity.kt"
    assert calls[0]["arguments"]["content"] == "package com.test"


def test_parse_multiple_tool_calls() -> None:
    calls = parse_seed_tool_call_content(_MULTI)
    assert len(calls) == 2
    assert calls[1]["arguments"]["path"] == "Second.kt"


def test_empty_input() -> None:
    assert extract_seed_tool_calls("") == []
    assert extract_seed_tool_calls("   ") == []
    assert extract_first_file("") is None
