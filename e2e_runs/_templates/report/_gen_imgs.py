# -*- coding: utf-8 -*-
from PIL import Image
import base64, io, os

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)

def b64(path, maxw):
    im = Image.open(path).convert('RGB')
    if im.width > maxw:
        im = im.resize((maxw, int(im.height * maxw / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=82)
    return base64.b64encode(buf.getvalue()).decode()

def img(path, maxw, cap):
    if not os.path.exists(path):
        return ''
    return '<div class="card"><div class="cap">' + cap + '</div><img src="data:image/jpeg;base64,' + b64(path, maxw) + '" /></div>'

R = lambda *a: os.path.join(ROOT, *a)

device = ''.join([
    img(R('e2e_runs/_capture_inbox/screenshot.png'), 900, '原始截图 (source) 3840x2160'),
    img(R('e2e_runs/20260902T160242_doubao-seed-2-1-turbo-260628/screenshots/device_xml_stack.png'), 900, 'XML 真机 (device) 3840x2160'),
    img(R('e2e_runs/screenshots_device_compose_now.png'), 900, 'Kotlin Compose 真机 (device) 3840x2160'),
])

render = ''.join([
    img(R('e2e_runs/20260901_doubao-seed-2-1-turbo-260628/renders/unified_kt_screenshot.png'), 640, 'Compose 渲染 960x720'),
    img(R('e2e_runs/20260901_doubao-seed-2-1-turbo-260628/renders/unified_xml_screenshot.png'), 640, 'XML 渲染 960x720'),
    img(R('e2e_runs/20260901_doubao-seed-2-1-turbo-260628/renders/render_html_screenshot.png'), 640, 'HTML 渲染 960x720'),
    img(R('e2e_runs/20260901_doubao-seed-2-1-turbo-260628/renders/render_a2ui_screenshot.png'), 640, 'A2UI 渲染 960x720'),
    img(R('e2e_runs/20260901_doubao-seed-2-1-turbo-260628/renders/render_qml_screenshot.png'), 640, 'QML 渲染 2560x1440'),
])

with open(os.path.join(BASE, '_device_imgs.html'), 'w', encoding='utf-8') as f:
    f.write(device)
with open(os.path.join(BASE, '_render_imgs.html'), 'w', encoding='utf-8') as f:
    f.write(render)
print('OK device=%d render=%d' % (len(device), len(render)))
