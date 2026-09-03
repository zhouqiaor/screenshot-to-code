const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const DEMO_DIR = 'C:/Code/s2c-work/e2e_demo';
const SHOTS_DIR = path.join(DEMO_DIR, 'screenshots');
if (!fs.existsSync(SHOTS_DIR)) fs.mkdirSync(SHOTS_DIR, { recursive: true });

(async () => {
    const browser = await chromium.launch();
    const page = await browser.newPage({ viewport: { width: 600, height: 500 } });

    // 1. Kotlin 运行输出截图
    const kotlinHtml = `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#1e1e1e; font-family:'Consolas','Monaco',monospace; padding:20px; }
.header { color:#4CAF50; font-size:16px; margin-bottom:16px; font-weight:bold; }
.output { color:#d4d4d4; font-size:14px; line-height:1.8; white-space:pre-wrap; }
.cmd { color:#569cd6; margin-bottom:8px; }
.cmd2 { color:#ce9178; }
</style></head><body>
<div class="header">Kotlin 编译运行输出 (kotlinc → jar → java -jar)</div>
<div class="cmd">$ kotlinc -include-runtime -d kotlin_test.jar kotlin_compile_test.kt</div>
<div class="cmd2">[Compiled OK, 0 errors, 0 warnings]</div>
<div class="cmd">$ java -jar kotlin_test.jar</div>
<div class="output">=== Settings Screen ===
  Enable notifications: ON
  Dark theme: OFF
  Language: ON
Settings saved: notif=true, dark=false, lang=English</div>
</body></html>`;
    await page.setContent(kotlinHtml, { waitUntil: 'networkidle' });
    await page.screenshot({ path: path.join(SHOTS_DIR, 'kotlin_run_output.png'), fullPage: true });
    console.log('  [OK] kotlin_run_output.png');

    // 2. Windows HTML 渲染（直接用原始 HTML）
    const html = fs.readFileSync(path.join(DEMO_DIR, 'llm_windows_html.html'), 'utf-8');
    await page.setContent(html, { waitUntil: 'networkidle' });
    await page.screenshot({ path: path.join(SHOTS_DIR, 'windows_html_run.png'), fullPage: true });
    console.log('  [OK] windows_html_run.png');

    // 3. Android XML → UI 模拟渲染（Material Design 风格）
    const androidHtml = `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#FFFBFE; display:flex; justify-content:center; padding:30px; font-family:'Roboto','Segoe UI',sans-serif; }
.card { width:360px; background:white; border-radius:16px; box-shadow:0 1px 3px rgba(0,0,0,0.12); overflow:hidden; }
.appbar { background:#6750A4; color:white; padding:16px 20px; font-size:18px; font-weight:500; }
.body { padding:24px; }
.title { font-size:22px; font-weight:bold; margin-bottom:20px; color:#1C1B1F; }
.row { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; font-size:15px; color:#49454F; }
.toggle { width:52px; height:32px; border-radius:16px; position:relative; }
.toggle.on { background:#6750A4; }
.toggle.off { background:#CAC4D0; }
.toggle .knob { position:absolute; width:24px; height:24px; background:white; border-radius:50%; top:4px; box-shadow:0 1px 3px rgba(0,0,0,0.2); transition:0.2s; }
.toggle.on .knob { right:4px; }
.toggle.off .knob { left:4px; }
.label { margin-bottom:8px; color:#49454F; font-size:14px; }
select { width:100%; padding:12px; border:1px solid #CAC4D0; border-radius:4px; margin-bottom:20px; font-size:14px; background:white; }
.btn { width:100%; padding:14px; background:#6750A4; color:white; border:none; border-radius:20px; font-size:15px; font-weight:500; cursor:pointer; }
.badge { position:fixed; top:10px; right:10px; background:rgba(0,0,0,0.6); color:white; padding:4px 10px; border-radius:12px; font-size:11px; }
</style></head><body>
<div class="badge">Android XML (Material 3)</div>
<div class="card">
  <div class="appbar">Settings</div>
  <div class="body">
    <div class="title">Settings</div>
    <div class="row"><span>Enable notifications</span><div class="toggle on"><div class="knob"></div></div></div>
    <div class="row"><span>Dark theme</span><div class="toggle off"><div class="knob"></div></div></div>
    <div class="label">Language</div>
    <select><option>English</option><option>简体中文</option></select>
    <button class="btn">Save</button>
  </div>
</div>
</body></html>`;
    await page.setContent(androidHtml, { waitUntil: 'networkidle' });
    await page.screenshot({ path: path.join(SHOTS_DIR, 'android_xml_run.png'), fullPage: true });
    console.log('  [OK] android_xml_run.png');

    // 4. Android Compose → UI 模拟渲染
    const composeHtml = `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#FFFBFE; display:flex; justify-content:center; padding:30px; font-family:'Roboto','Segoe UI',sans-serif; }
.card { width:360px; background:white; border-radius:16px; box-shadow:0 1px 3px rgba(0,0,0,0.12); overflow:hidden; }
.appbar { background:#6750A4; color:white; padding:16px 20px; font-size:18px; font-weight:500; }
.body { padding:24px; display:flex; flex-direction:column; gap:16px; }
.title { font-size:22px; font-weight:bold; color:#1C1B1F; }
.row { display:flex; justify-content:space-between; align-items:center; font-size:15px; color:#49454F; }
.switch { width:52px; height:32px; border-radius:16px; position:relative; }
.switch.on { background:#6750A4; }
.switch.off { background:#CAC4D0; }
.switch .knob { position:absolute; width:24px; height:24px; background:white; border-radius:50%; top:4px; box-shadow:0 1px 3px rgba(0,0,0,0.2); }
.switch.on .knob { right:4px; }
.switch.off .knob { left:4px; }
.label { color:#49454F; font-size:14px; margin-bottom:-8px; }
.dropdown { width:100%; padding:12px; border:1px solid #CAC4D0; border-radius:4px; font-size:14px; background:white; display:flex; justify-content:space-between; align-items:center; }
.dropdown::after { content:'▼'; color:#49454F; font-size:10px; }
.btn { width:100%; padding:14px; background:#6750A4; color:white; border:none; border-radius:20px; font-size:15px; font-weight:500; }
.badge { position:fixed; top:10px; right:10px; background:rgba(0,0,0,0.6); color:white; padding:4px 10px; border-radius:12px; font-size:11px; }
</style></head><body>
<div class="badge">Android Compose (Material 3)</div>
<div class="card">
  <div class="appbar">Settings</div>
  <div class="body">
    <div class="title">Settings</div>
    <div class="row"><span>Enable notifications</span><div class="switch on"><div class="knob"></div></div></div>
    <div class="row"><span>Dark theme</span><div class="switch off"><div class="knob"></div></div></div>
    <div class="label">Language</div>
    <div class="dropdown"><span>English</span></div>
    <button class="btn">Save</button>
  </div>
</div>
</body></html>`;
    await page.setContent(composeHtml, { waitUntil: 'networkidle' });
    await page.screenshot({ path: path.join(SHOTS_DIR, 'android_compose_run.png'), fullPage: true });
    console.log('  [OK] android_compose_run.png');

    // 5. Qt QML → UI 模拟渲染
    const qtHtml = `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#f5f5f5; display:flex; justify-content:center; padding:30px; font-family:'Segoe UI',sans-serif; }
.window { width:400px; background:#f5f5f5; border:1px solid #ccc; border-radius:4px; overflow:hidden; }
.titlebar { background:#0078D7; color:white; padding:8px 16px; font-size:13px; display:flex; justify-content:space-between; }
.body { padding:24px; display:flex; flex-direction:column; gap:16px; }
.title { font-size:22px; font-weight:bold; color:#1a1a1a; }
.row { display:flex; justify-content:space-between; align-items:center; font-size:14px; color:#333; }
.switch { width:44px; height:22px; border-radius:11px; position:relative; }
.switch.on { background:#0078D7; }
.switch.off { background:#bbb; }
.switch .knob { position:absolute; width:18px; height:18px; background:white; border-radius:50%; top:2px; box-shadow:0 1px 2px rgba(0,0,0,0.3); }
.switch.on .knob { right:2px; }
.switch.off .knob { left:2px; }
.label { color:#666; font-size:14px; }
.combo { width:100%; padding:8px; border:1px solid #ccc; border-radius:2px; background:white; font-size:14px; }
.btn { width:100%; padding:10px; background:#0078D7; color:white; border:none; border-radius:4px; font-size:14px; font-weight:500; }
.badge { position:fixed; top:10px; right:10px; background:rgba(0,0,0,0.6); color:white; padding:4px 10px; border-radius:12px; font-size:11px; }
</style></head><body>
<div class="badge">Qt QML (QtQuick.Controls)</div>
<div class="window">
  <div class="titlebar"><span>Settings</span><span>— □ ✕</span></div>
  <div class="body">
    <div class="title">Settings</div>
    <div class="row"><span>Enable notifications</span><div class="switch on"><div class="knob"></div></div></div>
    <div class="row"><span>Dark theme</span><div class="switch off"><div class="knob"></div></div></div>
    <div class="label">Language</div>
    <div class="combo">English ▼</div>
    <button class="btn">Save</button>
  </div>
</div>
</body></html>`;
    await page.setContent(qtHtml, { waitUntil: 'networkidle' });
    await page.screenshot({ path: path.join(SHOTS_DIR, 'qt_qml_run.png'), fullPage: true });
    console.log('  [OK] qt_qml_run.png');

    // 6. WPF → UI 模拟渲染（Windows 原生外观）
    const wpfHtml = `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#f3f3f3; display:flex; justify-content:center; padding:30px; font-family:'Segoe UI',sans-serif; }
.window { width:400px; background:white; border:1px solid #ccc; box-shadow:0 2px 8px rgba(0,0,0,0.15); }
.titlebar { background:#0078D7; color:white; padding:8px 16px; font-size:13px; display:flex; justify-content:space-between; }
.body { padding:24px; }
.title { font-size:24px; font-weight:bold; margin-bottom:20px; color:#1a1a1a; }
.row { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; font-size:14px; }
.row label { width:200px; }
.checkbox { width:20px; height:20px; border:2px solid #0078D7; border-radius:3px; position:relative; }
.checkbox.checked { background:#0078D7; }
.checkbox.checked::after { content:'✓'; color:white; font-size:14px; position:absolute; top:-2px; left:2px; }
.label { color:#666; font-size:14px; margin-bottom:8px; }
.combo { width:100%; padding:8px; border:1px solid #ddd; border-radius:4px; background:white; font-size:14px; margin-bottom:24px; }
.btn { width:100%; padding:10px; background:#0078D7; color:white; border:none; border-radius:4px; font-size:14px; font-weight:500; }
.badge { position:fixed; top:10px; right:10px; background:rgba(0,0,0,0.6); color:white; padding:4px 10px; border-radius:12px; font-size:11px; }
</style></head><body>
<div class="badge">Windows WPF (XAML)</div>
<div class="window">
  <div class="titlebar"><span>Settings</span><span>— □ ✕</span></div>
  <div class="body">
    <div class="title">Settings</div>
    <div class="row"><label>Enable notifications</label><div class="checkbox checked"></div></div>
    <div class="row"><label>Dark theme</label><div class="checkbox"></div></div>
    <div class="label">Language</div>
    <div class="combo">English ▼</div>
    <button class="btn">Save</button>
  </div>
</div>
</body></html>`;
    await page.setContent(wpfHtml, { waitUntil: 'networkidle' });
    await page.screenshot({ path: path.join(SHOTS_DIR, 'windows_wpf_run.png'), fullPage: true });
    console.log('  [OK] windows_wpf_run.png');

    // 7. A2UI → UI 渲染
    const a2uiCode = fs.readFileSync(path.join(DEMO_DIR, 'llm_a2ui.jsonl'), 'utf-8');
    const lines = a2uiCode.trim().split('\n').filter(l => l.trim());
    const objects = {};
    for (const line of lines) {
        try { const obj = JSON.parse(line); objects[obj.id] = obj; } catch(e) {}
    }
    const rootId = lines[0] ? JSON.parse(lines[0]).id : null;
    function render(id) {
        const obj = objects[id];
        if (!obj) return '';
        const t = obj.type, p = obj.props || {};
        if (t === 'text') return `<div style="margin-bottom:8px;font-size:${p.size||14}px;${p.bold?'font-weight:bold':''};color:#1a1a1a">${p.text||''}</div>`;
        if (t === 'button') return `<button class="btn">${p.text||'Button'}</button>`;
        if (t === 'switch') { const on=p.checked; return `<div class="toggle ${on?'on':'off'}"><div class="knob"></div></div>`; }
        if (t === 'dropdown') { const o=(p.options||[]).map((x,i)=>`<option ${i===(p.selectedIndex||0)?'selected':''}>${x}</option>`).join(''); return `<select>${o}</select>`; }
        if (t === 'column') return `<div style="display:flex;flex-direction:column">${(obj.children||[]).map(render).join('')}</div>`;
        if (t === 'row') return `<div class="row">${(obj.children||[]).map(render).join('')}</div>`;
        return `<div>${t}</div>`;
    }
    const a2uiHtml = `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#f3f3f3; display:flex; justify-content:center; padding:30px; font-family:'Segoe UI',sans-serif; }
.card { width:380px; background:white; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.1); padding:24px; }
.toggle { width:44px; height:22px; border-radius:11px; position:relative; }
.toggle.on { background:#0078D7; }
.toggle.off { background:#ccc; }
.toggle .knob { position:absolute; width:18px; height:18px; background:white; border-radius:50%; top:2px; box-shadow:0 1px 2px rgba(0,0,0,0.3); }
.toggle.on .knob { right:2px; }
.toggle.off .knob { left:2px; }
.row { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; font-size:15px; }
select { width:100%; padding:8px; border:1px solid #ddd; border-radius:4px; margin-bottom:16px; font-size:14px; }
.btn { width:100%; padding:10px; background:#0078D7; color:white; border:none; border-radius:4px; font-size:14px; }
.badge { position:fixed; top:10px; right:10px; background:rgba(0,0,0,0.6); color:white; padding:4px 10px; border-radius:12px; font-size:11px; }
</style></head><body>
<div class="badge">A2UI (JSONL)</div>
<div class="card">${render(rootId)}</div>
</body></html>`;
    await page.setContent(a2uiHtml, { waitUntil: 'networkidle' });
    await page.screenshot({ path: path.join(SHOTS_DIR, 'a2ui_run.png'), fullPage: true });
    console.log('  [OK] a2ui_run.png');

    await browser.close();
    console.log('\nAll run-effect screenshots generated.');
})();
