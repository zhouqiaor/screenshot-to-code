"""Generic code validation tool routed by stack type.

The validator checks well-formedness and basic structural correctness for
each supported stack without requiring external compilers or build tools.
It is intentionally lightweight: it catches syntax errors the LLM is most
likely to make (unclosed tags, unbalanced braces, malformed JSON) so the
agent loop can self-correct before returning a broken deliverable.

Dependencies kept minimal:
- html: lxml if available, otherwise ElementTree as a fallback.
- android_xml: ElementTree from the standard library.
- android_compose / qt_qml: regex + bracket balancing (no parser deps).
- a2ui: json.loads per line from the standard library.

jsonschema is optional; when unavailable, a2ui falls back to json.loads
plus a shallow structural check.
"""

from __future__ import annotations

import json
import re
from typing import Any, List, Literal, TypedDict

from xml.etree import ElementTree


Stack = Literal["html", "android_compose", "android_xml", "qt_qml", "a2ui"]

_SEVERITY = Literal["error", "warning"]


class ValidationIssue(TypedDict):
    line: int
    col: int
    message: str
    severity: _SEVERITY


class ValidationResult(TypedDict):
    ok: bool
    stack: Stack
    errors: List[ValidationIssue]
    warnings: List[ValidationIssue]


def validate_code(stack: Stack, code: str) -> ValidationResult:
    """Validate generated code by stack type.

    Returns a :class:`ValidationResult` with ``ok`` set to ``True`` when
    no errors were found.  Warnings are informational and do not flip
    ``ok`` to ``False``.
    """
    if not code:
        return ValidationResult(
            ok=False,
            stack=stack,
            errors=[
                ValidationIssue(
                    line=1,
                    col=1,
                    message="Empty code payload.",
                    severity="error",
                )
            ],
            warnings=[],
        )

    if stack == "html":
        errors, warnings = _validate_html(code)
    elif stack == "android_xml":
        errors, warnings = _validate_android_xml(code)
    elif stack == "android_compose":
        errors, warnings = _validate_android_compose(code)
    elif stack == "qt_qml":
        errors, warnings = _validate_qt_qml(code)
    elif stack == "a2ui":
        errors, warnings = _validate_a2ui(code)
    else:
        return ValidationResult(
            ok=False,
            stack=stack,
            errors=[
                ValidationIssue(
                    line=1,
                    col=1,
                    message=f"Unsupported stack: {stack}",
                    severity="error",
                )
            ],
            warnings=[],
        )

    return ValidationResult(
        ok=len(errors) == 0,
        stack=stack,
        errors=errors,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_HTML_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})

_HTML_TAG_RE = re.compile(
    r"<(/?)([a-zA-Z][a-zA-Z0-9]*)((?:\s+(?:[^>\"']|\"[^\"]*\"|'[^']*')*)?)(/?)>",
    re.DOTALL,
)

# Strips HTML comments, <script> blocks, and <style> blocks before tag matching
_HTML_STRIP_RE = re.compile(
    r"<!--[\s\S]*?-->"  # HTML comments
    r"|<script\b[^>]*>[\s\S]*?</script\s*>"  # script blocks
    r"|<style\b[^>]*>[\s\S]*?</style\s*>",  # style blocks
    re.IGNORECASE | re.DOTALL,
)


def _line_col_from_offset(text: str, offset: int) -> tuple[int, int]:
    """Return the 1-based (line, col) for a 0-based character offset."""
    if offset <= 0:
        return 1, 1
    upto = text[:offset]
    line = upto.count("\n") + 1
    last_nl = upto.rfind("\n")
    col = offset - last_nl if last_nl >= 0 else offset + 1
    return line, col


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------


