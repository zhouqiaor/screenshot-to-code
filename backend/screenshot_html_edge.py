"""Screenshot HTML files using Edge headless mode."""
import subprocess
import time
from pathlib import Path

BASE = Path(__file__).parent.parent

EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"

files = {
    "direct": BASE / "e2e_demo" / "run_20260901" / "kotlin_pipeline" / "html_preview.html",
    "ws": BASE / "e2e_demo" / "run_20260901" / "ws_output.html",
}

out = {
    "direct": BASE / "e2e_demo" / "run_20260901" / "screenshot_direct.png",
    "ws": BASE / "e2e_demo" / "run_20260901" / "screenshot_ws.png",
}

for key, html_path in files.items():
    out_path = out[key]
    # Edge headless screenshot
    cmd = [
        EDGE,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--screenshot=" + str(out_path).replace("\\", "/"),
        "--window-size=800,1600",
        "--virtual-time-budget=10000",
        "file:///" + html_path.as_posix(),
    ]
    print(f"Screenshot {key}: {html_path.name} -> {out_path.name}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if out_path.exists():
        print(f"  OK: {out_path.stat().st_size:,} bytes")
    else:
        print(f"  FAILED: {result.stderr[:200]}")

print("Done")
