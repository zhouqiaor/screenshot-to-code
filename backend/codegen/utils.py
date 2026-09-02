import re
from typing import Optional


def extract_html_content(text: str, stack: str = "") -> str:
    """Extract code content from LLM response, adapting to the target stack.

    For web stacks (html_tailwind, react_tailwind, etc.), this extracts
    the HTML content from <html> tags or markdown code fences.

    For native stacks (android_compose, android_xml, a2ui, qt_qml,
    windows_wpf, winui3), the extraction logic is stack-specific:
    - android_compose: extract Kotlin code from ```kotlin fences
    - android_xml: extract XML from ```xml fences
    - a2ui: extract JSONL from ```jsonl fences
    - qt_qml: extract QML from ```qml fences
    - windows_wpf / winui3: extract XAML from ```xml fences
    """
    # Check for <file path="..."> wrapper first (agent tool format)
    file_match = re.search(
        r'<file\s+path="([^"]+)">\s*(.*?)\s*</file>',
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if file_match:
        file_path = file_match.group(1)
        file_content = file_match.group(2).strip()
        # For multi-file stacks, return the main deliverable file
        if _is_main_file(file_path, stack):
            return extract_html_content(file_content, stack)
        return file_content

    # Strip markdown code fences if present, adapting to stack
    lang_map = {
        "android_compose": "kotlin",
        "android_xml": "xml",
        "a2ui": "jsonl",
        "qt_qml": "qml",
        "windows_wpf": "xml",
        "winui3": "xml",
    }
    lang = lang_map.get(stack, "html")

    # Strip markdown code fences
    text = re.sub(r'^```' + lang + r'?\s*\n?', '', text, flags=re.MULTILINE)
    text = re.sub(r'^```\s*$', '', text, flags=re.MULTILINE)

    # For web stacks: try to find DOCTYPE + html tags
    if stack == "" or stack in ("html_css", "html_tailwind", "react_tailwind", "bootstrap", "vue_tailwind", "ionic_tailwind"):
        match_with_doctype = re.search(
            r"(<!DOCTYPE\s+html[^>]*>.*?<html.*?>.*?</html>)", text, re.DOTALL | re.IGNORECASE
        )
        if match_with_doctype:
            return match_with_doctype.group(1)

        match = re.search(r"(<html.*?>.*?</html>)", text, re.DOTALL)
        if match:
            return match.group(1)
        else:
            print(
                "[HTML Extraction] No <html> tags found in the generated content"
            )
            return text

    # For native stacks: return the stripped text as-is
    # The LLM should have produced clean code without HTML wrapper
    return text.strip()


def _is_main_file(file_path: str, stack: str) -> bool:
    """Check if a file path is the main deliverable for a stack."""
    main_files = {
        "android_compose": ("MainActivity.kt",),
        "android_xml": ("activity_main.xml",),
        "a2ui": ("surface.jsonl",),
        "qt_qml": ("main.qml",),
        "windows_wpf": ("MainWindow.xaml",),
        "winui3": ("MainWindow.xaml",),
    }
    if stack in main_files:
        return file_path in main_files[stack]
    # Web stacks: index.html is the main file
    return file_path == "index.html"
