import re


def extract_html_content(text: str, stack: str = "") -> str:
    file_match = re.search(
        r"<file\s+path=\"[^\"]+\">\s*(.*?)\s*</file>",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if file_match:
        return extract_html_content(file_match.group(1).strip(), stack=stack)

    # For non-web stacks (android_compose, qt_qml, etc.), strip markdown
    # code fences and return the raw code without trying to find <html>.
    if stack and stack not in ("html", "react", "vue", "bootstrap", "ionic", ""):
        text = re.sub(r'^```[a-zA-Z]*\s*\n?', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n?```\s*$', '', text, flags=re.MULTILINE)
        return text.strip()

    # First, strip markdown code fences if present
    text = re.sub(r'^```html?\s*\n?', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n?```\s*$', '', text, flags=re.MULTILINE)

    # Try to find DOCTYPE + html tags together
    match_with_doctype = re.search(
        r"(<!DOCTYPE\s+html[^>]*>.*?<html.*?>.*?</html>)", text, re.DOTALL | re.IGNORECASE
    )
    if match_with_doctype:
        return match_with_doctype.group(1)

    # Fall back to just <html> tags
    match = re.search(r"(<html.*?>.*?</html>)", text, re.DOTALL)
    if match:
        return match.group(1)
    else:
        # Otherwise, we just send the previous HTML over
        print(
            "[HTML Extraction] No <html> tags found in the generated content"
        )
        return text
