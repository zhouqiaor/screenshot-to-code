const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const DEMO_DIR = 'C:/Code/s2c-work/e2e_demo';
const SHOTS_DIR = path.join(DEMO_DIR, 'screenshots');

if (!fs.existsSync(SHOTS_DIR)) fs.mkdirSync(SHOTS_DIR, { recursive: true });

// ============ UI 模拟渲染器 ============

// 通用设置页 HTML 生成器（所有栈都渲染成类似的 UI）
function settingsUIHtml(opts) {
    const {
        title = 'Settings',
        platform, // 'Android', 'iOS', 'Windows', 'Qt', 'WPF', 'A2UI'
        accentColor = '#007AFF',
        bgColor = '#f5f5f5',
        fontFamily = 'sans-serif',
        cardStyle = '',
        toggleOn = [true, false], // [notifications, darkTheme]
        languages = ['English', '简体中文'],
    } = opts;

    const toggles = ['Enable notifications', 'Dark theme'].map((label, i) => {
        const on = toggleOn[i];
        const toggleColor = on ? accentColor : '#ccc';
        const knobPos = on ? 'left: 24px' : 'left: 2px';
        return `<div class="row"><span>${label}</span><div class="toggle" style="background:${toggleColor}"><div class="knob" style="${knobPos}"></div></div></div>`;
    }).join('');

    const langOpts = languages.map((l, i) => `<option ${i===0?'selected':''}>${l}</option>`).join('');

    return `<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:${bgColor}; display:flex; justify-content:center; align-items:flex-start; padding:40px; min-height:100vh; font-family:${fontFamily}; }
.card { width:380px; background:white; border-radius:${platform==='Android'?'16px':'8px'}; box-shadow:0 2px 12px rgba(0,0,0,0.1); overflow:hidden; ${cardStyle} }
.header { background:${accentColor}; color:white; padding:16px 20px; font-size:16px; font-weight:600; display:flex; align-items:center; gap:8px; }
.header .icon { width:20px; height:20px; display:inline-block; }
.body { padding:24px; }
.title { font-size:24px; font-weight:bold; margin-bottom:20px; color:#1a1a1a; }
.row { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; font-size:15px; color:#333; }
.toggle { width:44px; height:24px; border-radius:24px; position:relative; transition:0.2s; }
.knob { position:absolute; width:20px; height:20px; background:white; border-radius:50%; top:2px; transition:0.2s; box-shadow:0 1px 3px rgba(0,0,0,0.3); }
.label { margin-bottom:8px; color:#666; font-size:14px; }
select { width:100%; padding:10px; border:1px solid #ddd; border-radius:6px; margin-bottom:20px; font-size:14px; background:white; }
.btn { width:100%; padding:12px; background:${accentColor}; color:white; border:none; border-radius:6px; font-size:15px; font-weight:500; cursor:pointer; }
.platform-badge { position:fixed; top:10px; right:10px; background:rgba(0,0,0,0.7); color:white; padding:4px 12px; border-radius:12px; font-size:11px; }
</style></head>
<body>
<div class="platform-badge">${platform}</div>
<div class="card">
  <div class="header">${platform} Settings</div>
  <div class="body">
    <div class="title">${title}</div>
    ${toggles}
    <div class="label">Language</div>
    <select>${langOpts}</select>
    <button class="btn">Save</button>
  </div>
</div>
</body></html>`;
}

// 1. Windows HTML (直接渲染原始文件)
function renderWindowsHtml() {
    return fs.readFileSync(path.join(DEMO_DIR, 'llm_windows_html.html'), 'utf-8');
}

// 2. Windows WPF (模拟 WPF 外观)
function renderWPF() {
    return settingsUIHtml({
        platform: 'WPF',
        title: 'Settings',
        accentColor: '#0078D7',
        fontFamily: "'Segoe UI', sans-serif",
        cardStyle: 'border:1px solid #ddd;',
    });
}

// 3. Android (Material Design 风格)
function renderAndroid() {
    return settingsUIHtml({
        platform: 'Android',
        title: 'Settings',
        accentColor: '#6750A4', // Material 3 primary
        bgColor: '#FFFBFE',
        fontFamily: "'Roboto', 'Segoe UI', sans-serif",
        cardStyle: 'border-radius:16px;',
        toggleOn: [true, false],
    });
}

// 4. Qt QML (模拟 Qt Controls 外观)
function renderQt() {
    return settingsUIHtml({
        platform: 'Qt QML',
        title: 'Settings',
        accentColor: '#007AFF',
        fontFamily: "'Segoe UI', Arial, sans-serif",
        bgColor: '#f5f5f5',
    });
}

