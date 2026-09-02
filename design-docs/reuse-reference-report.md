# 业界开源项目复用参考报告

> 调研日期：2026-09-01
> 目标：从调研项目中筛选出可直接复用 / 需适配 / 长期参考的方案，给出文件级集成点

---

## 1. 项目总览（新增 + 已有）

| # | 项目 | 类型 | 与本 Fork 的关系 | 复用等级 |
|---|---|---|---|---|
| 1 | **Compose Driver** | AI ↔ Compose 交互 | 直接复用：HTTP 驱动 Compose 预览 | ⭐⭐⭐ 立即 |
| 2 | **ComposablePreviewScanner** | @Preview 自动截图测试 | 直接复用：Glance Widget 截图验证 | ⭐⭐⭐ 立即 |
| 3 | **Paparazzi** (Square) | JVM Compose 截图测试 | 适配后复用：替代 ADB 真机截屏 | ⭐⭐ 短期 |
| 4 | **Roborazzi** | Robolectric 截图 + AI 断言 | 适配后复用：AI 视觉验证闭环 | ⭐⭐ 短期 |
| 5 | **Shot** (pedrovgs) | Android 截图测试 Gradle 插件 | 参考：record/verify 工作流 | ⭐ 参考 |
| 6 | **micro-agent** (BuilderIO) | TDD + 视觉匹配循环 | 架构参考：生成→测试→截图对比→迭代 | ⭐⭐ 架构 |
| 7 | **FigmaToCode** | Figma → 多栈代码 | 架构参考：AltNode IR 中间表示 | ⭐⭐ 架构 |
| 8 | **Flame-Code-VLM** | 专用 VLM 截图→代码 | 长期参考：训练 fork 专用模型 | ⭐ 长期 |
| 9 | **figma-to-compose** (LobeHub) | Figma → Compose MCP Skill | 参考：icon→VectorDrawable 管线 | ⭐ 参考 |
| 10 | **implement-page-android** (AGMO) | 多帧 Figma→Compose | 参考：frame 拆分 + 视觉验证循环 | ⭐ 参考 |
| 11 | **Android Gemini Generate UI** | 官方截图→Compose | 竞品参考：Android Studio 原生能力 | ⭐ 竞品 |
| 12 | **TRIM / Text-or-Pixels** | VLM token 优化 | 已实现：T1 压缩 + T4 截断 + T5 历史 | ✅ 已落地 |

---

## 2. 直接复用项目（⭐⭐⭐ 立即集成）

### 2.1 Compose Driver — AI Agent 的 Compose "眼睛和手"

**仓库**：https://github.com/jdemeulenaere/compose-driver
**协议**：Apache 2.0 | **版本**：0.5.0 (2026-02) | **Stars**：~562

**核心机制**：
- Gradle Settings Plugin 自动创建 `:compose-driver-android` / `:compose-driver-desktop` 子项目
- 将 Composable 包裹在 `ComposeUiTest` 测试 harness 中
- 启动内嵌 HTTP Server (localhost:8080)，将 HTTP 请求翻译为 `ComposeUiTest` 动作
- Android 走 Robolectric，Desktop 走 JVM，**均无需模拟器/设备**

**API 端点**：
| 类别 | 端点 | 功能 |
|---|---|---|
| 观测 | `/screenshot` | 截取目标节点或根节点 PNG |
| 观测 | `/printTree` | 输出语义节点树文本 |
| 观测 | `/waitForNode` | 等待节点出现 |
| 交互 | `/click` `/doubleClick` `/longClick` | 点击/双击/长按 |
| 交互 | `/textInput` `/textReplacement` `/textClearance` | 文本输入 |
| 手势 | `/swipe` `/pointerInput/*` | 滑动/指针事件 |
| 生命周期 | `/reset` | 切换 Composable |
| 可观测性 | `gifDurationMs` 参数 | 录制 GIF（需 ffmpeg） |

**本 Fork 集成点**：

| 集成位置 | 用途 | 改动量 |
|---|---|---|
| `e2e_demo/android_project/settings.gradle.kts` | 添加 compose-driver 插件 | +3 行 |
| `backend/e2e_compile_verify.py` | 生成 Compose 代码后启动 Driver → `/screenshot` 截图 | +50 行 Python |
| `backend/routes/adb.py` | 作为 ADB 真机截屏的 JVM 降级方案 | 新增 route |

