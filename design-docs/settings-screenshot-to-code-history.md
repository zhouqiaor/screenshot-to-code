# 设置界面截图转代码 - 历史记录分析

> 生成日期: 2026-09-01 20:46 | 仓库: C:\Code\screenshot-to-code

---

## 一、概述

本项目历史中共记录了 **四轮** "设置界面截图转代码" 的完整 E2E 生成记录，按时间顺序为：

| 轮次 | 日期 | Commit | 目录 | 模型 | 栈数 | Token |
|------|------|--------|------|------|------|-------|
| Phase 0 | 2026-09-01 08:42 | `872695c` | `e2e_demo/` (根) | doubao-seed-evolving | 6 | 8,346 |
| Phase 1 | 2026-09-01 09:06-10:40 | `bf54dde`→`5ff932e` | `e2e_test/` | 模板/LLM 混合 | 6 | ~8,346 |
| Phase 2 | 2026-09-01 17:00-20:15 | (未提交) | `e2e_demo/run_20260901/` | seed-2-1-turbo | 5 | 58,618 |
| Phase 3 | 2026-09-01 20:49 | (未提交) | `e2e_demo/run_20260901/deep_verify/` | 深度验证 | 4+1(WinUI3) | — |

> **Phase 3 (deep_verify)** 是 Phase 2 的扩展深度验证，新增 **WinUI3 XAML** 栈（`settings_page.xaml`，8133 chars）、aapt2 编译验证、设备渲染截图、QML 深度结构分析。

| 维度 | Phase 1: 模板生成 | Phase 2: LLM 视觉生成 |
|------|-------------------|----------------------|
| **日期** | 2026-08-31 | 2026-09-01 |
| **源截图** | `captures/settings_page_initial.png`（已不在本地） | ADB 截屏 Android 设置-声音与显示（5.8MB PNG） |
| **LLM 模型** | doubao-seed-evolving | doubao-seed-2-1-turbo-260628 |
| **Token 消耗** | 8,346 (1547 in + 6799 out) | 58,618 (2506 in + 55968 out) |
| **费用** | 免费（额度内） | ¥0.85 |
| **技术栈数** | 6 栈（含 WPF） | 5 栈（无 WPF） |
| **代码总字符** | ~10,780 chars | ~59,644 chars |
| **验证结果** | 6/6 PASS | 5/5 PASS（compile_report 中 HTML 有 1 error） |

---

## 二、Phase 0: 首次 LLM 6 栈生成 (2026-09-01 08:42)

### 2.0.1 Git 记录

- **Commit**: `872695c` — "feat: add windows_wpf stack + e2e demo for 6 UI stacks"
- **作者**: zhouqiao8
- **时间**: 2026-09-01 08:42:06 +0800
- **改动**: 26 files, +1690 -1 lines
- **这是首次 Kotlin/Android 开发时执行的设置界面截图转代码**

### 2.0.2 源截图

- 来源: `captures/settings_page_initial.png`（test_report.json 记录）
- 内容: 简单 Settings 设置界面（Dark Mode 开关、Notifications 开关、Language 下拉、Save 按钮）

### 2.0.3 LLM 模型与 Token

- **模型**: `doubao-seed-evolving`（火山引擎免费额度）
- **Token**: 8,346 (1547 input + 6799 output)
- **策略**: 一次性 LLM 调用生成 6 栈代码，WPF XAML 手写骨架（0 tokens）

### 2.0.4 生成产物（e2e_demo/ 根目录）

| 技术栈 | 文件 | 字符数 | validate_code | 错误 | 警告 |
|--------|------|--------|---------------|------|------|
| Android XML | llm_android_xml.xml | 1,553 | PASS | 0 | 0 |
| Android Compose | llm_android_compose.kt | 2,209 | PASS | 0 | 0 |
| Qt QML | llm_qt_qml.qml | 1,353 | PASS | 0 | 0 |
| Windows HTML | llm_windows_html.html | 2,961 | PASS | 0 | 0 |
| Windows WPF | llm_windows_wpf.xaml | 2,034 | PASS | 0 | 0 |
| A2UI JSONL | llm_a2ui.jsonl | 943 | PASS | 0 | 3 |

**raw_output.txt**: 284 行，含 `===SEP===` 分隔的 6 栈原始 LLM 输出

**A2UI 警告详情**：`switch` 和 `dropdown` 类型不在 A2UI 标准类型列表中（仅支持 button/card/column/container/image/input/list/row/stack/text）。11 行 JSONL，11 个节点。

