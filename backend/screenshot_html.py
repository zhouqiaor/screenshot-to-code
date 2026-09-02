"""Screenshot two HTML files side by side using Playwright."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = Path(__file__).parent.parent

files = {
    "direct": BASE / "e2e_demo" / "run_20260901" / "kotlin_pipeline" / "html_preview.html",
    "ws": BASE / "e2e_demo" / "run_20260901" / "ws_output.html",
}

out = {
    "direct": BASE / "e2e_demo" / "run_20260901" / "screenshot_direct.png",
    "ws": BASE / "e2e_demo" / "run_20260901" / "screenshot_ws.png",
}

with sync_playwright() as p:
    browser = p.chromium.launch()
    for key, html_path in files.items():
        page = browser.new_page(viewport={"width": 800, "height": 1200})
        page.goto(f"file:///{html_path.as_posix()}")
        page.wait_for_load_state("networkidle")
        # Take full page screenshot
        page.screenshot(path=str(out[key]), full_page=True)
        print(f"{key}: {out[key]} ({out[key].stat().st_size:,} bytes)")
        page.close()
    browser.close()

print("Done")