**集成代码示例**：
```kotlin
// settings.gradle.kts
plugins {
    id("io.github.jdemeulenaere.compose.driver") version "0.5.0"
}
composeDriver {
    android {
        robolectric {
            sdk = 34
            qualifiers = "w410dp-h920dp-xhdpi"
        }
    }
}
```

```python
# e2e_compile_verify.py 中新增
def compose_driver_screenshot(composable_class: str, output_path: str):
    """启动 Compose Driver，截图，返回 PNG 路径"""
    import subprocess, time, requests
    # 1. 启动 driver
    proc = subprocess.Popen(
        ["./gradlew", ":compose-driver-android:run",
         f"-Dcompose.driver.composable={composable_class}"],
        cwd=ANDROID_PROJECT_DIR,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    # 2. 等待 server 就绪
    for _ in range(30):
        try:
            r = requests.get("http://localhost:8080/status", timeout=1)
            if r.text.strip() == "ok":
                break
        except:
            time.sleep(1)
    # 3. 截图
    r = requests.get("http://localhost:8080/screenshot", timeout=10)
    with open(output_path, "wb") as f:
        f.write(r.content)
    proc.terminate()
```

**为何直接复用**：
- 当前 fork 的 Android 编译验证卡在 Gradle/AGP 兼容性问题（9.5.1 vs 8.x）
- Compose Driver **绕过了 APK 构建**，直接在 JVM 上渲染 Composable
- 这意味着 LLM 生成的 `.kt` 文件可以在**不打包 APK** 的情况下截图验证
- 与 fork 的 `validate_code.py` 形成互补：语法验证 + 视觉验证

### 2.2 ComposablePreviewScanner — @Preview 自动截图测试

**仓库**：https://github.com/sergio-sastre/ComposablePreviewScanner
**月下载量**：300,000+ | **协议**：未明确（含 LICENSE 文件）

**核心机制**：
- 基于 ClassGraph 字节码扫描，自动发现所有 `@Preview` 注解的 Composable
- 与截图测试库无关：Paparazzi / Roborazzi / Shot / Android-Testify 均支持
- **支持 Glance App Widget**（`GlanceComposablePreviewScanner`）

**对本 Fork 的关键价值**：

当前 fork 的 AGenUI PlayGround 项目使用 Jetpack Glance 1.1.1 开发 Widget。ComposablePreviewScanner 的 `GlanceComposablePreviewScanner` 可以：
1. 自动扫描 Glance `@Preview` 注解
2. 配合 Roborazzi/Paparazzi 在 JVM 上截图（无需设备）
3. 生成的截图可作为 LLM 视觉匹配的 baseline

**集成方式**：
```kotlin
// AGenUI 项目 build.gradle.kts
dependencies {
    testImplementation("io.github.sergio-sastre.ComposablePreviewScanner:glance:0.9.0")
    testImplementation("io.github.takahirom.roborazzi:roborazzi:1.40.0")
}

// ScreenshotTest.kt
class GlanceWidgetScreenshotTest {
    @Test
    fun captureAllGlancePreviews() {
        val previews = GlanceComposablePreviewScanner()
            .scanPackageTrees("com.amap.agenuiplayground.widget.glance")
            .getPreviews()
        
        previews.forEach { preview ->
            preview.invoke()  // 渲染 Glance Composable
            // Roborazzi 截图
        }
    }
}
```

---

## 3. 短期适配项目（⭐⭐ 1-2 Sprint 内）

### 3.1 Paparazzi — JVM Compose 截图测试

**仓库**：https://github.com/cashapp/paparazzi (Square)
**协议**：Apache 2.0

**核心价值**：
- 纯 JVM 运行，通过 Layoutlib 渲染 Compose UI
- 无需模拟器/设备，**CI 友好**
- 支持多设备配置、主题、字体缩放、locale 回归

