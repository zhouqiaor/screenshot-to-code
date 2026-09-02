# screenshot-to-code 项目记忆

## 项目概况
- **fork 来源**：`zhouqiaor/screenshot-to-code.git`（fork 自 abi/screenshot-to-code）
- **上游 remote**：`upstream` → https://github.com/abi/screenshot-to-code.git（2026-09-01 添加）
- **工作区**：`C:\Code\screenshot-to-code`
- **git remote**：origin → https://github.com/zhouqiaor/screenshot-to-code.git
- **HEAD**：853c2c4（main），upstream/main = d026163（merge base = upstream HEAD，无上游新 commit）
- **Fork 规模**：31 fork-only commits · 93 文件变更 · +7684/-55 行
- **Fork 定位**：面向 Android/国产模型的 screenshot-to-code 扩展

## OCR (OpenCodeReview) 集成
- **workflow 文件**：`.github/workflows/ocr-review.yml` + `scripts/parse_review.py`（PR 评论解析器）
- **触发方式**：PR open/synchronize/reopen + issue_comment `/open-code-review`
- **LLM Provider**：`volcengine`（OCR 内置 provider，protocol=openai）
- **配置方式**：`ocr config set provider/model/api_key`（非交互式 CI）
- **关键教训**：不要用 `OCR_LLM_*` 环境变量走 legacy 路径 — 该路径不设 protocol，OCR 默认走 Anthropic 协议导致 404
- **OCR JSON schema**：`{ status, summary: {}, tool_calls: {}, comments: [{path, start_line, end_line, severity, category, content}] }` — 注意是 `comments` 不是 `issues`，是 `path` 不是 `file`，是 `content` 不是 `message`
- **Heredoc 教训**：YAML `run: |` 块内嵌 Python heredoc 时，`<<'PYEOF'` 终止符必须行首无缩进，否则 bash 无法识别结束 → 改用独立 .py 文件
- **GitHub Secrets**：`OCR_LLM_AUTH_TOKEN`（火山引擎 Ark API Key）
- **GitHub Variables**：`OCR_LLM_MODEL`（`doubao-seed-evolving`）
- **PR #5**：https://github.com/zhouqiaor/screenshot-to-code/pull/5（OCR Run #8/#9 全部成功）
- **PR #7**：https://github.com/zhouqiaor/screenshot-to-code/pull/7（修复 OCR 评论 Message 列空 + heredoc 缩进 bug）
- **OCR 官方配置文档**：https://open-codereview.ai/docs/configuration

## 火山引擎视觉模型
- `VISION_ENDPOINT_IDS`：12 个视觉模型名 → endpoint ID 映射（见 `backend/costs/volcano_models.py`）
- **2026-09-01 17:02 实测**：15 个已开通模型中仅 `doubao-seed-2-1-turbo-260628` API 可用（endpoint 已创建 + 账户正常时 200 OK）
- `doubao-seed-evolving` 额度已用完（剩 0/11.5M）
- 其余 13 个模型均 404（endpoint 未创建），包括 GLM-5.2/GLM-4.7/DeepSeek-V4-pro 等
- 建议：优先创建 doubao-seed-1.6-flash endpoint（最便宜 ¥0.15/M input）

## 火山引擎账户状态 (2026-09-01 19:15)
- **新 Key** `ark-ee42ad2d-...-9e892`：4 个模型可用（seed-2-1-turbo, seed-evolving, character-251128, character-260628）
- **doubao-seed-1-6-vision-250815**：已 EOM（2026-07-10 停止新购），无法新建接入点，API 返回 404。EOS 2026-09-21
- **doubao-seed-2-1-turbo-260628**：已验证支持视觉多模态（/chat/completions + image_url → 200 OK）
- **5 栈生成完成**：5/5 validate_code PASS，消耗 58,618 tokens，¥0.85
- Ark API 调用日志持久化：`e2e_demo/ark_api_log.md`
- 5 栈生成脚本：`backend/generate_5stacks_combined.py` + `backend/gen_a2ui_html.py`