### 2.0.5 截图渲染

使用 Playwright Chromium（render_screenshots.cjs）渲染 6 张截图：
- `screenshots/a2ui.png` (9KB)
- `screenshots/android_compose.png` (53KB)
- `screenshots/android_xml.png` (37KB)
- `screenshots/qt_qml.png` (33KB)
- `screenshots/windows_html.png` (9KB)
- `screenshots/windows_wpf.png` (10KB)

### 2.0.6 后续增强（同日 09:06-10:40）

| 时间 | Commit | 内容 |
|------|--------|------|
| 09:06 | `bf54dde` | docs: 端到端编译验证报告 (compilation_report.md, 176 行) |
| 10:20 | `be726cc` | docs: 完整 E2E 编译报告 L1-L4 验证 + kotlin_compile_test.kt |
| 10:25 | `8ab84be` | feat: 6 栈端到端运行效果截图 (render_kotlin_output.cjs + render_ui_effects.cjs) |
| 10:40 | `5ff932e` | feat: Android APK 编译+签名+安装到设备 200.47.91.1 |

**Phase 0 APK 构建** (commit `5ff932e`):
- 手动构建: aapt2 compile/link → kotlinc → d8 → apksigner v3
- APK 7099 bytes, targetSdk=31, minSdk=29
- 安装到 TEQU-S2C 设备 (Android 12, SDK 31, 3840×2160)
- 包名: com.example.settings
- 设备有 Kiosk 模式阻止前台显示

### 2.0.7 Phase 0 关键特征

1. **首次将 LLM 生成的 Kotlin Compose 代码编译为 APK 并安装到真实设备**
2. 6 栈全部通过 validate_code，6/6 截图渲染成功
3. Kotlin 纯编译验证（kotlin_compile_test.kt → 5.3MB jar → 运行成功）
4. OpenCodeReview 6 轮迭代审查（11→4→13→14→7→8 findings，全部修复）
5. PR #3 squash-merged 到 main as `bd7b349`

---

## 三、Phase 1: 模板对照验证 (2026-09-01 ~09:00)

### 3.1 源截图
- 路径: `captures/settings_page_initial.png`（test_report.json 记录，文件已不在本地）
- 内容: 简单的 Settings 设置界面（含 Dark Mode 开关、Language 下拉选择、Save 按钮）

### 3.2 生成产物（e2e_test/ 目录）

| 技术栈 | 文件 | 字符数 | 验证 | 错误 | 警告 |
|--------|------|--------|------|------|------|
| Android XML | settings_android_xml.xml | 1,973 | PASS | 0 | 0 |
| Android Compose | settings_android_compose.kt | 1,988 | PASS | 0 | 0 |
| Qt QML | settings_qt_qml.qml | 1,167 | PASS | 0 | 0 |
| Windows HTML | settings_windows_win32.html | 2,954 | PASS | 0 | 0 |
| A2UI JSONL | settings_a2ui.jsonl | 805 | PASS | 0 | 2 |

**A2UI 警告详情**：`switch` 和 `dropdown` 类型不在 A2UI 标准类型列表中（仅支持 button/card/column/container/image/input/list/row/stack/text）。

### 3.3 代码内容特征

Phase 1 的代码是**简洁的设置页骨架**：
- Android XML: LinearLayout + TextView + Switch + Spinner + Button
- Android Compose: SettingsScreen() 含 darkMode/notifications 开关 + Save 按钮
- Qt QML: ApplicationWindow + ColumnLayout + Switch + ComboBox + Button
- Windows HTML: 自包含 HTML，含 CSS toggle-switch 组件
- A2UI: 9 个节点的 JSONL（root → title/row_dark/row_lang/btn_save）

### 3.4 额外产物

`e2e_test/llm_generated_android_xml.txt` — 一个更完整的 Android XML 版本（134 行），含：
- notifications/dark mode/auto-sync 三个开关
- language Spinner
- Material Design 组件（SwitchMaterial, MaterialButton）
- 分割线 View

---

## 四、Phase 2: LLM 视觉生成 (2026-09-01 17:00-20:15)

### 4.1 源截图

- 截图来源: **ADB 200.47.91.1**（Android 设备截屏）
- 截图内容: **Android 设置 - 声音与显示页面**
- 原始截图: `e2e_demo/screenshots/run_20260901/source_screenshot.png`（5,847,934 bytes = 5.8MB）
- 压缩版本:
  - `source_screenshot_1024.png`（654KB，1024px 宽）
  - `source_screenshot_768.jpg`（50KB，768×432 JPEG，base64 ~65KB）

