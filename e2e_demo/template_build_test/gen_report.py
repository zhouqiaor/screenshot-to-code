import base64, json
from pathlib import Path
from datetime import datetime

base = Path(r'C:\Code\screenshot-to-code\e2e_demo\template_build_test')
run_dir = Path(r'C:\Code\screenshot-to-code\e2e_demo\run_20260901')

def img_b64(path):
    p = Path(path)
    if not p.exists():
        return ''
    return f'data:image/png;base64,{base64.b64encode(p.read_bytes()).decode()}'

def size_str(path):
    p = Path(path)
    if not p.exists():
        return 'N/A'
    s = p.stat().st_size
    if s > 1024*1024:
        return f'{s/1024/1024:.1f}MB'
    return f'{s/1024:.1f}KB'

compose_apk_size = size_str(base / 'kotlin_compose/app/build/outputs/apk/debug/app-debug.apk')
xml_apk_size = size_str(base / 'android_xml_full/final_signed.apk')
qml_exe_size = size_str(base / 'qt_qml_full/build/E2ESettings.exe')

stacks = [
    {
        'name': 'Kotlin Compose', 'icon': 'K',
        'compile': f'BUILD SUCCESSFUL (24s)',
        'detail': 'Gradle 8.9 + AGP 8.5.2 + Kotlin 1.9.24 + Compose 1.7.3',
        'output': f'APK {compose_apk_size}',
        'fix': 'Added package declaration + fillMaxHeight import',
        'status': 'pass',
        'img': '',
        'img_size': '',
    },
    {
        'name': 'Android XML', 'icon': 'X',
        'compile': 'aapt2 compile + link + javac + d8 + apksigner - ALL PASS',
        'detail': 'aapt2 34.0.0 + android.jar SDK 34 + JDK 21 + d8 + apksigner',
        'output': f'Signed APK {xml_apk_size} (AndroidManifest + resources.arsc + classes.dex + META-INF)',
        'fix': 'Replaced AppCompat widgets with framework: AppCompatButton->Button, AppCompatEditText->EditText, SwitchCompat->Switch, app:thumbTint->android:thumbTint, app:trackTint->android:trackTint; Replaced ic_menu_daydream->ic_menu_manage (framework drawable not found)',
        'status': 'pass',
        'img': img_b64(run_dir / 'deep_verify/xml_screenshot.png'),
        'img_size': size_str(run_dir / 'deep_verify/xml_screenshot.png'),
    },
    {
        'name': 'Qt QML', 'icon': 'Q',
        'compile': 'CMake configure + build - ALL PASS',
        'detail': 'CMake 3.x + MinGW 13.1.0 + Qt 6.11.0 (Quick/Controls2/Layouts)',
        'output': f'E2ESettings.exe {qml_exe_size} (PE executable, Qt6 DLLs linked)',
        'fix': 'CMakeLists: qt_add_executable -> qt6_add_executable, qt_add_qml_module -> qt6_add_qml_module, explicit Qt6:: targets',
        'status': 'pass',
        'img': img_b64(base / 'qml_screenshot.png'),
        'img_size': size_str(base / 'qml_screenshot.png'),
    },
    {
        'name': 'Windows HTML', 'icon': 'H',
        'compile': 'Edge headless render OK',
        'detail': 'No compilation needed',
        'output': f'PNG {size_str(base / "html_screenshot.png")}',
        'fix': 'No fix needed',
        'status': 'pass',
        'img': img_b64(base / 'html_screenshot.png'),
        'img_size': size_str(base / 'html_screenshot.png'),
    },
    {
        'name': 'A2UI', 'icon': 'A',
        'compile': 'JSONL parse + runner.html render',
        'detail': 'a2ui_runner.html (JSONL to DOM)',
        'output': f'PNG {size_str(base / "a2ui_screenshot.png")}',
        'fix': 'JSONL inlined into runner.html (bypass file:// CORS)',
        'status': 'pass',
        'img': img_b64(base / 'a2ui_screenshot.png'),
        'img_size': size_str(base / 'a2ui_screenshot.png'),
    },
    {
        'name': 'WinUI3', 'icon': 'W',
        'compile': 'NuGet restore OK / XAML compiler FAILED',
        'detail': 'dotnet build + WindowsAppSDK 1.5 - XamlCompiler.exe (net472) needs VS MSBuild',
        'output': 'C# ready, XAML pre-compile needs Visual Studio',
        'fix': 'csproj: RID win10->win, remove duplicate ApplicationDefinition/Page',
        'status': 'partial',
        'img': img_b64(base / 'winui3_screenshot.png'),
        'img_size': size_str(base / 'winui3_screenshot.png'),
    },
]