**本 Fork 适配点**：
| 适配项 | 当前状态 | 改动 |
|---|---|---|
| Gradle 版本 | Fork 用 8.9-9.5.1 | Paparazzi 需要 AGP 8.x + Gradle 8.x |
| Compose BOM | Fork 未配置 | 需添加 `androidx.compose:compose-bom` |
| 截图输出 | 无 | `src/test/snapshots/images/` |

**工作流**：
```
./gradlew :app:recordPaparazziDebug   # 录制基准截图
./gradlew :app:verifyPaparazziDebug   # 对比验证
```

**与 fork 的集成**：
- LLM 生成 Compose 代码 → Paparazzi 截图 → 与原始设计截图对比 → 视觉回归
- 替代当前 `PIL ImageGrab` + `qmlscene` 方案，统一为 JVM 管线

### 3.2 Roborazzi — Robolectric 截图 + AI 断言

**仓库**：https://github.com/takahirom/roborazzi
**协议**：Apache 2.0

**独特功能 — AI-Powered Image Assertion**：
- 当截图与基准不同时，自动调用 LLM（Gemini/OpenAI）进行视觉断言
- 可自定义断言 prompt（如 "should have a search bar"）
- 支持 `requiredFulfillmentPercent` 阈值

**本 Fork 集成价值**：
- 将 Roborazzi 的 AI 断言接入 fork 的国产模型（doubao-seed-2-1-turbo）
- 形成**自动视觉验证闭环**：生成代码 → Roborazzi 截图 → AI 对比 → 反馈修复

```kotlin
// 自定义 AI 断言模型，接入火山引擎
aiAssertionModel = object : AiAssertionOptions.AiAssertionModel {
    override fun assert(...): AiAssertionResults {
        // 调用 doubao-seed-2-1-turbo vision API
        // 返回断言结果
    }
}
```

---

## 4. 架构级参考项目（⭐⭐）

### 4.1 micro-agent — TDD + 视觉匹配循环

**仓库**：https://github.com/BuilderIO/micro-agent
**协议**：MIT | **Stars**：4.3k

**核心模式**：
```
截图/设计稿 → LLM 生成代码 → 运行测试 → 截图当前状态
  → Claude Opus 对比截图 → 给出视觉差异反馈 → LLM 修复 → 循环
```

**与 fork 的关系**：
- Fork 当前只有 `validate_code.py` 做语法检查，**缺少视觉验证闭环**
- micro-agent 的视觉匹配模式可直接移植到 fork 的 web 栈
- Native 栈需配合 Compose Driver / Paparazzi 实现类似循环

**文件级集成点**：
```
backend/agent/tools/
├── validate_code.py        # 已有：语法验证
├── visual_match.py          # 新建：截图对比（micro-agent 模式）
│   ├── capture_screenshot() # 调用 Edge/Compose Driver 截图
│   ├── compare_images()     # 调用 LLM vision 对比
│   └── feedback_loop()      # 差异 → 修复 → 重试
```

### 4.2 FigmaToCode — AltNode IR 中间表示

**仓库**：https://github.com/riccardoperra/FigmaToCode
**协议**：MIT | **Stars**：3k+

**架构启示**：
```
当前 Fork：截图 → LLM → 各栈独立 prompt（12 栈 = 12 套指令）
FigmaToCode：设计稿 → AltNode IR → 多栈 codegen（一次解析，多栈输出）
```

**长期演进方向**：
- 短期：保持 `get_system_prompt(stack)` 路由模式
- 中期：引入 IR 层 — 截图 → LLM 生成 UI 描述 JSON → 各栈 codegen
- 优势：新增栈只需加 codegen 模块，不需要新 prompt

---

## 5. 参考项目（⭐）

### 5.1 Shot — Android 截图测试

**仓库**：https://github.com/pedrovgs/Shot
**协议**：Apache 2.0 | **Stars**：~1.5k

**参考价值**：
- record/verify 工作流设计
- 支持多 Flavor、多设备
- HTML 报告生成（差异对比图）
- 5.0.0+ 支持 Compose `compareScreenshot(composeRule)`

**不复用原因**：需要真实设备/模拟器，与 fork 的 JVM-first 方向不符。

### 5.2 figma-to-compose — Figma → Compose MCP Skill

**来源**：LobeHub Skills Marketplace

