"""Parse uiautomator dump XML into skeleton.json format for Android Compose codegen.

The skeleton.json contains a tree of UI nodes with:
- class name, bounds, resource_id, text
- inferred component_type (switch, seekbar, text, button, etc.)
- fill_ratio (how much of the element bounds is filled by content)
- visual_bounds (bounds relative to parent)

Usage:
    python -m scripts.skeleton_parser <ui_tree.xml> [--output skeleton.json]
    python backend/scripts/skeleton_parser.py ui_tree.xml -o skeleton.json
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

# Mapping from Android class names to semantic component types
_CLASS_MAPPING: dict[str, str] = {
    "android.widget.Switch": "switch",
    "android.widget.SeekBar": "seekbar",
    "android.widget.TextView": "text",
    "android.widget.EditText": "text_input",
    "android.widget.ImageView": "image",
    "android.widget.ImageButton": "image_button",
    "android.widget.Button": "button",
    "android.widget.CheckBox": "checkbox",
    "android.widget.RadioButton": "radio_button",
    "android.widget.LinearLayout": "container",
    "android.widget.FrameLayout": "container",
    "android.widget.RelativeLayout": "container",
    "android.widget.ConstraintLayout": "container",
    "androidx.constraintlayout.widget.ConstraintLayout": "container",
    "android.widget.RecyclerView": "list",
    "androidx.recyclerview.widget.RecyclerView": "list",
    "android.widget.ListView": "list",
    "android.widget.ScrollView": "scroll",
    "androidx.core.widget.NestedScrollView": "scroll",
    "android.widget.TabHost": "tab",
    "android.widget.Spinner": "dropdown",
    "android.widget.ProgressBar": "progress",
    "android.widget.Toolbar": "toolbar",
    "androidx.appcompat.widget.Toolbar": "toolbar",
}


def parse_bounds(bounds_str: str) -> list[int]:
    """Parse uiautomator bounds string '[x1,y1][x2,y2]' into [x1, y1, x2, y2]."""
    bounds_str = bounds_str.strip()
    if not bounds_str:
        return [0, 0, 0, 0]
    # Format: [0,0][1080,2280]
    parts = bounds_str.strip("[]").split("][")
    if len(parts) != 2:
        return [0, 0, 0, 0]
    try:
        x1, y1 = map(int, parts[0].split(","))
        x2, y2 = map(int, parts[1].split(","))
        return [x1, y1, x2, y2]
    except (ValueError, IndexError):
        return [0, 0, 0, 0]


def infer_component_type(class_name: str) -> str:
    """Map Android class name to semantic component type."""
    return _CLASS_MAPPING.get(class_name, "unknown")


def calculate_fill_ratio(
    element_bounds: list[int], children: list[dict[str, Any]]
) -> float:
    """Calculate how much of the element's area is covered by its children.

    fill_ratio = total_child_area / element_area
    A low fill_ratio (<0.5) means the container should be transparent.
    """
    ex1, ey1, ex2, ey2 = element_bounds
    elem_area = (ex2 - ex1) * (ey2 - ey1)
    if elem_area <= 0:
        return 1.0

    total_child_area = 0
    for child in children:
        cb = child.get("bounds_device", [0, 0, 0, 0])
        cx1, cy1, cx2, cy2 = cb
        child_area = max(0, cx2 - cx1) * max(0, cy2 - cy1)
        total_child_area += child_area

    return round(min(1.0, total_child_area / elem_area), 3) if children else 0.0


def compute_visual_bounds(
    bounds_device: list[int], parent_bounds: list[int] | None
) -> list[int]:
    """Compute bounds relative to parent (for nested layout positioning)."""
    if parent_bounds is None:
        return bounds_device
    return [
        bounds_device[0] - parent_bounds[0],
        bounds_device[1] - parent_bounds[1],
        bounds_device[2] - parent_bounds[0],
        bounds_device[3] - parent_bounds[1],
    ]


def build_node(
    elem: ET.Element,
    parent_bounds: list[int] | None = None,
) -> dict[str, Any]:
    """Recursively build a skeleton node from an XML element."""
    bounds_device = parse_bounds(elem.get("bounds", "[0,0][0,0]"))
    visual_bounds = compute_visual_bounds(bounds_device, parent_bounds)

    children: list[dict[str, Any]] = []
    # uiautomator nests nodes inside <node> elements
    for child in elem.findall("node"):
        children.append(build_node(child, bounds_device))

    fill_ratio = calculate_fill_ratio(bounds_device, children)
    class_name = elem.get("class", "")

    node: dict[str, Any] = {
        "class": class_name,
        "component_type": infer_component_type(class_name),
        "bounds_device": bounds_device,
        "visual_bounds": visual_bounds,
        "resource_id": elem.get("resource-id", ""),
        "text": elem.get("text", ""),
        "content_desc": elem.get("content-desc", ""),
        "clickable": elem.get("clickable", "false") == "true",
        "enabled": elem.get("enabled", "true") == "true",
        "state": "on" if elem.get("checked", "false") == "true" else "off",
        "fill_ratio": fill_ratio,
        "children": children,
    }
    return node


def parse_ui_tree(xml_path: str) -> dict[str, Any]:
    """Parse uiautomator dump XML into skeleton.json tree.

    Args:
        xml_path: Path to ui_tree.xml from `adb shell uiautomator dump`.

    Returns:
        Skeleton dict with screen dimensions and node tree.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # The root <hierarchy> element contains one <node> child
    root_node = root.find("node")
    if root_node is None:
        root_node = root  # fallback: some dumps use node as root

    skeleton_tree = build_node(root_node, parent_bounds=None)

    # Extract screen dimensions from root bounds
    screen_bounds = parse_bounds(root_node.get("bounds", "[0,0][0,0]"))
    width = screen_bounds[2] - screen_bounds[0]
    height = screen_bounds[3] - screen_bounds[1]

    return {
        "screen": {"width": width, "height": height},
        "root": skeleton_tree,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse uiautomator XML to skeleton.json")
    parser.add_argument("xml_path", help="Path to ui_tree.xml")
    parser.add_argument("--output", "-o", default=None, help="Output JSON path (default: stdout)")
    args = parser.parse_args()

    xml_file = Path(args.xml_path)
    if not xml_file.exists():
        print(f"Error: {xml_file} not found", file=sys.stderr)
        return 1

    skeleton = parse_ui_tree(str(xml_file))
    output_json = json.dumps(skeleton, indent=2, ensure_ascii=False)

    if args.output:
        Path(args.output).write_text(output_json, encoding="utf-8")
        print(f"Wrote skeleton to {args.output}", file=sys.stderr)
    else:
        print(output_json)

    return 0


if __name__ == "__main__":
    sys.exit(main())
