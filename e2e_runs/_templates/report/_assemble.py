# -*- coding: utf-8 -*-
import os
BASE = os.path.dirname(os.path.abspath(__file__))

html = open(os.path.join(BASE, 'verification_merged.html'), encoding='utf-8').read()
device = open(os.path.join(BASE, '_device_imgs.html'), encoding='utf-8').read()
render = open(os.path.join(BASE, '_render_imgs.html'), encoding='utf-8').read()

html = html.replace('__DEVICE__', device).replace('__RENDER__', render)

out = os.path.join(BASE, 'e2e_verification_report_merged.html')
with open(out, 'w', encoding='utf-8') as f:
    f.write(html)
print('OK', len(html) // 1024, 'KB ->', out)
