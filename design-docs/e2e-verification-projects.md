# 端到端验证项目调研：Qt/QML · Kotlin/Compose · Android XML · A2UI · WinUI3

> 调研日期：2026-09-01  
> 目标：为 fork 的 `validate_code.py`（6 栈轻量验证器）和 `e2e_compile_verify.py`（端到端编译+截图管线）寻找业界优秀 demo / 开源项目，补充每栈的"渲染验证 + 参考实现"能力。

---

## 0. 当前 E2E 验证管线现状

### 0.1 已有的验证能力

| 验证层 | 实现位置 | 能力 | 缺口 |
|---|---|---|---|
| **语法验证** | `backend/agent/tools/validate_code.py` | 6 栈结构检查（HTML/XML/QML/Compose/A2UI/WPF） | 无编译，无运行时验证 |
| **编译验证** | `e2e_demo/run_20260901/e2e_compile_report.json` | 5 栈全部 PASS | 仅验证 LLM 产出代码的语法正确性 |
| **截图渲染** | `render_screenshots.cjs` + Edge headless | HTML + A2UI 已截图 | QML / Compose / Android XML 截图靠手动 |
| **ADB 截图** | `backend/capture/` + `backend/routes/adb.py` | 真机截屏 + UI Automator | 需设备在线，Gradle 构建未打通 |

### 0.2 5 栈 E2E 验证矩阵

| 栈 | 语法验证 | 编译验证 | 截图渲染 | 视觉回归 | 参考实现 |
|---|---|---|---|---|---|
| HTML/CSS | ✅ validate_code | ✅ Edge headless | ✅ `--screenshot` | ❌ | 需补充 |
| A2UI JSONL | ✅ validate_code | ✅ JSONL→HTML | ✅ Edge headless | ❌ | 需补充 |
| Qt QML | ✅ validate_code | ⚠️ 需 qmlscene | ⚠️ 需 qmlscenegrabber | ❌ | 需补充 |
| Android Compose | ✅ validate_code | ⚠️ 需 Gradle | ❌ 需 Compose Driver / Paparazzi | ❌ | 需补充 |
| Android XML | ✅ validate_code | ⚠️ 需 Gradle | ❌ 需设备/Robolectric | ❌ | 需补充 |
| WinUI3 | ❌ 未实现 | ❌ 需 WinAppSDK | ❌ | ❌ | 需补充 |

---

## 1. Qt/QML 栈

### 1.1 参考实现项目

#### QML Snippets Examples
- **仓库**：`github.com/JesusRamosMembrive/QML-SnippetsExamples`
- **License**：MIT
- **技术栈**：Qt 6.4+, CMake, GitHub Actions CI
- **内容**：66 个 QML 组件实现，涵盖 HUD、PFD（Primary Flight Display）、ECAM、着色器、3D 图表
- **复用价值**：
  - 作为 LLM 生成 QML 代码的 golden reference — 可提取典型组件模式（Button/Slider/ListView）
  - CMake 构建配置可直接参照用于 `e2e_compile_verify.py` 的 QML 编译验证
  - GitHub Actions workflow 展示了 headless QML CI 的完整配置
- **集成点**：提取 5-10 个经典组件（Button、Column/Row Layout、ScrollView、Switch、Slider）作为 QML system prompt 的 few-shot 示例