### 4.2 UI 描述（LLM 视觉分析结果）

从 `ui_description.json` 提取的截图内容：

- **主题**: light，主色 #1677ff，背景 #f5f5f5
- **标题**: 设置 - 声音与显示
- **布局**: 水平布局（侧边栏 + 内容区）
- **侧边栏**: 搜索框 + 导航列表（企业服务配置/声音与显示/摄像机/壁纸/Wi-Fi/智慧功能/高级设置）
- **内容区组件**:
  - 扬声器开关（开启）
  - 音量滑块（带喇叭图标）
  - 提示音量滑块
  - 按键音开关（开启）
  - 麦克风开关（关闭）
  - 亮度滑块（带太阳图标）

### 4.3 生成过程

| 步骤 | 时间 | 模型 | Token (in/out) | 费用 | 结果 |
|------|------|------|----------------|------|------|
| 1. 模型测试 | 17:02 | seed-2-1-turbo | 48+96 | ¥0.0004 | 唯一可用模型确认 |
| 2. 旧 Key 尝试 | 17:08-17:19 | — | 0 | ¥0 | 8×403 欠费 + 1×timeout |
| 3. 新 Key 测试 | 18:10 | seed-2-1-turbo | ~600 | ¥0.007 | 4 个模型可用确认 |
| 4. 合并 5 栈生成 | 18:25-18:31 | seed-2-1-turbo | 900+26206 | ¥0.3958 | KOTLIN✅ XML✅ QML✅ HTML截断 A2UI缺失 |
| 5. A2UI 补充 | 18:55-19:10 | seed-2-1-turbo | 792+18467 | ¥0.2774 | A2UI ✅ |
| 6. HTML 补充 | 18:55-19:10 | seed-2-1-turbo | 814+11295 | ¥0.1721 | HTML ✅ |
| 7. validate_code | 19:15 | — | — | — | 5/5 ALL PASS |

**总计**: 27 次 API 调用（8 成功 / 19 失败），58,618 tokens，¥0.85

### 4.4 生成产物（e2e_demo/run_20260901/ 目录）

| 技术栈 | 文件 | 字符数 | validate_code | 编译验证 | 截图渲染 |
|--------|------|--------|---------------|----------|----------|
| Kotlin Compose | llm_android_compose.kt | 16,410 | PASS (0/0) | 40 imports, 1 @Composable | unified_kt_screenshot.png (22KB) |
| Android XML | llm_android_xml.xml | 16,533 | PASS (0/0) | 46 elements, aapt2 compile ✅ | unified_xml_screenshot.png (18KB) |
| Qt QML | llm_qt_qml.qml | 8,414 | PASS (0/0) | 4 imports, 59 properties | unified_qml_screenshot.png (10KB) |
| Windows HTML | llm_windows_html.html | 12,357 | PASS (0/0) | 36 CSS rules, 7 inputs | unified_html_screenshot.png (27KB) |
| A2UI JSONL | llm_a2ui.jsonl | 5,930 | PASS (0/0) | 37 nodes, 9 types | unified_a2ui_screenshot.png (28KB) |

### 4.5 编译验证补充（e2e_compile_report.json）

最终统一验证 `e2e_unified_report.json` 结果：
- Kotlin Compose: ✅ 通过（含 SoundDisplaySettings 函数）
- Android XML: ✅ 通过（aapt2 编译成功）
- Qt QML: ✅ 通过（ApplicationWindow 根元素，4 imports）
- Windows HTML: ❌ **validate_code 报 1 error**（Tag aside invalid, line 269）
- A2UI JSONL: ✅ 通过（37 行全部 JSON 合法，9 种类型覆盖）

### 4.6 代码内容特征

Phase 2 的代码是**完整的应用级设置页面**：

**Kotlin Compose** (`SoundDisplaySettings()`):
- 40 个 import（含 material.icons 的 VolumeUp/VolumeDown/BrightnessHigh/Search/Close）
- 主题色: PrimaryColor = #1677FF
- 状态: speakerEnabled, volume, tipVolume, keyToneEnabled, micEnabled, brightness
- 完整的 Material 3 组件：Surface, Switch, Slider, OutlinedTextField, Icon, IconButton

**Android XML**:
- 46 个元素，LinearLayout 根
- Material Design 组件：SwitchMaterial, MaterialButton
- 分割线、资源引用