def _validate_html(code: str) -> tuple[List[ValidationIssue], List[ValidationIssue]]:
    errors: List[ValidationIssue] = []
    warnings: List[ValidationIssue] = []

    try:
        import lxml.etree as lxml_etree  # type: ignore[import-not-found]
    except ImportError:
        lxml_etree = None  # type: ignore[assignment]

    if lxml_etree is not None:
        try:
            parser: Any = lxml_etree.HTMLParser(recover=False)  # type: ignore[union-attr]
            lxml_etree.fromstring(code.encode("utf-8"), parser=parser)  # type: ignore[union-attr]
            error_log: Any = getattr(parser, "error_log", None)
            if error_log:
                for entry in error_log:
                    level: int = int(getattr(entry, "level", 0))
                    severity: _SEVERITY = "error" if level >= 2 else "warning"
                    issue = ValidationIssue(
                        line=max(int(getattr(entry, "line", 1)), 1),
                        col=max(int(getattr(entry, "column", 1)), 1),
                        message=str(getattr(entry, "message", "") or "HTML parse error"),
                        severity=severity,
                    )
                    (errors if severity == "error" else warnings).append(issue)
        except Exception as exc:
            errors.append(
                ValidationIssue(
                    line=1,
                    col=1,
                    message=f"HTML parse error: {exc}",
                    severity="error",
                )
            )
        return errors, warnings

    # Fallback: parse as XML and accept HTML5 void elements.
    # Strip comments, scripts, and styles to avoid false-positive tag
    # matches on angle brackets inside those regions.
    stripped_html = _HTML_STRIP_RE.sub("", code)
    stack: List[str] = []
    for match in _HTML_TAG_RE.finditer(stripped_html):
        closing = match.group(1) == "/"
        tag = match.group(2).lower()
        self_close = match.group(4) == "/"
        line, col = _line_col_from_offset(code, match.start())
        if closing:
            if not stack:
                errors.append(
                    ValidationIssue(
                        line=line,
                        col=col,
                        message=f"Unexpected closing tag </{tag}> with empty stack.",
                        severity="error",
                    )
                )
                continue
            last = stack.pop()
            if last != tag:
                errors.append(
                    ValidationIssue(
                        line=line,
                        col=col,
                        message=f"Mismatched tag: expected </{last}> but got </{tag}>.",
                        severity="error",
                    )
                )
        elif not self_close and tag not in _HTML_VOID_TAGS:
            stack.append(tag)
    for tag in reversed(stack):
        errors.append(
            ValidationIssue(
                line=1,
                col=1,
                message=f"Unclosed tag <{tag}>.",
                severity="error",
            )
        )
    return errors, warnings


# ---------------------------------------------------------------------------
# Android XML
# ---------------------------------------------------------------------------


def _validate_android_xml(code: str) -> tuple[List[ValidationIssue], List[ValidationIssue]]:
    errors: List[ValidationIssue] = []
    warnings: List[ValidationIssue] = []

    try:
        root = ElementTree.fromstring(code)
    except ElementTree.ParseError as exc:
        msg = str(exc)
        position = getattr(exc, "position", (1, 0))
        line = int(position[0]) if position and position[0] else 1
        col = int(position[1]) + 1 if position and len(position) > 1 else 1
        errors.append(
            ValidationIssue(
                line=line,
                col=col,
                message=f"XML parse error: {msg}",
                severity="error",
            )
        )
        return errors, warnings

    allowed_roots = {
        "androidx.constraintlayout.widget.ConstraintLayout",
        "LinearLayout",
        "RelativeLayout",
        "FrameLayout",
        "androidx.coordinatorlayout.widget.CoordinatorLayout",
        "ScrollView",
        "androidx.core.widget.NestedScrollView",
        "merge",
    }
    if root.tag not in allowed_roots:
        warnings.append(
            ValidationIssue(
                line=1,
                col=1,
                message=(
                    f"Unexpected root element <{root.tag}>. "
                    f"Expected one of: {sorted(allowed_roots)}."
                ),
                severity="warning",
            )
        )

    if "xmlns:android" not in code:
        warnings.append(
            ValidationIssue(
                line=1,
                col=1,
                message="Missing xmlns:android namespace declaration on root.",
                severity="warning",
            )
        )

    return errors, warnings


# ---------------------------------------------------------------------------
# Android Compose (Kotlin)
# ---------------------------------------------------------------------------


