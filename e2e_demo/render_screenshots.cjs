const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const DEMO_DIR = 'C:/Code/s2c-work/e2e_demo';
const SHOTS_DIR = path.join(DEMO_DIR, 'screenshots');

if (!fs.existsSync(SHOTS_DIR)) fs.mkdirSync(SHOTS_DIR, { recursive: true });

// Code highlight HTML template for non-HTML stacks
function codeToHtml(code, title, lang) {
    const escaped = code
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    return `<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>${title}</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #1e1e1e; font-family: 'Consolas', 'Monaco', monospace; padding: 24px; }
.header { color: #569cd6; font-size: 18px; margin-bottom: 16px; font-weight: bold; }
.code-block { color: #d4d4d4; font-size: 13px; line-height: 1.6; white-space: pre-wrap; word-wrap: break-word; }
.tag { color: #569cd6; }
.attr { color: #9cdcfe; }
.string { color: #ce9178; }
.comment { color: #6a9955; }
.keyword { color: #c586c0; }
.label { color: #7L: #b5cea8; }
</style></head>
<body>
<div class="header">${title}</div>
<div class="code-block">${escaped}</div>
</body></html>`;
}

// WPF XAML -> HTML visual preview (approximate rendering)
function wpfToHtml(xamlCode) {
    return `<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>WPF Settings Preview</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #f3f3f3; display: flex; justify-content: center; padding: 40px; }
.window {
    width: 400px; background: white; border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15); overflow: hidden;
    font-family: 'Segoe UI', sans-serif; font-size: 14px;
}
.titlebar { background: #0078D7; color: white; padding: 8px 16px; font-size: 12px; }
.content { padding: 24px; }
.title { font-size: 24px; font-weight: bold; margin-bottom: 20px; color: #1a1a1a; }
.row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.row label { flex: 1; }
.checkbox { width: 20px; height: 20px; border: 2px solid #0078D7; border-radius: 4px; }
.checkbox.checked { background: #0078D7; position: relative; }
.checkbox.checked::after { content: '\u2713'; color: white; font-size: 14px; position: absolute; top: -2px; left: 2px; }
.label-text { margin-bottom: 8px; color: #666; }
select { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; margin-bottom: 24px; font-size: 14px; }
button { width: 100%; padding: 10px; background: #0078D7; color: white; border: none; border-radius: 4px; font-size: 14px; cursor: pointer; }
</style></head>
<body>
<div class="window">
  <div class="titlebar">Settings</div>
  <div class="content">
    <div class="title">Settings</div>
    <div class="row"><label>Enable notifications</label><div class="checkbox checked"></div></div>
    <div class="row"><label>Dark theme</label><div class="checkbox"></div></div>
    <div class="label-text">Language</div>
    <select><option>English</option><option>简体中文</option><option>日本語</option></select>
    <button>Save</button>
  </div>
</div>
</body></html>`;
}

// A2UI -> visual preview
function a2uiToHtml(jsonlCode) {
    const lines = jsonlCode.trim().split('\n').filter(l => l.trim());
    let objects = {};
    for (const line of lines) {
        try { const obj = JSON.parse(line); objects[obj.id] = obj; } catch(e) {}
    }
    // Find root (first object's children)
    const rootId = lines[0] ? JSON.parse(lines[0]).id : null;
    function render(id) {
        const obj = objects[id];
        if (!obj) return '';
        const type = obj.type;
        const props = obj.props || {};
        if (type === 'text') {
            return `<div style="margin-bottom:8px;font-size:${props.size||14}px;font-weight:${props.bold?'bold':'normal'}">${props.text||''}</div>`;
        }
        if (type === 'button') {
            return `<button style="width:100%;padding:10px;background:#0078D7;color:white;border:none;border-radius:4px;margin-top:16px">${props.text||'Button'}</button>`;
        }
        if (type === 'switch') {
            return `<div style="width:44px;height:22px;background:${props.checked?'#0078D7':'#ccc'};border-radius:22px;position:relative"><div style="position:absolute;width:18px;height:18px;background:white;border-radius:50%;top:2px;${props.checked?'left:24px':'left:2px'};transition:0.2s"></div></div>`;
        }
        if (type === 'dropdown') {
            const opts = (props.options||[]).map((o,i) => `<option ${i===props.selectedIndex?'selected':''}>${o}</option>`).join('');
            return `<select style="width:100%;padding:8px;border:1px solid #ddd;border-radius:4px;margin-bottom:8px">${opts}</select>`;
        }
        if (type === 'column') {
            return `<div style="display:flex;flex-direction:column">${(obj.children||[]).map(render).join('')}</div>`;
        }
        if (type === 'row') {
            return `<div style="display:flex;flex-direction:row;justify-content:space-between;align-items:center;margin-bottom:12px">${(obj.children||[]).map(render).join('')}</div>`;
        }
        return `<div>${type}</div>`;
    }
    return `<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>A2UI Preview</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#f3f3f3; display:flex; justify-content:center; padding:40px; font-family:'Segoe UI',sans-serif; }
.preview { width:400px; background:white; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.1); padding:24px; }
</style></head>
<body><div class="preview">${render(rootId)}</div></body></html>`;
}

(async () => {
    const browser = await chromium.launch();
    const page = await browser.newPage({ viewport: { width: 500, height: 600 } });

    const tasks = [
        { name: 'windows_html', file: 'llm_windows_html.html', type: 'direct' },
        { name: 'windows_wpf', file: null, type: 'wpf_preview' },
        { name: 'a2ui', file: 'llm_a2ui.jsonl', type: 'a2ui' },
        { name: 'android_xml', file: 'llm_android_xml.xml', type: 'code', lang: 'XML' },
        { name: 'android_compose', file: 'llm_android_compose.kt', type: 'code', lang: 'Kotlin' },
        { name: 'qt_qml', file: 'llm_qt_qml.qml', type: 'code', lang: 'QML' },
    ];

    for (const task of tasks) {
        const outPath = path.join(SHOTS_DIR, `${task.name}.png`);
        let html;

        if (task.type === 'direct') {
            html = fs.readFileSync(path.join(DEMO_DIR, task.file), 'utf-8');
        } else if (task.type === 'wpf_preview') {
            html = wpfToHtml();
        } else if (task.type === 'a2ui') {
            const code = fs.readFileSync(path.join(DEMO_DIR, task.file), 'utf-8');
            html = a2uiToHtml(code);
        } else if (task.type === 'code') {
            const code = fs.readFileSync(path.join(DEMO_DIR, task.file), 'utf-8');
            html = codeToHtml(code, `${task.name} (${task.lang})`, task.lang);
        }

        await page.setContent(html, { waitUntil: 'networkidle' });
        await page.screenshot({ path: outPath, fullPage: true });
        console.log(`  [OK] ${task.name}.png`);
    }

    await browser.close();
    console.log(`\nAll screenshots saved to ${SHOTS_DIR}`);
})();