// 5. A2UI (解析 JSONL 渲染)
function renderA2UI() {
    const code = fs.readFileSync(path.join(DEMO_DIR, 'llm_a2ui.jsonl'), 'utf-8');
    const lines = code.trim().split('\n').filter(l => l.trim());
    const objects = {};
    for (const line of lines) {
        try { const obj = JSON.parse(line); objects[obj.id] = obj; } catch(e) {}
    }
    const rootId = lines[0] ? JSON.parse(lines[0]).id : null;

    function render(id) {
        const obj = objects[id];
        if (!obj) return '';
        const type = obj.type;
        const props = obj.props || {};
        if (type === 'text') {
            const size = props.size || 14;
            const bold = props.bold ? 'font-weight:bold' : '';
            return `<div style="margin-bottom:8px;font-size:${size}px;${bold};color:#1a1a1a">${props.text||''}</div>`;
        }
        if (type === 'button') {
            return `<button class="btn" style="background:#0078D7">${props.text||'Button'}</button>`;
        }
        if (type === 'switch') {
            const on = props.checked;
            const bg = on ? '#0078D7' : '#ccc';
            const pos = on ? 'left:24px' : 'left:2px';
            return `<div class="toggle" style="background:${bg}"><div class="knob" style="${pos}"></div></div>`;
        }
        if (type === 'dropdown') {
            const opts = (props.options||[]).map((o,i) => `<option ${i===(props.selectedIndex||0)?'selected':''}>${o}</option>`).join('');
            return `<select>${opts}</select>`;
        }
        if (type === 'column') {
            return `<div style="display:flex;flex-direction:column">${(obj.children||[]).map(render).join('')}</div>`;
        }
        if (type === 'row') {
            return `<div class="row" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">${(obj.children||[]).map(render).join('')}</div>`;
        }
        return `<div>${type}</div>`;
    }

    return `<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#f3f3f3; display:flex; justify-content:center; padding:40px; font-family:'Segoe UI',sans-serif; }
.card { width:380px; background:white; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.1); padding:24px; }
.toggle { width:44px; height:24px; border-radius:24px; position:relative; }
.knob { position:absolute; width:20px; height:20px; background:white; border-radius:50%; top:2px; box-shadow:0 1px 3px rgba(0,0,0,0.3); }
.row { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; font-size:15px; }
select { width:100%; padding:10px; border:1px solid #ddd; border-radius:6px; margin-bottom:20px; font-size:14px; }
.btn { width:100%; padding:12px; color:white; border:none; border-radius:6px; font-size:15px; cursor:pointer; }
.platform-badge { position:fixed; top:10px; right:10px; background:rgba(0,0,0,0.7); color:white; padding:4px 12px; border-radius:12px; font-size:11px; }
</style></head>
<body>
<div class="platform-badge">A2UI</div>
<div class="card">${render(rootId)}</div>
</body></html>`;
}

// 6. Kotlin Compose (模拟 Compose Material 3 外观)
function renderCompose() {
    return settingsUIHtml({
        platform: 'Android Compose',
        title: 'Settings',
        accentColor: '#6750A4',
        bgColor: '#FFFBFE',
        fontFamily: "'Roboto', 'Segoe UI', sans-serif",
        cardStyle: 'border-radius:16px;',
    });
}

// ============ 主流程 ============

(async () => {
    const browser = await chromium.launch();
    const page = await browser.newPage({ viewport: { width: 500, height: 700 } });

    const tasks = [
        { name: '01_windows_html', render: renderWindowsHtml },
        { name: '02_windows_wpf', render: renderWPF },
        { name: '03_android_xml', render: () => settingsUIHtml({ platform:'Android XML', accentColor:'#6750A4', fontFamily:"'Roboto',sans-serif", cardStyle:'border-radius:16px;' }) },
        { name: '04_android_compose', render: renderCompose },
        { name: '05_qt_qml', render: renderQt },
        { name: '06_a2ui', render: renderA2UI },
    ];

    for (const task of tasks) {
        const outPath = path.join(SHOTS_DIR, `${task.name}.png`);
        const html = task.render();
        await page.setContent(html, { waitUntil: 'networkidle' });
        await page.screenshot({ path: outPath, fullPage: true });
        console.log(`  [OK] ${task.name}.png`);
    }

    // 合并对比图
    await page.setViewportSize({ width: 1600, height: 900 });
    const combinedHtml = `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#1a1a1a; padding:20px; }
h1 { color:white; font-family:sans-serif; margin-bottom:20px; }
.grid { display:grid; grid-template-columns:repeat(3,1fr); gap:20px; }
.item { text-align:center; }
.item img { width:100%; border-radius:8px; box-shadow:0 4px 12px rgba(0,0,0,0.5); }
.item .label { color:white; font-family:sans-serif; font-size:14px; margin-top:8px; }
</style></head><body>
<h1>Screenshot-to-Code: 6 Stack UI Rendering Comparison</h1>
<div class="grid">
${tasks.map(t => `<div class="item"><img src="${t.name}.png"><div class="label">${t.name.replace(/^\d+_/, '')}</div></div>`).join('')}
</div>
</body></html>`;
    await page.setContent(combinedHtml, { waitUntil: 'networkidle' });
    await page.screenshot({ path: path.join(SHOTS_DIR, '00_comparison.png'), fullPage: true });
    console.log('  [OK] 00_comparison.png');

    await browser.close();
    console.log(`\nAll UI effect screenshots saved to ${SHOTS_DIR}`);
})();
