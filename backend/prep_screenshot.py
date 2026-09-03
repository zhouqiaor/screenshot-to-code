"""Prepare screenshot for LLM input — resize and base64 encode."""
import base64
import os
from PIL import Image

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
base = os.path.join(BASE_DIR, "e2e_demo", "screenshots", "run_20260901")
src = os.path.join(base, "source_screenshot.png")

img = Image.open(src)
print(f"Original: {img.size}, Mode: {img.mode}")

# Resize to max 768 wide (vision models handle this well, much smaller base64)
ratio = 768 / img.size[0]
new_h = int(img.size[1] * ratio)
img_resized = img.resize((768, new_h), Image.LANCZOS)

# Convert RGBA to RGB (smaller)
if img_resized.mode == "RGBA":
    bg = Image.new("RGB", img_resized.size, (255, 255, 255))
    bg.paste(img_resized, mask=img_resized.split()[3] if img_resized.mode == "RGBA" else None)
    img_resized = bg

# Save as JPEG for smaller size
jpeg_path = os.path.join(base, "source_screenshot_768.jpg")
img_resized.save(jpeg_path, "JPEG", quality=85)
print(f"Resized JPEG: {img_resized.size}")

jpeg_size = os.path.getsize(jpeg_path)
print(f"JPEG size: {jpeg_size} bytes ({jpeg_size/1024:.0f} KB)")

# Base64 encode
with open(jpeg_path, "rb") as f:
    b64 = base64.b64encode(f.read()).decode()
print(f"Base64 length: {len(b64)} chars ({len(b64)/1024:.0f} KB)")

with open(os.path.join(base, "source_b64.txt"), "w") as f:
    f.write(b64)
print(f"Saved base64 to source_b64.txt")
print("Done")
