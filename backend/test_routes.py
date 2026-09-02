"""Test backend routes respond correctly."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("OPENAI_API_KEY", "test-key-for-import-check")

from main import app
from fastapi.testclient import TestClient

client = TestClient(app)

routes = [
    ("GET", "/"),
    ("GET", "/capabilities"),
    ("GET", "/metrics"),
    ("GET", "/design-systems"),
    ("GET", "/custom-keys"),
]

results = {}
for method, path in routes:
    try:
        if method == "GET":
            resp = client.get(path)
        else:
            resp = client.post(path)
        results[path] = {
            "method": method,
            "status": resp.status_code,
            "ok": resp.status_code < 500,
        }
    except Exception as e:
        results[path] = {"method": method, "status": "error", "ok": False, "error": str(e)}

# Also test /adb/devices (fork-specific route)
try:
    resp = client.get("/adb/devices")
    results["/adb/devices"] = {"method": "GET", "status": resp.status_code, "ok": resp.status_code < 500}
except Exception as e:
    results["/adb/devices"] = {"method": "GET", "status": "error", "ok": False, "error": str(e)}

# Test /metrics returns prometheus format
try:
    resp = client.get("/metrics")
    metrics_ok = "s2c_" in resp.text or "screenshot_to_code" in resp.text.lower() or resp.status_code == 200
    results["/metrics"] = {
        "method": "GET",
        "status": resp.status_code,
        "ok": metrics_ok,
        "content_type": resp.headers.get("content-type", ""),
        "body_preview": resp.text[:200] if resp.text else "",
    }
except Exception as e:
    pass

print(json.dumps(results, indent=2, ensure_ascii=False))
all_ok = all(r["ok"] for r in results.values())
print(f"\n=== Backend routes: {'ALL OK' if all_ok else 'HAS ERRORS'} ===")
