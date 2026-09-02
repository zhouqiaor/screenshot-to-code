"""Launch qmlscene and capture screenshot using PIL ImageGrab."""
import sys
sys.path.insert(0, r'C:\Users\georgeslark\.workbuddy\binaries\python\envs\default\Lib\site-packages')

import subprocess
import time
import os
from PIL import ImageGrab

os.environ['QML2_IMPORT_PATH'] = r'C:\Programs\Qt\6.11.0\mingw_64\qml'

qml_file = r'C:\Code\screenshot-to-code\e2e_demo\run_20260901\llm_qt_qml.qml'
output_png = r'C:\Code\screenshot-to-code\e2e_demo\run_20260901\render_qml_screenshot.png'

print("Launching qmlscene...")
proc = subprocess.Popen(
    [r'C:\Programs\Qt\6.11.0\mingw_64\bin\qmlscene.exe',
     '--no-version-detection', '--maximized', qml_file],
    env={**os.environ},
)

print(f"PID={proc.pid}, waiting 5s for window...")
time.sleep(5)

print("Capturing screenshot...")
img = ImageGrab.grab()
img.save(output_png, 'PNG')
print(f"Saved: {output_png} ({len(open(output_png, 'rb').read())} bytes)")

proc.terminate()
proc.wait()
print("qmlscene terminated")