_COMPOSABLE_RE = re.compile(
    r"@Composable(?:\([^)]*\))?\s+(?:private\s+|internal\s+)*fun\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)
_IMPORT_RE = re.compile(r"^\s*import\s+([a-zA-Z][\w.]*)", re.MULTILINE)


# Strip string literals and comments before brace/paren counting.
# A single combined regex pass avoids misclassifying comment-like sequences
# (e.g. URLs containing "//") that appear inside string literals, because
# the string alternative is matched first (leftmost alternation wins).
_STRIP_RE = re.compile(
    r'"""[\s\S]*?"""'  # triple-quoted strings
    r'|"(?:\\.|[^"\\])*"'  # double-quoted strings
    r"|'(?:\\.|[^'\\])*'"  # single-quoted strings
    r'|//[^\n]*'  # line comments
    r'|/\*[\s\S]*?\*/'  # block comments
)


def _strip_comments_and_strings(text: str) -> str:
    return _STRIP_RE.sub("", text)


def _check_balanced(text: str, open_ch: str, close_ch: str) -> int:
    depth = 0
    for ch in text:
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth < 0:
                return -1
    return depth


def _validate_android_compose(code: str) -> tuple[List[ValidationIssue], List[ValidationIssue]]:
    errors: List[ValidationIssue] = []
    warnings: List[ValidationIssue] = []

    if "@Composable" not in code:
        errors.append(
            ValidationIssue(
                line=1,
                col=1,
                message="No @Composable annotation found in Kotlin source.",
                severity="error",
            )
        )
    else:
        matches = list(_COMPOSABLE_RE.finditer(code))
        if not matches:
            errors.append(
                ValidationIssue(
                    line=1,
                    col=1,
                    message="@Composable present but no composable fun signature detected.",
                    severity="error",
                )
            )

    stripped = _strip_comments_and_strings(code)

    brace_depth = _check_balanced(stripped, "{", "}")
    if brace_depth < 0:
        errors.append(
            ValidationIssue(
                line=1,
                col=1,
                message="Unbalanced braces: more '}' than '{'.",
                severity="error",
            )
        )
    elif brace_depth > 0:
        errors.append(
            ValidationIssue(
                line=1,
                col=1,
                message=f"Unbalanced braces: {brace_depth} unclosed '{{'.",
                severity="error",
            )
        )

    paren_depth = _check_balanced(stripped, "(", ")")
    if paren_depth < 0:
        errors.append(
            ValidationIssue(
                line=1,
                col=1,
                message="Unbalanced parentheses: more ')' than '('.",
                severity="error",
            )
        )
    elif paren_depth > 0:
        errors.append(
            ValidationIssue(
                line=1,
                col=1,
                message=f"Unbalanced parentheses: {paren_depth} unclosed '('.",
                severity="error",
            )
        )

    if not _IMPORT_RE.search(code):
        warnings.append(
            ValidationIssue(
                line=1,
                col=1,
                message="No import statements found; Compose code usually imports androidx.compose.*.",
                severity="warning",
            )
        )

    return errors, warnings


# ---------------------------------------------------------------------------
# Qt QML
# ---------------------------------------------------------------------------


_QML_IMPORT_RE = re.compile(r"^\s*import\s+\S+", re.MULTILINE)
_QML_PROPERTY_RE = re.compile(r"^\s*property\s+(\w+)\s+(\w+)\s*:", re.MULTILINE)


def _validate_qt_qml(code: str) -> tuple[List[ValidationIssue], List[ValidationIssue]]:
    errors: List[ValidationIssue] = []
    warnings: List[ValidationIssue] = []

    stripped_qml = _strip_comments_and_strings(code)
    brace_depth = _check_balanced(stripped_qml, "{", "}")
    if brace_depth < 0:
        errors.append(
            ValidationIssue(
                line=1,
                col=1,
                message="Unbalanced braces: more '}' than '{'.",
                severity="error",
            )
        )
    elif brace_depth > 0:
        errors.append(
            ValidationIssue(
                line=1,
                col=1,
                message=f"Unbalanced braces: {brace_depth} unclosed '{{'.",
                severity="error",
            )
        )

    if not _QML_IMPORT_RE.search(code):
        warnings.append(
            ValidationIssue(
                line=1,
                col=1,
                message="No import statements found; QML files usually import QtQuick.",
                severity="warning",
            )
        )

    property_re = _QML_PROPERTY_RE
    matches = list(property_re.finditer(code))
    if not matches and "property " in code:
        for line_no, line in enumerate(code.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("property ") and ":" not in stripped:
                errors.append(
                    ValidationIssue(
                        line=line_no,
                        col=1,
                        message="Malformed property declaration (missing ':').",
                        severity="error",
                    )
                )

    return errors, warnings


# ---------------------------------------------------------------------------
# a2ui (line-delimited JSON)
# ---------------------------------------------------------------------------


def _validate_a2ui(code: str) -> tuple[List[ValidationIssue], List[ValidationIssue]]:
    errors: List[ValidationIssue] = []
    warnings: List[ValidationIssue] = []

    try:
        import jsonschema  # type: ignore[import-not-found]
        jsonschema_ok = True
    except ImportError:
        jsonschema_ok = False

    lines = code.splitlines()
    if not lines:
        errors.append(
            ValidationIssue(
                line=1,
                col=1,
                message="Empty a2ui payload.",
                severity="error",
            )
        )
        return errors, warnings

    allowed_types = {
        "container", "card", "column", "row", "text", "button",
        "input", "image", "list", "stack",
    }

    schema: dict[str, Any] = {
        "type": "object",
        "required": ["id", "type"],
        "properties": {
            "id": {"type": "string"},
            "type": {"type": "string"},
            "children": {"type": "array"},
            "text": {"type": "string"},
            "bind": {"type": "object"},
            "onClick": {"type": "string"},
            "style": {"type": "object"},
            "src": {"type": "string"},
            "placeholder": {"type": "string"},
        },
    }

    seen_ids: dict[str, int] = {}

    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError as exc:
            errors.append(
                ValidationIssue(
                    line=idx,
                    col=exc.pos + 1 if hasattr(exc, "pos") else 1,
                    message=f"Invalid JSON: {exc.msg}",
                    severity="error",
                )
            )
            continue
        if not isinstance(obj, dict):
            errors.append(
                ValidationIssue(
                    line=idx,
                    col=1,
                    message="Each a2ui line must be a JSON object.",
                    severity="error",
                )
            )
            continue
        if jsonschema_ok:
            try:
                jsonschema.validate(instance=obj, schema=schema)
            except jsonschema.ValidationError as exc:
                errors.append(
                    ValidationIssue(
                        line=idx,
                        col=1,
                        message=f"Schema validation failed: {exc.message}",
                        severity="error",
                    )
                )
        else:
            if "type" not in obj:
                errors.append(
                    ValidationIssue(
                        line=idx,
                        col=1,
                        message="Missing required field 'type'.",
                        severity="error",
                    )
                )
            if "id" not in obj:
                errors.append(
                    ValidationIssue(
                        line=idx,
                        col=1,
                        message="Missing required field 'id'.",
                        severity="error",
                    )
                )

        # Check type value is in the allowed set (warning, not error —
        # forward compatibility with future types).
        obj_type = obj.get("type")
        if isinstance(obj_type, str) and obj_type not in allowed_types:
            warnings.append(
                ValidationIssue(
                    line=idx,
                    col=1,
                    message=f"Unknown type '{obj_type}'. Expected one of: {sorted(allowed_types)}.",
                    severity="warning",
                )
            )

        # Check for duplicate ids
        obj_id = obj.get("id")
        if isinstance(obj_id, str):
            if obj_id in seen_ids:
                errors.append(
                    ValidationIssue(
                        line=idx,
                        col=1,
                        message=f"Duplicate id '{obj_id}' (first seen on line {seen_ids[obj_id]}).",
                        severity="error",
                    )
                )
            else:
                seen_ids[obj_id] = idx

    return errors, warnings


__all__ = [
    "Stack",
    "ValidationIssue",
    "ValidationResult",
    "validate_code",
]