now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
passed = sum(1 for s in stacks if s['status'] == 'pass')
partial = sum(1 for s in stacks if s['status'] == 'partial')

stacks_html = ''
for s in stacks:
    badge = 'PASS' if s['status'] == 'pass' else ('PARTIAL' if s['status'] == 'partial' else 'FAIL')
    cls = s['status']
    img_html = ''
    if s['img']:
        img_html = f'<img src="{s["img"]}" class="screenshot" loading="lazy">'
    stacks_html += f'''
    <div class="stack-card {cls}">
        <div class="stack-header"><span class="icon">{s["icon"]}</span><h3>{s["name"]}</h3><span class="badge {cls}">{badge}</span></div>
        <div class="stack-body">
            <div class="row"><span class="label">Compile</span><span>{s["compile"]}</span></div>
            <div class="row"><span class="label">Toolchain</span><span class="mono">{s["detail"]}</span></div>
            <div class="row"><span class="label">Output</span><span>{s["output"]}</span></div>
            <div class="row"><span class="label">Fix</span><span>{s["fix"]}</span></div>
            {img_html}
        </div>
    </div>'''

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>6 Stack E2E Compile Report - {now}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Segoe UI','Microsoft YaHei',sans-serif; background: #0d1117; color: #c9d1d9; line-height: 1.6; }}
.container {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
h1 {{ font-size: 28px; margin-bottom: 8px; color: #58a6ff; }}
h2 {{ font-size: 20px; margin: 24px 0 12px; color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 6px; }}
.meta {{ color: #8b949e; font-size: 13px; margin-bottom: 24px; }}
.summary {{ display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }}
.stat {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px 24px; min-width: 140px; text-align: center; }}
.stat .num {{ font-size: 32px; font-weight: 700; }}
.stat .label {{ font-size: 13px; color: #8b949e; }}
.stat.pass .num {{ color: #3fb950; }}
.stat.partial .num {{ color: #d29922; }}
.stat.total .num {{ color: #58a6ff; }}
.stack-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
.stack-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; overflow: hidden; }}
.stack-card.pass {{ border-left: 4px solid #3fb950; }}
.stack-card.partial {{ border-left: 4px solid #d29922; }}
.stack-header {{ display: flex; align-items: center; gap: 8px; padding: 12px 16px; border-bottom: 1px solid #30363d; }}
.stack-header h3 {{ font-size: 16px; flex: 1; }}
.stack-header .icon {{ font-size: 20px; font-weight: 700; color: #58a6ff; }}
.badge {{ padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
.badge.pass {{ background: #1a3a2a; color: #3fb950; }}
.badge.partial {{ background: #3a321a; color: #d29922; }}
.badge.fail {{ background: #3a1a1a; color: #f85149; }}
.stack-body {{ padding: 12px 16px; }}
.row {{ display: flex; gap: 8px; margin: 4px 0; font-size: 13px; }}
.row .label {{ min-width: 80px; color: #8b949e; }}
.mono {{ font-family: 'Cascadia Code',monospace; font-size: 12px; }}
.screenshot {{ width: 100%; border-radius: 4px; margin: 8px 0; border: 1px solid #30363d; }}
table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
th, td {{ padding: 8px 12px; text-align: left; border: 1px solid #30363d; font-size: 13px; }}
th {{ background: #161b22; color: #58a6ff; }}
.note {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; margin: 16px 0; }}
.note h3 {{ color: #d29922; margin-bottom: 8px; }}
code {{ background: #1e2429; padding: 2px 6px; border-radius: 3px; font-size: 12px; color: #f0883e; }}
.pipeline {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; margin: 12px 0; }}
.pipeline h3 {{ color: #3fb950; margin-bottom: 8px; }}
.pipeline ol {{ padding-left: 20px; }}
.pipeline li {{ margin: 4px 0; }}
.pipeline .step-pass {{ color: #3fb950; }}
</style>
</head>
<body>
<div class="container">
<h1>6 Stack E2E Compile Verification Report</h1>
<div class="meta">Generated: {now} | Dir: e2e_demo/template_build_test/</div>

<div class="summary">
<div class="stat pass"><div class="num">{passed}</div><div class="label">Full Pass</div></div>
<div class="stat partial"><div class="num">{partial}</div><div class="label">Partial</div></div>
<div class="stat total"><div class="num">6</div><div class="label">Total Stacks</div></div>
</div>

<h2>Per-Stack Compile Details</h2>
<div class="stack-grid">
{stacks_html}
</div>

<h2>Android XML Full Build Pipeline (6 Steps)</h2>
<div class="pipeline">
<h3>Complete aapt2 -> javac -> d8 -> apksigner Pipeline</h3>
<ol>
<li class="step-pass">aapt2 compile: res/layout/activity_main.xml -> compiled.zip (21916 bytes)</li>
<li class="step-pass">aapt2 link: .flat + android.jar + AndroidManifest.xml -> base4.apk (3765 bytes) + R.java (4 IDs)</li>
<li class="step-pass">javac: R.java + MainActivity.java -> 4 .class files (JDK 21, source/target 8)</li>
<li class="step-pass">d8 dex: .class files -> classes.dex (1760 bytes)</li>
<li class="step-pass">Python zipfile: merge classes.dex into base4.apk -> final2.apk (5623 bytes)</li>
<li class="step-pass">apksigner sign: debug.keystore -> final_signed.apk ({xml_apk_size}), verify PASS</li>
</ol>
<p><strong>APK contents:</strong> AndroidManifest.xml, res/layout/activity_main.xml, resources.arsc, classes.dex, META-INF (ANDROIDD.SF + ANDROIDD.RSA + MANIFEST.MF)</p>
</div>

<h2>Qt QML Full Build Pipeline (CMake + MinGW)</h2>
<div class="pipeline">
<h3>CMake Configure + Build</h3>
<ol>
<li class="step-pass">CMake configure: Qt6 6.11.0 + MinGW 13.1.0 + MinGW Makefiles generator</li>
<li class="step-pass">QML source copy + qmlimportscanner + AUTOMOC</li>
<li class="step-pass">RCC resource compilation (2 qrc files)</li>
<li class="step-pass">QML type registration + QML cache generation (main_qml.cpp + loader)</li>
<li class="step-pass">C++ compilation: main.cpp + 5 generated .cpp -> .obj files</li>
<li class="step-pass">Linking: E2ESettings.exe ({qml_exe_size}) - Qt6Core/Gui/Qml/QuickControls2 DLLs</li>
</ol>
<p><strong>DLL dependencies:</strong> Qt6Core.dll, Qt6Gui.dll, Qt6Qml.dll, Qt6QuickControls2.dll, libgcc_s_seh-1.dll, libstdc++-6.dll, KERNEL32.dll, msvcrt.dll</p>
</div>

<h2>Verification Matrix</h2>
<table>
<tr><th>Stack</th><th>L1 Syntax</th><th>L2 Compile</th><th>L3 Screenshot</th><th>L4 Device</th><th>Status</th></tr>
<tr><td>Kotlin Compose</td><td>validate_code</td><td>Gradle 24s -> APK 15MB</td><td>~HTML 22KB</td><td>APK to device</td><td>PASS</td></tr>
<tr><td>Android XML</td><td>validate_code</td><td>aapt2+javac+d8+sign -> APK {xml_apk_size}</td><td>XML to HTML 26KB</td><td>WebView 118KB</td><td>PASS</td></tr>
<tr><td>Qt QML</td><td>qmllint 0 errors</td><td>CMake+MinGW -> exe {qml_exe_size}</td><td>QML to HTML 31KB</td><td>-</td><td>PASS</td></tr>
<tr><td>Windows HTML</td><td>validate_code</td><td>- no compile</td><td>Edge direct 26KB</td><td>-</td><td>PASS</td></tr>
<tr><td>A2UI</td><td>37/37 JSON</td><td>JSONL parse</td><td>runner.html 8.8KB</td><td>-</td><td>PASS</td></tr>
<tr><td>WinUI3</td><td>tag balanced</td><td>NuGet OK / XAML FAIL</td><td>XAML to HTML 32KB</td><td>-</td><td>PARTIAL</td></tr>
</table>

<h2>Toolchain Environment</h2>
<table>
<tr><th>Tool</th><th>Version/Path</th><th>Status</th></tr>
<tr><td>Gradle</td><td>8.9 (~/.gradle/wrapper/dists/)</td><td>Installed</td></tr>
<tr><td>AGP + Kotlin</td><td>8.5.2 + 1.9.24</td><td>Gradle deps</td></tr>
<tr><td>aapt2</td><td>34.0.0 (Android SDK build-tools)</td><td>Installed</td></tr>
<tr><td>android.jar</td><td>android-34</td><td>Installed</td></tr>
<tr><td>JDK</td><td>21.0.11 (C:\\Programs\\Java\\jdk-21.0.11)</td><td>Installed</td></tr>
<tr><td>d8 + apksigner</td><td>34.0.0 (build-tools)</td><td>Installed</td></tr>
<tr><td>debug.keystore</td><td>C:\\Users\\georgeslark\\.android\\</td><td>Available</td></tr>
<tr><td>Edge</td><td>Headless new mode</td><td>Installed</td></tr>
<tr><td>Qt SDK</td><td>6.11.0 + 5.15.2 (C:\\Programs\\Qt)</td><td>Installed</td></tr>
<tr><td>CMake</td><td>Qt Tools CMake_64</td><td>Installed</td></tr>
<tr><td>MinGW</td><td>13.1.0 (mingw1310_64)</td><td>Installed</td></tr>
<tr><td>.NET SDK</td><td>8.0.424 + 6.0.428 (~/.dotnet)</td><td>Installed</td></tr>
<tr><td>WindowsAppSDK</td><td>1.5.240607001 (NuGet)</td><td>NuGet restore OK</td></tr>
<tr><td>Visual Studio MSBuild</td><td>Not installed</td><td>Required for WinUI3 XAML</td></tr>
<tr><td>ADB</td><td>platform-tools</td><td>Installed</td></tr>
</table>

<div class="note">
<h3>WinUI3 Compile Limitation</h3>
<p>WinUI3 XAML compiler (<code>XamlCompiler.exe</code>, net472) exits with code 1 under <code>dotnet build</code> (Core MSBuild).
This is <strong>not a XAML syntax issue</strong> but a known WinUI3 limitation - XAML pre-compilation requires Visual Studio's full MSBuild (not .NET Core version).</p>
<p><strong>Verified parts:</strong></p>
<ul>
<li>NuGet restore OK (27s)</li>
<li>csproj syntax OK (RID fix + ApplicationDefinition fix)</li>
<li>XAML structure validation OK (15 controls, 65 instances, tag balanced)</li>
<li>XAML to HTML render OK (32KB screenshot)</li>
</ul>
<p><strong>Solution:</strong> Install VS 2022 Community (free) or Build Tools 2022 (with WinUI workload), then <code>msbuild E2EApp.csproj /p:Platform=x64</code>.</p>
</div>

<h2>LLM Code Fix Log</h2>
<table>
<tr><th>Stack</th><th>Issue</th><th>Fix</th></tr>
<tr><td>Kotlin Compose</td><td>Missing <code>package</code> declaration + missing <code>fillMaxHeight</code> import</td><td>Add <code>package com.e2e.settings</code> + <code>import ...fillMaxHeight</code></td></tr>
<tr><td>Android XML</td><td>AppCompat widgets + attrs not in framework android.jar</td><td>AppCompatButton->Button, AppCompatEditText->EditText, SwitchCompat->Switch, app:thumbTint->android:thumbTint, app:trackTint->android:trackTint; ic_menu_daydream->ic_menu_manage</td></tr>
<tr><td>Qt QML</td><td>CMake commands used old qt_ prefix</td><td>qt_add_executable->qt6_add_executable, qt_add_qml_module->qt6_add_qml_module, explicit Qt6:: targets</td></tr>
<tr><td>Windows HTML</td><td>No issues</td><td>-</td></tr>
<tr><td>A2UI</td><td>file:// protocol fetch CORS restriction</td><td>JSONL inlined into runner.html</td></tr>
<tr><td>WinUI3</td><td>csproj RID format + duplicate ApplicationDefinition</td><td>win10-x64 to win-x64, remove explicit ApplicationDefinition</td></tr>
</table>

</div>
</body>
</html>'''

out = base / 'e2e_compile_report.html'
out.write_text(html, encoding='utf-8')
print(f'Report: {out.stat().st_size} bytes -> {out}')