#### Qt 官方示例
- **来源**：Qt 安装目录 `Examples/Qt-*/quick/` 或 [Qt Examples](https://doc.qt.io/qt-6/qtexamples.html)
- **关键示例**：
  - `quick/controls/` — 全套 Material/Universal 控件演示
  - `quick/layouts/` — ColumnLayout/RowLayout/GridLayout 使用
  - `quick/views/` — ListView/GridView/PathView 数据绑定
- **复用价值**：作为 QML system prompt 中控件使用规范的权威参考

### 1.2 Headless 渲染验证

#### Qt Lancelot Graphics Testing
- **文档**：[Qt Baseline Testing](https://doc.qt.io/qt-6/qtbaseline-testing.html)
- **工具**：`qmlscenegrabber` — Qt 自带的 QML 场景截图工具
- **核心命令**：
  ```bash
  # 离屏模式渲染 QML 场景（CI 环境，无需显示器）
  export QT_QPA_PLATFORM=offscreen
  qmlscenegrabber -o screenshot.png scene.qml

  # 对比基线截图
  qmlscenegrabber -o actual.png scene.qml
  # Lancelot 自动对比 actual.png vs baseline.png
  ```
- **集成到 `e2e_compile_verify.py`**：
  ```python
  # QML 栈：qmlscenegrabber 截图
  def render_qml_screenshot(qml_file: str, output_png: str) -> bool:
      env = os.environ.copy()
      env["QT_QPA_PLATFORM"] = "offscreen"
      result = subprocess.run(
          ["qmlscenegrabber", "-o", output_png, qml_file],
          env=env, capture_output=True, timeout=30
      )
      return result.returncode == 0 and os.path.exists(output_png)
  ```
- **前提**：本机需安装 Qt 6.x（`qmlscenegrabber` 在 `bin/` 目录下）
- **降级方案**：若 Qt 未安装，跳过截图，仅保留语法验证

#### QML TestCase.grabImage()
- **文档**：[Qt Test QML Types](https://doc.qt.io/qt-6/qttest-qmltest.html)
- **用法**：在 QML 单元测试中直接截图
  ```qml
  import QtTest 1.0

  TestCase {
      name: "SettingsRenderTest"
      function test_render() {
          var image = grabImage()
          image.save("/tmp/settings_screenshot.png")
          verify(image.width > 0)
      }
  }
  ```
- **运行**：`QMLTEST_RUNNER=qmltestrunner` 或 `qmltestrunner -input test.qml`
- **复用价值**：不需要额外工具，纯 QML 内嵌测试即可截图

#### MCP QML Server（社区项目）
- **来源**：Qt 邮件列表讨论中的社区项目
- **架构**：WebSocket-based QML introspection server
- **工具集**：
  - `qml_snapshot` — 获取 QML 对象树
  - `qml_screenshot` — 截取当前 QML 渲染画面
  - `qml_get_property` / `qml_set_property` — 动态属性读写
- **复用价值**：长期方向 — 让 AI agent 直接驱动 QML 应用进行交互测试（类似 Compose Driver 的 QML 版）
- **当前状态**：概念阶段，无公开仓库，需持续关注

### 1.3 QML 栈集成建议

| 优先级 | 措施 | 预期效果 |
|---|---|---|
| **P0** | `qmlscenegrabber` + `QT_QPA_PLATFORM=offscreen` 集成到 `e2e_compile_verify.py` | QML 栈获得自动截图能力 |
| **P1** | 从 QML Snippets Examples 提取 5-10 个组件作为 golden reference | 提升 LLM 生成 QML 的控件使用准确率 |
| **P2** | `TestCase.grabImage()` 写 QML 单元测试 | 细粒度组件级截图验证 |

---

## 2. Kotlin/Compose 栈

### 2.1 参考实现项目

#### Compose Driver（⭐ 直接复用）
- **仓库**：`github.com/jdemeulenaere/compose-driver` (Apache 2.0, v0.5.0)
- **核心价值**：HTTP Server 包装 `ComposeUiTest`，通过 REST API 驱动 Compose UI
- **API 端点**：
  - `GET /screenshot` → 截图
  - `POST /click` → 点击
  - `POST /swipe` → 滑动
  - `GET /printTree` → 语义树
- **关键优势**：Android 走 Robolectric（无需模拟器），Desktop 走 JVM — **绕过 fork 的 Gradle/AGP 兼容性问题**
- **集成代码**（`settings.gradle.kts`）：
  ```kotlin
  include("compose-driver")
  project(":compose-driver").projectDir = 
      file("../compose-driver/driver")
  ```
- **集成到 `e2e_compile_verify.py`**：
  ```python
  # Compose 栈：Compose Driver 截图
  def render_compose_screenshot(kt_file: str, output_png: str) -> bool:
      # 1. 启动 Compose Driver server（后台）
      # 2. POST /load → 加载 @Preview Composable
      # 3. GET /screenshot → 保存截图
      import requests
      resp = requests.get(
          "http://localhost:8080/screenshot",
          params={"preview": "SoundDisplaySettings"}
      )
      with open(output_png, "wb") as f:
          f.write(resp.content)
      return os.path.exists(output_png)
  ```

#### ComposablePreviewScanner（⭐ 自动发现 @Preview）
- **仓库**：`github.com/sergio-sastre/ComposablePreviewScanner`
- **核心价值**：ClassGraph 字节码扫描，自动发现所有 `@Preview` 注解的 Composable
- **月下载量**：300K+，已被 Roborazzi 集成为核心依赖
- **Glance 支持**：`GlanceComposablePreviewScanner` — 直接适配 fork 的 Glance Widget 场景
- **集成到 AGenUI**：
  ```kotlin
  // 自动扫描所有 @Preview 函数
  val previews = scanGlancePreviews()
  previews.forEach { preview ->
      // 截图 + 对比
  }
  ```

#### sound-source-player（设置 UI 参考）
- **仓库**：`github.com/roll-w/sound-source-player`
- **内容**：完整的 Compose 设置界面，使用 `PlayerTheme` 系统
- **复用价值**：
  - 声明式 preference DSL — 可作为 LLM 生成设置界面的 golden reference
  - `ContentTypography` + `FontUnit` 系统 — Compose 字体管理的最佳实践
  - 当前 fork 的 `e2e_test/settings_android_compose.kt` 已参考此项目

#### android-showcase（Material 3 参考实现）
- **仓库**：`github.com/igorwojda/android-showcase` (MIT, ~2k stars)
- **技术栈**：Kotlin, AGP 8.0, Android SDK 34, Material Design 3
- **复用价值**：
  - 20+ Material 3 组件的完整 Compose 实现
  - **AGP 8.0 + SDK 34** — 与 fork 的 Gradle 构建配置兼容，可作为编译验证的基准项目
  - `build.gradle.kts` 配置可直接参照解决 fork 的 AGP/Gradle 版本冲突

### 2.2 截图验证工具

#### Paparazzi（⭐ 纯 JVM 截图）
- **仓库**：`github.com/cashapp/paparazzi` (Apache 2.0, ~2.1k stars)
- **核心价值**：纯 JVM 运行 Compose 截图，通过 Layoutlib 模拟 Android 渲染
- **性能**：~2s/截图，CI 友好
- **Gradle 任务**：
  ```bash
  ./gradlew recordPaparazziDebug   # 记录基线截图
  ./gradlew verifyPaparazziDebug   # 对比基线截图
  ```
- **集成优势**：不需要 Android SDK/模拟器 — 与 Compose Driver 互补
  - Compose Driver → 交互测试（点击/滑动）
  - Paparazzi → 像素级回归测试

#### Roborazzi（⭐ AI 增强截图对比）
- **仓库**：`github.com/takahirom/roborazzi` (Apache 2.0, ~680 stars)
- **核心价值**：基于 Robolectric 的截图测试 + **AI-Powered Image Assertion**
- **AI 对比能力**：
  - 截图不同时，调用 LLM 进行视觉断言
  - 支持 Gemini / OpenAI
  - 可自定义 `AiAssertionModel` 接口 → 接入火山引擎 doubao
- **自定义 doubao 模型**：
  ```kotlin
  class DoubaoAssertionModel : AiAssertionModel {
      override suspend fun assert(
          expected: BufferedImage,
          actual: BufferedImage,
          prompt: String
      ): Boolean {
          // 调用火山引擎 Ark API
          // POST https://ark.cn-beijing.volces.com/api/v3/chat/completions
          // model: doubao-seed-2-1-turbo-260628
          // 传入两张图 + 断言 prompt
      }
  }
  ```
- **集成优先级**：P1 — 在 Paparazzi 基线截图的基础上增加语义级验证

#### Shot（需设备/模拟器）
- **仓库**：`github.com/pedrovgs/shot` (Apache 2.0, ~1.5k stars)
- **定位**：Android 截图测试 Gradle 插件，5.0.0+ 支持 Compose
- **限制**：需要设备或模拟器 — 在 fork 的受限环境中不推荐优先使用
- **优势**：HTML diff 报告直观，适合最终验收阶段

### 2.3 Compose 栈集成建议

| 优先级 | 措施 | 预期效果 |
|---|---|---|
| **P0** | Compose Driver 集成 → `e2e_compile_verify.py` | Compose 栈获得自动截图能力，绕过 Gradle |
| **P0** | ComposablePreviewScanner → AGenUI Glance | 自动发现 @Preview，批量截图 |
| **P1** | Paparazzi 集成 → 像素级回归测试 | 检测 LLM 生成代码的视觉退化 |
| **P1** | 从 android-showcase 提取 M3 组件模板 | 提升 Compose system prompt 质量 |
| **P2** | Roborazzi AI assertion + doubao 模型 | 语义级截图对比 |

---

## 3. Android XML 栈

### 3.1 参考实现项目

#### android-showcase（Material 3 XML 参考）
- **仓库**：`github.com/igorwojda/android-showcase` (MIT)
- **技术栈**：Kotlin, AGP 8.0, Android SDK 34, Material Design 3
- **XML 价值**：`res/layout/` 下的 M3 风格 XML 布局
- **构建兼容性**：**AGP 8.0 + SDK 34** — 与 fork 的 `e2e_demo/android_project/` 配置对齐
- **复用点**：
  - `build.gradle.kts` 可作为 fork Android XML 编译验证的配置基准
  - Material 3 主题/颜色/字体定义可直接参照

#### cheesesquare（Material Design 经典 demo）
- **仓库**：`github.com/chrisbanes/cheesesquare`
- **内容**：Google Design Support Library 的官方 demo
- **复用价值**：`CoordinatorLayout` + `AppBarLayout` + `CollapsingToolbarLayout` + `FloatingActionButton` 的经典 XML 实现
- **适用场景**：作为 LLM 生成 Android XML 的 Material Design 参考

#### MaterialDesign 项目
- **仓库**：`github.com/yechaoa/MaterialDesign`
- **内容**：20+ Material Design 3 组件的完整 XML + Kotlin 实现
- **复用价值**：每个组件都有 `res/layout/*.xml` — 可提取为 Android XML system prompt 的 few-shot 示例

### 3.2 截图验证工具

#### Layoutlib + Robolectric（纯 JVM）
- **原理**：Android SDK 的 Layoutlib 库可在 JVM 上模拟 View 渲染
- **工具**：`utils/layoutlib`（Android SDK 自带）
- **使用**：
  ```bash
  # 通过 Robolectric 在 JVM 上渲染 XML 布局
  ./gradlew recordRoborazziDebug
  ```
- **优势**：不需要设备/模拟器，CI 友好
- **限制**：部分自定义 View 渲染可能不一致

#### ADB + 设备截图（fork 已有基础设施）
- **现有能力**：`backend/capture/` + `backend/routes/adb.py`
- **流程**：
  1. `adb install settings.apk`
  2. `adb shell am start -n com.e2e.settings/.MainActivity`
  3. `adb exec-out screencap -p > screenshot.png`
- **当前断点**：Gradle 构建未打通（APK 未生成）
- **建议**：优先解决 Gradle 版本兼容，再启用 ADB 截图

### 3.3 Android XML 栈集成建议

| 优先级 | 措施 | 预期效果 |
|---|---|---|
| **P0** | 从 android-showcase 提取 `build.gradle.kts` 配置 | 解决 fork 的 AGP/Gradle 版本冲突 |
| **P1** | Robolectric + Layoutlib 渲染 XML 布局 | 无需设备的 XML 截图验证 |
| **P1** | 从 MaterialDesign 项目提取 5-10 个组件模板 | 提升 Android XML system prompt 质量 |
| **P2** | ADB 设备截图（依赖 Gradle 打通） | 真机渲染验证 |

---

## 4. A2UI 栈

### 4.1 协议与工具

#### A2UI 官方协议
- **官网**：[a2ui.org](https://a2ui.org)
- **License**：Apache 2.0
- **版本**：v0.8（稳定）→ v0.9（当前）→ v1.0（候选，2026 Q4）
- **核心规范**：
  - 声明式 JSON，非可执行代码
  - 扁平邻接表结构（flat adjacency list）— LLM 友好
  - 流式 JSONL 格式
  - 节点类型：`container` / `column` / `row` / `text` / `button` / `input` / `card` / `image` / `list`

#### 已有渲染器
| 渲染器 | 框架 | 状态 | 适用场景 |
|---|---|---|---|
| **Lit** | Web Components | ✅ 可用 | 浏览器预览（fork 当前使用） |
| **Angular** | Angular | ✅ 可用 | Angular 项目集成 |
| **Flutter** | Flutter | ✅ 可用 | 跨平台渲染 |
| React | React | 🗓️ 路线图 | 未来 |
| SwiftUI | SwiftUI | 🗓️ 路线图 | 未来 |
| Compose | Jetpack Compose | 🗓️ 路线图 | 未来（与 fork 高度相关） |

#### Composer（可视化编辑器）
- **功能**：A2UI JSONL 的可视化编辑器，所见即所得
- **复用价值**：可用来手动验证 LLM 生成的 A2UI JSONL — 在 Composer 中加载，目视检查布局

#### Theater（playground）
- **功能**：A2UI 协议的在线 playground
- **复用价值**：快速验证 A2UI JSONL 的正确性

### 4.2 fork 现有 A2UI 验证

#### 当前实现
- **语法验证**：`validate_code.py` 的 `_validate_a2ui()` — 逐行 `json.loads()` + 结构检查
- **渲染截图**：`render_a2ui_screenshot.png` — JSONL → HTML → Edge headless 截图
- **5 栈验证结果**：37 行 JSONL，37/37 解析成功，9 种节点类型

#### 当前验证覆盖
```json
{
  "json_parse": { "total_lines": 37, "parsed_count": 37, "errors": [], "ok": true },
  "type_coverage": { "types_used": ["button","card","column","container","image","input","list","row","text"], "count": 9, "ok": true },
  "parent_chain": { "total_ids": 37, "orphan_parents": [], "ok": true }
}
```

### 4.3 A2UI 栈集成建议

| 优先级 | 措施 | 预期效果 |
|---|---|---|
| **P0** | 对齐 A2UI v0.9 schema 规范 | 确保生成的 JSONL 符合最新协议 |
| **P1** | 集成 Lit 渲染器作为标准渲染层 | 替换当前手写 HTML 转换，使用官方渲染器 |
| **P1** | Theater playground URL 验证 | 在线快速验证 A2UI 正确性 |
| **P2** | 关注 Compose renderer 发布 | A2UI → Compose 自动渲染（与 fork 主栈对齐） |

---

## 5. WinUI3 栈

### 5.1 参考实现项目

#### WinUI 3 Gallery（⭐ 官方控件百科）
- **仓库**：`github.com/microsoft/WinUI-Gallery`
- **License**：MIT
- **技术栈**：.NET 10, WinUI 3, `slnx` 解决方案格式
- **核心价值**：
  - 所有 WinUI 3 控件的交互式演示 — 每个 XAML 控件的 canonical 实现
  - 源码可直接参考 — 每个 demo 页面就是一个完整的 XAML + C# code-behind
  - 控件分类：按钮、输入、列表、导航、对话框、图表、图标
- **复用点**：
  - 提取常用控件的 XAML 片段作为 WinUI3 system prompt 的 few-shot 示例
  - 作为 WinUI3 栈的"golden reference" — LLM 生成的 XAML 应与 Gallery 风格一致

#### Windows App SDK Samples
- **仓库**：`github.com/microsoft/WindowsAppSDK-Samples`
- **License**：MIT
- **内容**：Windows App SDK 各功能的端到端示例
- **复用价值**：
  - 包含 WinUI 3 的完整应用架构模式（MVVM、导航、数据绑定）
  - `csproj` / `slnx` 配置参考 — 为 fork 的 WinUI3 编译验证提供构建配置基准
  - MSIX 打包示例

#### Windows Community Toolkit
- **仓库**：`github.com/CommunityToolkit/Windows`
- **License**：MIT
- **内容**：WinUI 3 社区扩展控件库
- **复用价值**：
  - 补充 WinUI 3 原生控件不足的部分（如 `TokenizingTextBox`、`GridSplitter`）
  - 作为 WinUI3 system prompt 中"社区控件"部分的参考

### 5.2 WinUI3 验证方案

#### 语法验证（需新建）
- **当前状态**：`validate_code.py` 仅有 `windows_wpf` 栈，无 `winui3`
- **新建方案**（见 `winui3-and-token-optimization-plan.md`）：
  ```python
  # validate_code.py 新增
  Stack = Literal["html", "android_compose", "android_xml", "qt_qml", "a2ui", "windows_wpf", "winui3"]

  def _validate_winui3_xaml(code: str) -> tuple[List[ValidationIssue], List[ValidationIssue]]:
      # 1. 检查命名空间声明（Microsoft.UI.Xaml）
      # 2. 检查根元素（Window/Page/UserControl）
      # 3. XAML 标签平衡检查
      # 4. WinUI 3 控件白名单检查
  ```

#### 编译验证
- **工具**：`dotnet build` + WinUI 3 workload
- **前提**：需安装 .NET 10 SDK + Windows App SDK workload
- **命令**：
  ```bash
  dotnet build winui3_project/winui3_project.slnx -c Debug
  ```
- **CI 集成**：GitHub Actions 的 `windows-latest` runner 已预装 .NET SDK

#### 截图渲染
- **方案 A**：WinAppDriver + 截图
  ```csharp
  // 使用 WindowsApplicationDriver 截图
  var session = new WindowsDriver<WindowsElement>(new Uri("http://127.0.0.1:4723"), appCapabilities);
  var screenshot = session.GetScreenshot();
  screenshot.SaveAsFile("winui3_screenshot.png");
  ```
- **方案 B**：XAML Islands + 截图（更轻量）
  ```csharp
  // 使用 XAML Islands 在普通 WPF 应用中渲染 WinUI 3 XAML
  // 然后 WPF 截图机制截图
  ```
- **方案 C**：纯 XAML 解析验证（无运行时）
  - 类似当前 WPF 的做法 — 仅验证 XAML 结构正确性，不做运行时截图
  - **推荐作为初始版本**：先确保语法正确，截图作为 P2 功能

### 5.3 WinUI3 栈集成建议

| 优先级 | 措施 | 预期效果 |
|---|---|---|
| **P0** | `validate_code.py` 新增 `winui3` 栈 | XAML 语法验证 |
| **P0** | 从 WinUI Gallery 提取控件 XAML 模板 | WinUI3 system prompt few-shot |
| **P1** | `dotnet build` 编译验证 | XAML 编译时检查 |
| **P2** | WinAppDriver 截图 | 运行时渲染验证 |

---

## 6. 跨栈整合方案

### 6.1 推荐的 E2E 验证工具组合

| 验证层 | 工具 | 适用栈 | 依赖 |
|---|---|---|---|
| 语法验证 | `validate_code.py`（已有） | 全部 6 栈 | 无 |
| 编译验证 | 各栈原生编译器 | Compose→Gradle, QML→qmlscenegrabber, XML→aapt2, WinUI3→dotnet | 各栈 SDK |
| **截图渲染** | Edge headless（已有） | HTML, A2UI | 无 |
| | **qmlscenegrabber**（新） | QML | Qt 6.x |
| | **Compose Driver**（新） | Compose | JVM |
| | **Paparazzi**（新） | Compose 像素回归 | Gradle |
| | **Robolectric + Layoutlib**（新） | Android XML | JVM |
| | **WinAppDriver**（新） | WinUI3 | Windows |
| **视觉回归** | **Roborazzi AI assertion**（新） | Compose | LLM API |

### 6.2 统一截图接口设计

为 `e2e_compile_verify.py` 设计统一的截图接口：

```python
from typing import Protocol

class ScreenshotRenderer(Protocol):
    """各栈截图渲染器的统一接口"""
    def render(self, source_file: str, output_png: str) -> bool:
        """渲染源文件到 PNG 截图，返回是否成功"""
        ...

class EdgeRenderer(ScreenshotRenderer):
    """HTML / A2UI → Edge headless 截图（已有）"""
    def render(self, source_file: str, output_png: str) -> bool:
        # 已实现：render_screenshots.cjs
        ...

class QmlSceneGrabberRenderer(ScreenshotRenderer):
    """QML → qmlscenegrabber 截图（新）"""
    def render(self, source_file: str, output_png: str) -> bool:
        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "offscreen"
        result = subprocess.run(
            ["qmlscenegrabber", "-o", output_png, source_file],
            env=env, capture_output=True, timeout=30
        )
        return result.returncode == 0

class ComposeDriverRenderer(ScreenshotRenderer):
    """Compose → Compose Driver 截图（新）"""
    def render(self, source_file: str, output_png: str) -> bool:
        # 1. 启动 Compose Driver server
        # 2. POST /load → 加载 @Preview Composable
        # 3. GET /screenshot → 保存截图
        ...

class AndroidXmlRobolectricRenderer(ScreenshotRenderer):
    """Android XML → Robolectric/Layoutlib 截图（新）"""
    def render(self, source_file: str, output_png: str) -> bool:
        # 通过 Robolectric 在 JVM 上渲染 XML 布局
        ...
```

### 6.3 实施路线图

```
Phase 1 (P0 — 立即可做):
├── QML: qmlscenegrabber + offscreen 集成
├── Compose: Compose Driver REST API 截图
├── A2UI: 对齐 v0.9 schema + 官方 Lit 渲染器
├── WinUI3: validate_code 新增 winui3 栈
└── Compose: ComposablePreviewScanner → @Preview 自动发现

Phase 2 (P1 — 短期适配):
├── Compose: Paparazzi 像素级回归测试
├── Android XML: Robolectric + Layoutlib 渲染
├── 各栈: 从参考项目提取 few-shot 模板
├── WinUI3: dotnet build 编译验证
└── Android XML: 从 android-showcase 对齐 Gradle 配置

Phase 3 (P2 — 长期演进):
├── Compose: Roborazzi AI assertion + doubao 模型
├── WinUI3: WinAppDriver 截图
├── A2UI: 关注 Compose renderer 发布
├── QML: MCP QML Server → AI 驱动交互测试
└── 全栈: 视觉回归基线管理
```

---

## 7. 参考项目速查表

| 项目 | 栈 | License | Stars | 用途 |
|---|---|---|---|---|
| Compose Driver | Compose | Apache 2.0 | — | REST API 驱动 Compose 截图 |
| ComposablePreviewScanner | Compose | Apache 2.0 | — | 自动发现 @Preview |
| Paparazzi | Compose | Apache 2.0 | ~2.1k | 纯 JVM 截图 |
| Roborazzi | Compose | Apache 2.0 | ~680 | AI 增强截图对比 |
| Shot | Compose/XML | Apache 2.0 | ~1.5k | 设备截图测试 |
| QML Snippets Examples | QML | MIT | — | 66 个 QML 组件参考 |
| WinUI 3 Gallery | WinUI3 | MIT | — | 官方控件百科 |
| WindowsAppSDK-Samples | WinUI3 | MIT | — | 端到端示例 |
| Windows Community Toolkit | WinUI3 | MIT | — | 社区扩展控件 |
| android-showcase | XML/Compose | MIT | ~2k | M3 组件 + AGP 8.0 参考 |
| MaterialDesign | XML | — | — | 20+ M3 XML 组件 |
| cheesesquare | XML | — | — | Material Design 经典 |
| A2UI Protocol | A2UI | Apache 2.0 | — | 官方协议规范 |
| sound-source-player | Compose | — | — | 设置 UI DSL 参考 |

---

## 8. 与 reuse-reference-report.md 的关系

本文档聚焦**每栈的具体验证工具和参考实现**，是 `reuse-reference-report.md`（聚焦跨栈复用的架构级项目）的补充：

| 维度 | reuse-reference-report.md | 本文档 |
|---|---|---|
| 视角 | 架构级复用（Compose Driver、micro-agent 等） | 每栈的具体验证工具和 demo |
| 粒度 | 12 个项目，P0-P3 优先级 | 5 栈 × 3-5 个项目/工具 |
| 落地点 | fork 的整体架构演进 | `e2e_compile_verify.py` 的逐栈增强 |
| 互补 | Compose Driver 在两份报告中都出现 — 它既是架构级复用也是具体截图工具 |

两份报告合在一起，构成 fork 端到端验证的完整调研基础。