**Qt QML**:
- 4 imports（含 QtQuick.Controls.Material）
- 70 个属性绑定
- ApplicationWindow + ColumnLayout + RowLayout

**Windows HTML**:
- 自包含 HTML，lang="zh-CN"
- 36 条 CSS 规则
- 7 个 input 元素 + 1 个 button
- CSS 类: settings-card, setting-row, toggle, slider, save-btn

**A2UI JSONL**:
- 37 个节点
- 9 种类型: button, card, column, container, image, input, list, row, text
- 完整的父子引用链（无孤立节点）
- switch 和 dropdown 映射为 input 类型（inputType: "switch" / "range"）

---

## 五、四轮对比分析

### 5.1 复杂度对比

| 维度 | Phase 0 (首次 LLM) | Phase 1 (模板对照) | Phase 2 (LLM 视觉) | Phase 3 (深度验证) |
|------|-------------------|-------------------|-------------------|-------------------|
| 截图来源 | captures/settings_page | captures/settings_page | ADB 真实设备截屏 | 复用 Phase 2 截图 |
| UI 组件数 | ~5 个 | ~5 个 | ~12 个 | ~12 个 |
| 代码总字符 | ~10,650 | ~10,780 | ~59,644 | +8,133 (WinUI3) |
| Token 消耗 | 8,346 | ~8,346 | 58,618 | — (验证不生成) |
| 技术栈数 | 6（含 WPF） | 6（含 WPF） | 5（无 WPF） | 4+WinUI3 |
| 验证深度 | L1+L2+L3 | L1+L2+L3 | L1+L2+L3+L4(部分) | 深度结构+aapt2+设备 |
| 截图渲染 | Playwright 6 张 | Playwright 6 张 | Edge headless 5 张 | Edge 4张+设备1张 |
| APK 构建 | ✅ 手动 7KB | — | ✅ Gradle 15MB | — |
| 设备部署 | ✅ TEQU-S2C | — | ✅ 200.47.91.1 | ✅ XML 设备渲染 |
| WinUI3 | — | — | — | ✅ settings_page.xaml |

### 5.2 关键演进时间线

1. **Phase 0 → Phase 1**: 同一截图，Phase 0 是 LLM 生成版（e2e_demo/ 根），Phase 1 是模板对照版（e2e_test/），两者对照验证 LLM 生成质量
2. **Phase 0/1 → Phase 2**: 截图来源升级（模拟 → ADB 真实设备），LLM 模型升级（seed-evolving → seed-2-1-turbo），代码丰富度大幅提升
3. **APK 构建升级**: Phase 0 手动构建（aapt2→kotlinc→d8→apksigner，7099 bytes）→ Phase 2 Gradle 构建（assembleDebug，15MB）
4. **验证体系升级**: Phase 0 L1-L4 验证 → Phase 2 L1-L4 + aapt2 compile + Edge headless 截图 + Compose 推包到设备

### 5.3 持续存在的问题

1. **A2UI 类型系统**: `switch`/`dropdown`/`slider` 不在标准类型中，Phase 1 有 warning，Phase 2 通过映射为 `input` 类型解决
2. **HTML 解析**: Phase 2 的 HTML 在 compile_report 中出现 `aside` 标签解析错误（validate_code 通过但深度验证失败）
3. **模型可用性**: 火山引擎 15 个已开通模型中仅 1 个可用，其余均 404（endpoint 未创建）
4. **L4 编译缺口**: MSBuild（LOLBin 阻止）、aapt2（Phase 2 已补上）、Qt SDK（未安装）、Compose runtime（未配置）

---

## 六、文件索引

### Phase 0 产物（e2e_demo/ 根目录）
```
e2e_demo/
├── llm_android_xml.xml             # Android XML (1553 chars)
├── llm_android_compose.kt          # Kotlin Compose (2209 chars)
├── llm_qt_qml.qml                  # Qt QML (1353 chars)
├── llm_windows_html.html           # Windows HTML (2961 chars)
├── llm_windows_wpf.xaml            # Windows WPF (2034 chars)
├── llm_a2ui.jsonl                  # A2UI JSONL (943 chars)
├── raw_output.txt                  # LLM 原始输出 (284 行, ===SEP=== 分隔)
├── test_report.json                # 测试报告 (8346 tokens, 6/6 PASS)
├── validation_report.json          # 验证报告 (6/6 PASS, A2UI 3 warnings)
├── final_test_report.md            # 最终测试报告
├── compilation_report.md           # L1-L4 编译验证报告
├── kotlin_compile_test.kt          # 纯 Kotlin 编译验证文件
├── render_screenshots.cjs          # Playwright 截图渲染脚本
├── render_kotlin_output.cjs        # Kotlin 运行效果渲染
├── render_ui_effects.cjs           # UI 效果渲染
├── android_app/                    # Phase 0 APK 构建产物
│   ├── AndroidManifest.xml
│   └── build/ (classes.dex, base.apk, etc.)
└── screenshots/                    # 6 张 Playwright 渲染截图
    ├── a2ui.png, android_compose.png
    ├── android_xml.png, qt_qml.png
    ├── windows_html.png, windows_wpf.png
    └── (运行效果截图: *_run.png, kotlin_run_output.png)
```