## Token 规划规范
- 截图 → LLM 生成多栈代码时，**不要对每个栈独立发 vision 请求**
- 正确策略：1 次 vision 调用分析截图 → N 次纯文本调用生成各栈代码
- 效果：26K tokens（优化）vs 75K tokens（独立调用），节省 ~65%
- 图片压缩：原始截图压缩到 768px 宽 JPEG（~50KB），base64 ~65KB，远小于 PNG（~872KB）

## 业界开源项目复用参考 (2026-09-01)
- **复用报告**：`design-docs/reuse-reference-report.md`（12 项目，P0-P3 优先级矩阵）
- **P0 直接复用**：
  - **Compose Driver** (github.com/jdemeulenaere/compose-driver, Apache 2.0, v0.5.0) — HTTP Server 包裹 ComposeUiTest，**无需 APK 构建即可截图验证 Compose**，绕过 Gradle/AGP 兼容性问题
  - **ComposablePreviewScanner** (github.com/sergio-sastre/ComposablePreviewScanner) — 自动扫描 @Preview，**支持 Glance App Widget**，月下载 300K+
- **P1 短期适配**：Paparazzi (JVM Layoutlib) + Roborazzi (Robolectric + AI 断言可接火山引擎)
- **P2 架构参考**：micro-agent (TDD 视觉循环) + FigmaToCode (AltNode IR)
- **推荐截图测试组合**：Compose Driver（交互验证）+ Paparazzi（像素回归）+ Roborazzi AI 断言（语义验证）
- **Android Studio 内置竞品**：Gemini Generate UI（截图→Compose + Match UI to Target Image + Fix UI issues）

## E2E 验证项目调研 (2026-09-01)
- **调研报告**：`design-docs/e2e-verification-projects.md`（5 栈 × 3-5 个项目/工具）
- **Qt/QML**：`qmlscenegrabber` + `QT_QPA_PLATFORM=offscreen` headless 截图；`TestCase.grabImage()` 内嵌测试；QML Snippets Examples (66 组件) 参考
- **Kotlin/Compose**：Compose Driver + ComposablePreviewScanner (P0)；Paparazzi 像素回归；Roborazzi AI 断言；android-showcase (AGP 8.0) 编译基准
- **Android XML**：android-showcase (AGP 8.0 + SDK 34) Gradle 配置基准；Robolectric + Layoutlib 无设备渲染；MaterialDesign 20+ M3 组件
- **A2UI**：官方协议 v0.8/v0.9/v1.0，Lit/Angular/Flutter 渲染器已可用，Compose renderer 在路线图
- **WinUI3**：WinUI 3 Gallery (官方控件百科) + WindowsAppSDK-Samples + Community Toolkit；验证器需新建 winui3 栈
- **统一截图接口**：`ScreenshotRenderer` Protocol，5 个实现类对应 5 栈
- **3 Phase 路线图**：P0 qmlscenegrabber + Compose Driver + A2UI v0.9 + winui3 验证器 → P1 Paparazzi + Robolectric + few-shot 模板 → P2 Roborazzi AI + WinAppDriver + A2UI Compose renderer

## 注意事项
- `.workbuddy/` 目录在 worktree 清理时可能被误删，需重建

## Fork 核心架构差异（相对上游）
- **ADB 截屏 pipeline**：`backend/capture/` + `backend/routes/adb.py` + `backend/scripts/` — 从 Android 设备截屏 + UI Automator 提取主题/骨架
- **多文件 AgentFileState**：`backend/agent/state.py` — 单文件 → 多文件，支持 Android Compose 的 MainActivity.kt + preview.html
- **Token 治理**：`backend/costs/` — budget_checker（预算上限）+ model_router（路由）+ prompt_compressor（压缩）+ metrics（Prometheus 端点）
- **国产模型接入**：`llm.py` 注册 8 个模型（6 doubao + 1 qwen）+ `pricing.py` 定价 + `openai.py` Volcano Ark raw httpx fallback（绕过 SDK silent crash）
- **validate_code.py**：6 栈代码验证（HTML/WPF/Android XML/Compose/Qt QML/A2UI）
- **seed_tool_call.py**：种子工具调用，用于 Android Compose 初始文件注入
