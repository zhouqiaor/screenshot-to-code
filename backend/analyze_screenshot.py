"""Analyze screenshot for color and content analysis."""
import collections
import os
from PIL import Image

base = os.path.join(os.path.dirname(__file__), "..", "e2e_demo", "screenshots", "run_20260901")
src = os.path.join(base, "source_screenshot.png")

img = Image.open(src)
print(f"Image: {img.size} {img.mode}")

# Color analysis
small = img.resize((100, 56))
pixels = list(small.convert("RGB").getdata())
counter = collections.Counter(pixels)
print("Top 10 colors (RGB):")
for color, count in counter.most_common(10):
    print(f"  RGB{color}: {count} ({count*100//5600}%)")

# Crop regions for analysis
w, h = img.size
regions = {
    "top": (0, 0, w, h // 4),
    "middle": (0, h // 4, w, 3 * h // 4),
    "bottom": (0, 3 * h // 4, w, h),
}
for name, box in regions.items():
    crop = img.crop(box)
    crop_path = os.path.join(base, f"source_{name}.png")
    crop.save(crop_path)
    print(f"Saved {name}: {crop.size} -> {crop_path}")

# Check if it's a dark or light theme
r_avg = sum(p[0] for p in pixels) // len(pixels)
g_avg = sum(p[1] for p in pixels) // len(pixels)
b_avg = sum(p[2] for p in pixels) // len(pixels)
luminance = (0.299 * r_avg + 0.587 * g_avg + 0.114 * b_avg)
print(f"\nAverage luminance: {luminance:.1f} ({'DARK' if luminance < 128 else 'LIGHT'} theme)")
print(f"Average RGB: ({r_avg}, {g_avg}, {b_avg})")
