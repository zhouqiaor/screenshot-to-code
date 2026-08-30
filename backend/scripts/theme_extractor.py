"""Extract design tokens (theme.json) from an ADB screenshot using pixel sampling.

Uses two validated methods:
- Dark pixel scan (V7): For text colors — scan bounds for pixels with luminance < 200,
  sort by darkness, take darkest 10% average.
- Area average (V4): For background colors — average all pixels in the region.

Usage:
    python -m scripts.theme_extractor <screenshot.png> <skeleton.json> [--output theme.json]
    python backend/scripts/theme_extractor.py screenshot.png skeleton.json -o theme.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image


def _clamp(v: int) -> int:
    return max(0, min(255, v))


def luminance(rgb: tuple[int, ...]) -> float:
    """Calculate perceived luminance of an RGB pixel (Rec. 601 weights)."""
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{_clamp(r):02X}{_clamp(g):02X}{_clamp(b):02X}"


def extract_text_color(
    image: Image.Image, bounds: list[int]
) -> str | None:
    """Dark pixel scan method (V7 validated): take darkest 10% pixels' average.

    Scans the region for pixels with luminance < 200 (dark = text strokes),
    sorts by darkness, takes the darkest 10% and averages them. This avoids
    anti-aliased edges and background bleed, yielding the true text color.
    """
    x1, y1, x2, y2 = bounds
    if x2 <= x1 or y2 <= y1:
        return None

    region = image.crop((x1, y1, x2, y2))
    _fn = getattr(region, "get_flattened_data", region.getdata)
    pixels = list(_fn())

    # Handle RGBA tuples (discard alpha)
    rgb_pixels: list[tuple[int, int, int]] = []
    for p in pixels:
        if len(p) >= 3:
            rgb_pixels.append((p[0], p[1], p[2]))

    dark_pixels = [p for p in rgb_pixels if luminance(p) < 200]
    if not dark_pixels:
        return None

    dark_pixels.sort(key=luminance)
    top_count = max(1, len(dark_pixels) // 10)
    top_10 = dark_pixels[:top_count]

    avg_r = sum(p[0] for p in top_10) // len(top_10)
    avg_g = sum(p[1] for p in top_10) // len(top_10)
    avg_b = sum(p[2] for p in top_10) // len(top_10)

    return _rgb_to_hex(avg_r, avg_g, avg_b)


def extract_bg_color(image: Image.Image, bounds: list[int]) -> str:
    """Area average method (V4 validated): safe for background colors.

    Averages all pixel values in the region. Works well for flat or
    near-flat backgrounds. For textured backgrounds, use a small corner sample.
    """
    x1, y1, x2, y2 = bounds
    if x2 <= x1 or y2 <= y1:
        # Fall back to a tiny corner of the image
        x1, y1, x2, y2 = 0, 0, 10, 10

    region = image.crop((x1, y1, x2, y2))
    _fn = getattr(region, "get_flattened_data", region.getdata)
    pixels = list(_fn())
    if not pixels:
        return "#FFFFFF"

    # Handle RGBA tuples (discard alpha)
    r_sum = g_sum = b_sum = 0
    for p in pixels:
        if len(p) < 3:
            continue
        r_sum += p[0]
        g_sum += p[1]
        b_sum += p[2]

    count = len(pixels)
    return _rgb_to_hex(r_sum // count, g_sum // count, b_sum // count)


def _extract_corner_bg(image: Image.Image, sample_size: int = 20) -> str:
    """Sample background from four screen corners (most likely background area)."""
    w, h = image.size
    corners = [
        (0, 0, sample_size, sample_size),               # top-left
        (w - sample_size, 0, w, sample_size),           # top-right
        (0, h - sample_size, sample_size, h),           # bottom-left
        (w - sample_size, h - sample_size, w, h),       # bottom-right
    ]
    colors = [extract_bg_color(image, c) for c in corners]
    # Return the most common color (majority vote)
    counter = Counter(colors)
    return counter.most_common(1)[0][0]


def _collect_text_nodes(
    node: dict[str, Any], text_nodes: list[dict[str, Any]]
) -> None:
    """Recursively collect nodes that have text content (for text color sampling)."""
    if node.get("text"):
        text_nodes.append(node)
    for child in node.get("children", []):
        _collect_text_nodes(child, text_nodes)


def _collect_switch_nodes(
    node: dict[str, Any], switch_nodes: list[dict[str, Any]]
) -> None:
    """Recursively collect switch/seekbar nodes for accent color sampling."""
    ct = node.get("component_type", "")
    if ct in ("switch", "seekbar"):
        switch_nodes.append(node)
    for child in node.get("children", []):
        _collect_switch_nodes(child, switch_nodes)


def extract_theme(image_path: str, skeleton: dict[str, Any]) -> dict[str, Any]:
    """Extract theme.json from screenshot + skeleton.json.

    Args:
        image_path: Path to screenshot.png.
        skeleton: Parsed skeleton.json (from skeleton_parser.parse_ui_tree).

    Returns:
        theme.json dict with colors, spacing, typography, borderRadius.
    """
    image = Image.open(image_path).convert("RGB")
    root = skeleton.get("root", {})

    # Background: sample screen corners
    bg_hex = _extract_corner_bg(image)

    # Text colors: collect text nodes, sample their bounds
    text_nodes: list[dict[str, Any]] = []
    _collect_text_nodes(root, text_nodes)

    text_colors: list[dict[str, Any]] = []
    for node in text_nodes:
        bounds = node.get("bounds_device", [0, 0, 0, 0])
        text_hex = extract_text_color(image, bounds)
        if text_hex:
            text_colors.append({
                "hex": text_hex,
                "m3_role": "onSurface",
                "source": node.get("text", "")[:50],
                "method": "dark_pixel_scan",
            })

    # Accent colors: collect switch/seekbar nodes
    switch_nodes: list[dict[str, Any]] = []
    _collect_switch_nodes(root, switch_nodes)

    accent_colors: list[dict[str, Any]] = []
    for node in switch_nodes:
        bounds = node.get("bounds_device", [0, 0, 0, 0])
        # For switches, sample the track area (center horizontal strip)
        x1, y1, x2, y2 = bounds
        if x2 > x1 and y2 > y1:
            mid_y = (y1 + y2) // 2
            track_bounds = [x1, max(y1, mid_y - 3), x2, min(y2, mid_y + 3)]
            accent_hex = extract_bg_color(image, track_bounds)
            accent_colors.append({
                "hex": accent_hex,
                "m3_role": "primary",
                "component": node.get("component_type", ""),
                "method": "area_average",
            })

    # Typography: estimate font size from text node heights
    typography: dict[str, Any] = {}
    if text_nodes:
        heights = []
        for node in text_nodes:
            b = node.get("bounds_device", [0, 0, 0, 0])
            h = b[3] - b[1]
            if h > 0:
                heights.append(h)
        if heights:
            avg_height = sum(heights) / len(heights)
            typography = {
                "body_font_size_dp": round(avg_height * 0.8),
                "label_font_size_dp": round(avg_height * 0.7),
                "method": "estimated_from_text_bounds",
            }

    # Border radius: scan switch/seekbar bounds for rounded corners
    border_radius: dict[str, Any] = {}
    if switch_nodes:
        # Switches typically have border-radius = half their height
        sw = switch_nodes[0]
        b = sw.get("bounds_device", [0, 0, 0, 0])
        sw_height = b[3] - b[1]
        if sw_height > 0:
            border_radius = {
                "switch_radius_dp": round(sw_height / 2),
                "method": "half_of_switch_height",
            }

    return {
        "colors": {
            "background": {
                "hex": bg_hex,
                "m3_role": "surface",
                "method": "corner_sample",
            },
            "text_colors": text_colors,
            "accent_colors": accent_colors,
        },
        "typography": typography,
        "borderRadius": border_radius,
        "spacing": {},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract theme.json from screenshot + skeleton")
    parser.add_argument("screenshot", help="Path to screenshot.png")
    parser.add_argument("skeleton", help="Path to skeleton.json")
    parser.add_argument("--output", "-o", default=None, help="Output JSON path (default: stdout)")
    args = parser.parse_args()

    screenshot_path = Path(args.screenshot)
    skeleton_path = Path(args.skeleton)
    if not screenshot_path.exists():
        print(f"Error: {screenshot_path} not found", file=sys.stderr)
        return 1
    if not skeleton_path.exists():
        print(f"Error: {skeleton_path} not found", file=sys.stderr)
        return 1

    skeleton = json.loads(skeleton_path.read_text(encoding="utf-8"))
    theme = extract_theme(str(screenshot_path), skeleton)
    output_json = json.dumps(theme, indent=2, ensure_ascii=False)

    if args.output:
        Path(args.output).write_text(output_json, encoding="utf-8")
        print(f"Wrote theme to {args.output}", file=sys.stderr)
    else:
        print(output_json)

    return 0


if __name__ == "__main__":
    sys.exit(main())