### Phase 1 产物（e2e_test/）
```
e2e_test/
├── final_report.json              # 验证汇总
├── validation_results.json        # 详细验证结果
├── settings_android_xml.xml       # Android XML 代码
├── settings_android_compose.kt    # Kotlin Compose 代码
├── settings_qt_qml.qml            # Qt QML 代码
├── settings_windows_win32.html    # Windows HTML 代码
├── settings_a2ui.jsonl            # A2UI JSONL 代码
├── llm_generated_android_xml.txt  # LLM 生成的完整 Android XML
└── final_report.json              # 6/6 栈验证通过
```

### Phase 2 产物（e2e_demo/run_20260901/）
```
e2e_demo/run_20260901/
├── llm_android_compose.kt         # Kotlin Compose (16410 chars)
├── llm_android_xml.xml            # Android XML (16533 chars)
├── llm_qt_qml.qml                 # Qt QML (8414 chars)
├── llm_windows_html.html          # Windows HTML (12357 chars)
├── llm_a2ui.jsonl                 # A2UI JSONL (5930 chars)
├── ui_description.json            # LLM 视觉分析结果
├── generation_report.json         # 生成报告（含 token/费用）
├── validation_report.json         # 5/5 验证通过
├── e2e_compile_report.json        # 编译验证报告
├── e2e_unified_report.json        # 统一报告（含截图渲染）
├── e2e_5stack_report.html         # HTML 可视化报告
├── e2e_compile_report.html        # HTML 编译报告
├── e2e_unified_report.html        # HTML 统一报告
├── a2ui_preview.html              # A2UI 预览
├── compose_approximate.html       # Compose 近似渲染
├── xml_approximate.html           # XML 近似渲染
├── qml_approximate.html           # QML 近似渲染
├── unified_kt_screenshot.png      # Kotlin 截图
├── unified_xml_screenshot.png     # XML 截图
├── unified_qml_screenshot.png     # QML 截图
├── unified_html_screenshot.png    # HTML 截图
├── unified_a2ui_screenshot.png    # A2UI 截图
├── render_html_screenshot.png     # HTML 渲染截图
└── render_a2ui_screenshot.png     # A2UI 渲染截图
```

### 源截图
```
e2e_demo/screenshots/run_20260901/
├── source_screenshot.png           # 原始截图 (5.8MB)
├── source_screenshot_1024.png      # 1024px 压缩版 (654KB)
├── source_screenshot_768.jpg       # 768px JPEG 压缩版 (50KB)
└── source_b64.txt                 # base64 编码 (67KB)
```

### 相关报告
```
e2e_demo/
├── ark_api_log.md                  # Ark API 调用完整日志
├── model_test_results.json         # 15 个模型可用性测试
├── test_report.json                # Phase 1 测试报告
├── validation_report.json          # Phase 1 验证报告
├── validate_code_results.json      # Phase 1 代码验证结果
├── final_test_report.md            # Phase 1 最终测试报告
├── compilation_report.md           # 编译验证报告
└── e2e_full_validation_report.html # 完整验证报告 HTML
```

### 生成脚本
```
backend/
├── generate_5stacks.py             # 5 栈生成脚本（独立调用版）
├── generate_5stacks_combined.py    # 5 栈生成脚本（合并调用版）
├── generate_a2ui_html.py           # A2UI 转 HTML
├── gen_a2ui_html.py                # A2UI 转 HTML（简化版）
├── run_5stacks.py                  # 5 栈运行脚本
├── validate_5stacks.py             # 5 栈验证脚本
├── validate_5stacks_v2.py          # 5 栈验证脚本 v2
└── ws_generate_client.py           # WebSocket 生成客户端
```