**参考价值**：
- Icon → VectorDrawable 自动管线（`convert-svg-to-android-drawable`）
- Figma Auto Layout → Compose 布局映射规则（Column/Row/Box/spacedBy）
- Design Token 提取（颜色/字体/间距/圆角 → MaterialTheme）

### 5.3 implement-page-android — 多帧 Figma→Compose

**来源**：SkillsMP (AGMO Inc)

**参考价值**：
- 大 Figma 页面按 Frame 拆分 → 逐帧实现 → 组件注册表复用
- 编译验证循环（max 3 retries）
- 视觉验证委托给 opus 级模型

### 5.4 Android Gemini Generate UI — 官方竞品

**来源**：https://developer.android.google.cn/studio/gemini/generate-ui-with-images

**竞品分析**：
- Android Studio 内置 Gemini，截图 → Compose 代码
- 支持 "Match UI to Target Image"（右键预览 → AI 对齐）
- "Fix all UI check issues" — 自动修复无障碍问题
- 优势：IDE 原生集成，零配置
- 劣势：仅限 Compose，不支持其他栈；闭源

---

## 6. 复用集成优先级矩阵

| 优先级 | 项目 | 集成点 | 预期收益 | 工作量 |
|---|---|---|---|---|
| P0 | **Compose Driver** | e2e_compile_verify.py | 绕过 APK 构建直接截图验证 Compose | 2h |
| P0 | **ComposablePreviewScanner** | AGenUI Glance 项目 | Glance Widget @Preview 自动截图 | 4h |
| P1 | **Paparazzi** | android_project | JVM Compose 截图替代 ADB 真机 | 1d |
| P1 | **Roborazzi AI 断言** | backend/agent/tools/ | 国产模型视觉验证闭环 | 1d |
| P2 | **micro-agent 模式** | backend/agent/tools/visual_match.py | 生成→截图→对比→修复循环 | 2d |
| P3 | **FigmaToCode IR** | 长期架构 | 一次解析多栈输出 | 1w+ |

---

## 7. 推荐实施路径

### Sprint 1（立即）
1. **Compose Driver 集成**：在 `e2e_demo/android_project` 添加插件，绕过 Gradle/AGP 兼容性问题
2. **ComposablePreviewScanner + Roborazzi**：为 AGenUI Glance Widget 搭建 JVM 截图测试

### Sprint 2（短期）
3. **Paparazzi 基准截图**：为 5 栈生成结果建立视觉回归基线
4. **Roborazzi AI 断言接入火山引擎**：用 doubao-seed-2-1-turbo 替代 Gemini/OpenAI

### Sprint 3+（中期）
5. **micro-agent 视觉匹配循环**：`backend/agent/tools/visual_match.py`
6. **IR 层原型**：截图 → UI 描述 JSON → 多栈 codegen

---

## 8. 技术选型对比总结

### 截图测试方案对比

| 维度 | ADB 真机 (当前) | Compose Driver | Paparazzi | Roborazzi | Shot |
|---|---|---|---|---|---|
| 运行环境 | 设备/模拟器 | JVM (Robolectric) | JVM (Layoutlib) | JVM (Robolectric) | 设备/模拟器 |
| 需要模拟器 | ✅ | ❌ | ❌ | ❌ | ✅ |
| 速度 | 慢 (~30s) | 快 (~5s) | 极快 (~2s) | 快 (~3s) | 慢 (~30s) |
| Compose 支持 | ✅ | ✅ | ✅ 1.3+ | ✅ | ✅ 5.0+ |
| Glance 支持 | ✅ | ❌ | ⚠️ 有限 | ✅ | ❌ |
| AI 断言 | ❌ | ❌ | ❌ | ✅ (Gemini/OpenAI) | ❌ |
| GIF 录制 | ❌ | ✅ | ❌ | ❌ | ❌ |
| 交互能力 | adb shell | HTTP API | ❌ | ❌ | ❌ |
| CI 友好 | ❌ | ✅ | ✅ | ✅ | ⚠️ |
| Fork 推荐度 | 降级方案 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐ |

**推荐组合**：Compose Driver（交互验证）+ Paparazzi（像素回归）+ Roborazzi AI 断言（语义验证）
