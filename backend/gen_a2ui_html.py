import sys, os
sys.path.insert(0, r'C:\Users\georgeslark\.workbuddy\binaries\python\envs\default\Lib\site-packages')
os.environ['PYTHONIOENCODING'] = 'utf-8'

import json, time, httpx
from pathlib import Path

API_KEY = os.environ.get("ARK_API_KEY", "REDACTED")
BASE_URL = 'https://ark.cn-beijing.volces.com/api/v3'
MODEL = 'doubao-seed-2-1-turbo-260628'
OUTPUT_DIR = Path(r'C:\Code\screenshot-to-code\e2e_demo\run_20260901')
UI_DESC_PATH = OUTPUT_DIR / 'ui_description.json'

with open(UI_DESC_PATH, 'r', encoding='utf-8') as f:
    ui_desc = f.read()

client = httpx.Client(timeout=300.0)
headers = {'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'}

a2ui_prompt = '根据以下 UI 描述，生成 A2UI JSONL 格式代码。\n\nUI 描述:\n' + ui_desc + '\n\nA2UI 格式: JSONL，每行一个 JSON 对象，合法类型: button/card/column/container/image/input/list/row/stack/text\n页面: 设置-声音与显示，左侧侧边栏(搜索+导航列表)，右侧设置项(扬声器开关/音量滑块/提示音量滑块/按键音开关/麦克风开关/亮度滑块)\n直接输出 JSONL，不要 markdown fence。'

print('Generating A2UI...')
body = {'model': MODEL, 'messages': [{'role': 'user', 'content': a2ui_prompt}], 'max_tokens': 4000, 'temperature': 0.3, 'stream': False}
t0 = time.time()
resp = client.post(f'{BASE_URL}/chat/completions', headers=headers, json=body, timeout=300.0)
elapsed = time.time() - t0
print(f'Status: {resp.status_code} ({elapsed:.1f}s)')
if resp.status_code == 200:
    data = resp.json()
    content = data['choices'][0]['message']['content']
    usage = data.get('usage', {})
    print(f'Tokens: in={usage.get("prompt_tokens",0)} out={usage.get("completion_tokens",0)}')
    if content.strip().startswith('```'):
        lines = content.strip().split('\n')[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        content = '\n'.join(lines)
    with open(OUTPUT_DIR / 'llm_a2ui.jsonl', 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'A2UI -> llm_a2ui.jsonl {len(content)} chars OK')
else:
    print(f'ERROR: {resp.text[:500]}')

html_prompt = '根据以下 UI 描述，生成完整自包含 HTML 文件。\n\nUI 描述:\n' + ui_desc + '\n\n要求: DOCTYPE+html+head+body, 内联CSS, 左侧侧边栏+右侧设置内容, 圆角卡片布局, 配色#f5f5f5/#1677ff/#212121\n直接输出 HTML，不要 markdown fence。'

print('\nGenerating HTML...')
body2 = {'model': MODEL, 'messages': [{'role': 'user', 'content': html_prompt}], 'max_tokens': 6000, 'temperature': 0.3, 'stream': False}
t0 = time.time()
resp2 = client.post(f'{BASE_URL}/chat/completions', headers=headers, json=body2, timeout=300.0)
elapsed2 = time.time() - t0
print(f'Status: {resp2.status_code} ({elapsed2:.1f}s)')
if resp2.status_code == 200:
    data2 = resp2.json()
    content2 = data2['choices'][0]['message']['content']
    usage2 = data2.get('usage', {})
    print(f'Tokens: in={usage2.get("prompt_tokens",0)} out={usage2.get("completion_tokens",0)}')
    if content2.strip().startswith('```'):
        lines2 = content2.strip().split('\n')[1:]
        if lines2 and lines2[-1].strip() == '```':
            lines2 = lines2[:-1]
        content2 = '\n'.join(lines2)
    with open(OUTPUT_DIR / 'llm_windows_html.html', 'w', encoding='utf-8') as f:
        f.write(content2)
    print(f'HTML -> llm_windows_html.html {len(content2)} chars OK')
else:
    print(f'ERROR: {resp2.text[:500]}')

client.close()
