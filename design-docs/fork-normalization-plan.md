# Fork 目录规范化方案

> 基于 `abi/screenshot-to-code` 上游 main 分支文件树 vs 本地 fork 实际文件系统的全量对比。
> 生成时间：2026-09-02

---

## 一、现状概览

| 维度 | 上游 abi/screenshot-to-code | 本 Fork (zhouqiaor) |
|---|---|---|
| 根目录文件 | 12 个（README, LICENSE, docker-compose 等） | 24 个（含 12 个上游 + 12 个新增） |
| backend/ .py 文件 | ~40 个 | ~90 个（+50 个 fork 新增） |
| backend/ 子包 | 10 个 | 17 个（+7 个 fork 新增） |
| frontend/src/ 结构 | 基本一致 | +1 个 `variants/` 目录 |
| design-docs/ | 8 个 .md | 15 个 .md（+7 个 fork 新增） |
| .github/workflows/ | 无 workflow | +1 个 `ocr-review.yml` |
| e2e_demo/ | 不存在 | 394 文件（fork 新增） |
| e2e_test/ | 不存在 | 8 文件（fork 新增） |
| outputs/ | 不存在 | 6 文件（fork 新增） |
| ocr_logs2/ | 不存在 | 8 文件（fork 新增） |
| docs/ | 不存在 | 2 文件（fork 新增） |
| scripts/ | 不存在 | 1 文件（fork 新增） |

### Git 仓库状态

- **HEAD 损坏**：`git fsck` 报告所有分支的 SHA1 指针无效（main=853c2c4, fix/fork-only-bugs=31b432b, ocr-fix=ad87c5a 全部 invalid）
- `.git.broken/` 备份目录存在（已被 `.gitignore` 忽略）
- **根因**：本地 `.git` object store 完全损坏，无法执行任何 git diff/log 操作
- **影响**：无法用 `git diff upstream/main` 精确对比变更，本次分析基于文件系统 vs GitHub API 全量对比

---

## 二、Fork 新增内容分类

### 2.1 根目录新增文件（12 个）

| 文件 | 类别 | 状态 | 规范化建议 |
|---|---|---|---|
| `0_review.txt` | OCR 审查输出 | 临时产物 | **删除** → 已在 `.gitignore` 模式覆盖 |
| `aqtinstall.log` | Qt 安装日志 | 临时产物 | **删除** → 已在 `.gitignore` |
| `nul` | Windows 误创建空文件 | 垃圾 | **删除** → 已在 `.gitignore` |
| `PR_REVIEW_ASSESSMENT.md` | PR 评审记录 | 文档 | 移入 `design-docs/` 或删除 |
| `AGENTS.md` | AI Agent 指令 | 配置 | **保留**（Cursor Cloud 需要） |
| `CLAUDE.md` | AI Agent 指令 | 配置 | **保留** |
| `plan.md` | 开发计划 | 文档 | 移入 `design-docs/` |
| `ocr_logs2.zip` | OCR 日志压缩包 | 临时产物 | **删除** |
| `package.json` | 根级 npm 配置 | 配置 | **保留**（workspace 根） |
| `.gitattributes` | Git 属性 | 配置 | **保留** |
| `.gitignore` | Git 忽略规则 | 配置 | **保留**（已扩展 fork 规则） |

### 2.2 backend/ 新增 Python 文件（50 个，按功能分类）

#### A. 核心扩展 — 集成到上游架构（19 个，**保留**）

| 文件 | 功能 | 集成点 |
|---|---|---|
| `llm.py` (修改) | 新增 Qwen/Doubao 模型注册 | 上游已有，fork 扩展 |
| `config.py` (修改) | 新增 OPENAI_BASE_URL 等配置 | 上游已有，fork 扩展 |
| `agent/state.py` (修改) | 单文件 → 多文件 AgentFileState | 上游已有，fork 扩展 |
| `agent/tools/seed_tool_call.py` | Volcano Ark XML 工具调用解析 | 新增，Doubao 专用 |
| `agent/tools/validate_code.py` | 6 栈代码验证 | 新增，通用 |
| `prompts/prompt_types.py` (修改) | 新增 android_compose Stack 类型 | 上游已有，fork 扩展 |
| `prompts/a2ui_system.py` | A2UI 系统提示 | 新增 |
| `prompts/android_compose_system.py` | Compose 系统提示 | 新增 |
| `prompts/android_xml_system.py` | Android XML 系统提示 | 新增 |
| `prompts/create/image.py` (修改) | 图片提示扩展 | 上游已有，fork 扩展 |
| `routes/generate_code.py` (修改) | WebSocket 生成路由扩展 | 上游已有，fork 扩展 |
| `routes/model_choice_sets.py` (修改) | 模型选择集扩展 | 上游已有，fork 扩展 |
| `routes/adb.py` | ADB 截屏路由 | 新增 |
| `capture/__init__.py` | ADB 截屏包 | 新增 |
| `capture/pipeline.py` | ADB 截屏流水线 | 新增 |
| `capture/result.py` | 截屏结果模型 | 新增 |
| `capture/win_uia.py` | Windows UI Automation | 新增 |
| `scripts/adb_capture.py` | ADB 截屏脚本 | 新增 |
| `scripts/run_adb_pipeline.py` | ADB 流水线运行器 | 新增 |

#### B. Token 治理 — 新增子包（7 个，**保留**）

| 文件 | 功能 |
|---|---|
| `costs/__init__.py` | 包初始化（空，防循环导入） |
| `costs/budget_checker.py` | 预算上限检查 |
| `costs/model_router.py` | 模型路由 |
| `costs/pricing.py` | 国产模型定价 |
| `costs/prompt_compressor.py` | Prompt 压缩 |
| `costs/token_usage.py` | Token 用量追踪 |
| `costs/metrics.py` | Prometheus 指标端点 |
| `costs/volcano_models.py` | 火山引擎模型 endpoint 映射 |

#### C. 脚本/工具 — 骨架提取（4 个，**保留**）

| 文件 | 功能 |
|---|---|
| `scripts/skeleton_parser.py` | UI 骨架提取 |
| `scripts/theme_extractor.py` | 主题提取 |
| `codegen/utils.py` (修改) | extract_html_content 支持 stack 参数 |
| `codegen/test_utils.py` | codegen 测试 |

#### D. E2E 验证脚本（17 个，**需规范化**）

| 文件 | 功能 | 问题 |
|---|---|---|
| `analyze_screenshot.py` | 截图分析 | 散落在 backend/ 根 |
| `create_endpoint.py` | 火山引擎 endpoint 创建 | 散落 |
| `e2e_compile_verify.py` | 编译验证 | 散落 |
| `e2e_deep_verify.py` | 深度验证 (71KB) | 散落 |
| `e2e_unified_verify.py` | 统一验证 (37KB) | 散落 |
| `full_comparison_report.py` | 对比报告 | 散落 |
| `gen_a2ui_html.py` | A2UI HTML 生成 | 散落 |
| `gen_preview_html.py` | 预览 HTML 生成 | 散落 |
| `generate_5stacks.py` | 5 栈生成 | 散落 |
| `generate_5stacks_combined.py` | 5 栈合并生成 | 散落 |
| `generate_a2ui_html.py` | A2UI HTML 生成（重复?） | 与 gen_a2ui_html.py 重复 |
| `gen_acceptance_report.py` | 验收报告 | 散落 |
| `kotlin_pipeline.py` | Kotlin 流水线 | 散落 |
| `kotlin_pipeline_resume.py` | Kotlin 流水线恢复 | 散落 |
| `kotlin_run_comparison.py` | Kotlin 运行对比 | 散落 |
| `ws_generate_client.py` | WebSocket 生成客户端 | 散落 |
| `ws_vs_direct_report.py` | WS vs 直连对比 | 散落 |

#### E. 临时测试脚本（14 个，**需清理/归档**）

| 文件 | 功能 | 状态 |
|---|---|---|
| `test_1_6_vision.py` | 1.6 视觉模型测试 | 临时 |
| `test_all_models2.py` | 全模型测试 v2 | 临时 |
| `test_ark.py` | Ark API 测试 | 临时 |
| `test_ark_endpoints.py` | Ark endpoint 测试 | 临时 |
| `test_models.py` | 模型测试 | 临时 |
| `test_new_key.py` | 新 Key 测试 | 临时 |
| `test_new_key2.py` | 新 Key 测试 v2 | 临时 |
| `test_responses_api.py` | Responses API 测试 | 临时 |
| `test_routes.py` | 路由测试 | 临时 |
| `test_vision.py` | 视觉模型测试 | 临时 |
| `test_vision_model.py` | 视觉模型测试 | 临时 |
| `quick_test.py` | 快速测试 | 临时 |
| `prep_screenshot.py` | 截图预处理 | 临时 |
| `list_models.py` | 模型列表 | 临时 |

#### F. 渲染/截图工具（6 个，**需规范化**）

| 文件 | 功能 |
|---|---|
| `render_a2ui_preview.cjs` | A2UI 预览渲染 |
| `render_screenshot.cjs` | 截图渲染 |
| `screenshot_html.py` | HTML 截图 |
| `screenshot_html_edge.py` | Edge HTML 截图 |
| `screenshot_qml.py` | QML 截图 |
| `run_validate_e2e.py` | E2E 验证运行器 |
| `run_5stacks.py` | 5 栈运行器 |

### 2.3 backend/ 新增子包

| 子包 | 上游是否存在 | 功能 | 规范化建议 |
|---|---|---|---|
| `capture/` | ❌ | ADB 截屏 pipeline | **保留**（核心功能） |
| `costs/` | ❌ | Token 治理 | **保留**（核心功能） |
| `scripts/` | ❌ | 骨架/主题提取 | **保留** |
| `ws/` | ✅ | WebSocket 常量 | **保留**（上游已有 `ws/`） |
| `evals_data/` | ❌ | 评测数据 | **删除**（已在 `.gitignore`） |
| `local_assets/` | ❌ | 本地资源 | **删除**（已在 `.gitignore`） |

### 2.4 frontend/ 新增

| 项目 | 上游是否存在 | 功能 |
|---|---|---|
| `src/components/variants/Variants.tsx` | ❌ | 变体选择 UI |
| `src/App.tsx` (修改) | ✅ | 已扩展 |

### 2.5 design-docs/ 新增（7 个）

| 文件 | 功能 |
|---|---|
| `e2e-verification-projects.md` | E2E 验证项目调研 |
| `industry-research-analysis.md` | 业界研究分析 |
| `native-stacks-integration-plan.md` | 原生栈集成计划 |
| `reuse-reference-report.md` | 复用参考报告 |
| `script-optimization-plan.md` | 脚本优化计划 |
| `settings-screenshot-to-code-history.md` | 设置历史 |
| `skeleton-reuse-guide.md` | 骨架复用指南 |
| `winui3-and-token-optimization-plan.md` | WinUI3 与 Token 优化 |

### 2.6 CI/CD 新增

| 文件 | 功能 |
|---|---|
| `.github/workflows/ocr-review.yml` | OpenCodeReview CI |

---

## 三、规范化方案

### 3.1 目录结构重组

```
backend/
├── agent/           # 上游架构，fork 扩展（保留）
│   ├── tools/
│   │   ├── validate_code.py    # ← 新增：6栈验证
│   │   └── seed_tool_call.py   # ← 新增：Ark XML解析
│   └── state.py                # ← 修改：多文件状态
├── capture/         # ← 新增：ADB截屏pipeline（保留）
├── costs/           # ← 新增：Token治理（保留）
├── prompts/         # 上游架构，fork 扩展
│   ├── a2ui_system.py
│   ├── android_compose_system.py
│   └── android_xml_system.py
├── routes/          # 上游架构
│   └── adb.py       # ← 新增
├── scripts/         # ← 新增：骨架/主题提取（保留）
│
├── e2e/             # ★ 新建：E2E 验证统一收纳
│   ├── __init__.py
│   ├── verify/
│   │   ├── compile_verify.py      # ← 从 e2e_compile_verify.py 移入
│   │   ├── deep_verify.py         # ← 从 e2e_deep_verify.py 移入
│   │   └── unified_verify.py      # ← 从 e2e_unified_verify.py 移入
│   ├── generate/
│   │   ├── gen_5stacks.py          # ← 从 generate_5stacks.py 移入
│   │   ├── gen_5stacks_combined.py # ← 从 generate_5stacks_combined.py 移入
│   │   ├── gen_a2ui_html.py       # ← 合并 gen_a2ui_html.py + generate_a2ui_html.py
│   │   └── gen_preview_html.py    # ← 从 gen_preview_html.py 移入
│   ├── pipeline/
│   │   ├── kotlin_pipeline.py     # ← 从 kotlin_pipeline.py 移入
│   │   └── kotlin_pipeline_resume.py
│   ├── report/
│   │   ├── full_comparison.py     # ← 从 full_comparison_report.py 移入
│   │   ├── acceptance_report.py   # ← 从 gen_acceptance_report.py 移入
│   │   └── ws_vs_direct.py        # ← 从 ws_vs_direct_report.py 移入
│   ├── render/
│   │   ├── a2ui_preview.cjs       # ← 从 render_a2ui_preview.cjs 移入
│   │   └── screenshot.cjs         # ← 从 render_screenshot.cjs 移入
│   └── run/
│       ├── validate_e2e.py        # ← 从 run_validate_e2e.py 移入
│       └── run_5stacks.py         # ← 从 run_5stacks.py 移入
│
├── scripts_tmp/     # ★ 新建：临时测试脚本归档（或直接删除）
│   ├── test_1_6_vision.py
│   ├── test_all_models2.py
│   ├── test_ark.py
│   ├── test_ark_endpoints.py
│   ├── test_models.py
│   ├── test_new_key.py
│   ├── test_new_key2.py
│   ├── test_responses_api.py
│   ├── test_routes.py
│   ├── test_vision.py
│   ├── test_vision_model.py
│   ├── quick_test.py
│   ├── prep_screenshot.py
│   ├── list_models.py
│   ├── screenshot_html.py
│   ├── screenshot_html_edge.py
│   ├── screenshot_qml.py
│   ├── ws_generate_client.py
│   └── kotlin_run_comparison.py
│
├── (上游原有文件全部保留)
```

### 3.2 临时产物清理清单

以下文件/目录应从版本控制中移除（已在 `.gitignore` 但物理文件仍在）：

| 路径 | 类型 | 大小 | 操作 |
|---|---|---|---|
| `0_review.txt` | OCR 输出 | 14KB | 删除 |
| `aqtinstall.log` | 安装日志 | 529B | 删除 |
| `nul` | 空文件 | 0B | 删除 |
| `ocr_logs2/` | OCR 日志 | 8 文件 | 删除 |
| `ocr_logs2.zip` | OCR 压缩包 | 10KB | 删除 |
| `backend/local_assets/` | 本地资源 | 50KB | 删除（.gitignore 已覆盖） |
| `backend/evals_data/` | 评测数据 | 空 | 删除（.gitignore 已覆盖） |
| `e2e_demo/run_20260901/` | 运行产物 | ~8MB | **已迁移**至 `e2e_runs/20260901_doubao-seed-2-1-turbo-260628/`（见 `e2e-artifacts-organization.md`），源目录已清空删除 |
| `e2e_demo/screenshots/` | 截图产物 | ~8MB | 删除或移入 outputs/ |
| `outputs/screencoder-analysis/` | 分析产物 | ~10MB | 删除或归档 |

### 3.3 .gitignore 补充规则

> **2026-09-02 实测校正**：`.gitignore` 第 83 行**已存在** `e2e_runs/` 与 `ocr_logs2/`（两份方案的 `.gitignore` 提案均部分重复）。其余条目需按下方「待补充」补齐。

**已覆盖**（无需重复添加）：`e2e_runs/`(83)、`ocr_logs2/`(83)、`nul`(85)、`aqtinstall.log`(86)、`*.bak`(87)、`backend/local_assets/*`(8)、`run_logs/`(7)、`.git.broken/`、`.env`(17)

**待补充**（已用 `git check-ignore -v` 验证当前未忽略）：

```gitignore
# ── 根目录 / OCR 漏网（⚠️ 0_review.txt 当前可被 git add，务必补）──
0_review.txt
ocr_logs2.zip

# ── E2E 运行产物（与 e2e-artifacts-organization.md §5 合并）──
e2e_demo/run_*/
e2e_demo/screenshots/
outputs/
backend/scripts_tmp/
backend/e2e/run_*/

# ── 迁移备份（临时，确认后可删，注意 *.bak 不匹配前缀 .bak_）──
.bak_e2e_run_*/
```

> 注：`*.bak` 只匹配**后缀** `.bak`，不匹配前缀 `.bak_e2e_run_*` 目录，故备份目录需显式规则。

### 3.4 .env 安全问题

**`backend/.env` 包含明文 API Key**：
```
OPENAI_API_KEY=ark-&lt;REDACTED&gt;
OPENAI_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
```

**规范化建议**：
1. **立即轮换该 Key**（已暴露在工作区文件中）
2. `.env` 已在 `.gitignore` 中（第 17 行），不会被提交
3. 但物理文件存在于工作区，任何有文件系统访问的人都能读取
4. 建议改用环境变量注入：`export OPENAI_API_KEY=ark-xxx && poetry run uvicorn main:app`

### 3.5 重复文件合并

| 文件 A | 文件 B | 问题 | 建议 |
|---|---|---|---|
| `gen_a2ui_html.py` (3560B) | `generate_a2ui_html.py` (5460B) | 功能高度重叠 | 合并为 `e2e/generate/gen_a2ui_html.py` |
| `generate_5stacks.py` (12302B) | `generate_5stacks_combined.py` (5429B) | combined 是 5stacks 的重构版 | 保留 combined，归档原版 |

### 3.6 design-docs/ 规范化

当前 15 个 .md 文件平铺在 `design-docs/`，建议按主题分子目录：

```
design-docs/
├── architecture/          # 架构设计
│   ├── agent-tool-calling-flow.md
│   ├── agentic-runner-refactor.md
│   ├── prompt-history-refactor.md
│   ├── variant-system.md
│   └── commits-and-variants.md
├── stacks/               # 栈集成
│   ├── native-stacks-integration-plan.md
│   ├── winui3-and-token-optimization-plan.md
│   └── skeleton-reuse-guide.md
├── research/             # 调研报告
│   ├── e2e-verification-projects.md
│   ├── industry-research-analysis.md
│   ├── reuse-reference-report.md
│   └── settings-screenshot-to-code-history.md
├── ops/                  # 运维与优化
│   ├── script-optimization-plan.md
│   └── images-in-update-history.md
└── general.md
```

---

## 四、Git 仓库修复方案

当前 `.git` object store 完全损坏，无法正常操作。修复步骤：

### 方案 A：Fresh Clone + 手动合并（推荐）

```bash
# 1. 备份当前工作区（保留所有文件）
cp -r /c/Code/screenshot-to-code /c/Code/screenshot-to-code-backup

# 2. Fresh clone 上游
cd /c/Code
git clone https://github.com/abi/screenshot-to-code.git screenshot-to-code-fresh

# 3. 添加 fork remote
cd screenshot-to-code-fresh
git remote add origin https://github.com/zhouqiaor/screenshot-to-code.git
git remote add upstream https://github.com/abi/screenshot-to-code.git

# 4. Fetch fork 分支
git fetch origin

# 5. 基于 upstream/main 创建 fork 工作分支
git checkout -b fork/main origin/main

# 6. 将备份中的 fork 新增文件覆盖到 fresh clone
# （手动或用 rsync 选择性同步）

# 7. 提交并推送
git add -A
git commit -m "Restore fork additions on top of upstream main"
git push origin fork/main
```

### 方案 B：重建 .git（备用）

```bash
# 如果 fresh clone 不可行，删除损坏的 .git 并重新初始化
cd /c/Code/screenshot-to-code
mv .git .git.broken.old
mv .git.broken .git.broken.old
git init
git remote add origin https://github.com/zhouqiaor/screenshot-to-code.git
git remote add upstream https://github.com/abi/screenshot-to-code.git
git fetch origin
git reset --soft origin/main  # 保留工作区文件
```

---

## 五、优先级行动清单

| 优先级 | 操作 | 影响范围 | 预期效果 |
|---|---|---|---|
| **P0** | 轮换 `backend/.env` 中的火山引擎 API Key | 安全 | 消除密钥泄露风险 |
| **P0** | 修复 `.git` object store | 仓库 | 恢复 git diff/log/branch 能力 |
| **P1** | 删除 5 个根目录临时文件（0_review.txt, aqtinstall.log, nul, ocr_logs2/, ocr_logs2.zip） | 清理 | 减少 ~25KB 垃圾 |
| **P1** | 将 14 个临时测试脚本移入 `backend/scripts_tmp/` 或删除 | backend/ 根 | 减少 14 个散落文件 |
| **P1** | 将 17 个 E2E 脚本移入 `backend/e2e/` 子包 | backend/ 根 | 统一 E2E 代码组织 |
| **P2** | 合并重复文件（gen_a2ui_html.py / generate_a2ui_html.py） | backend/ | 消除重复 |
| **P2** | design-docs/ 按主题分子目录 | 文档 | 提高可导航性 |
| **P2** | 补充 `.gitignore` fork 专用规则 | 配置 | 防止产物再次入库 |
| **P3** | 将根目录 `plan.md` / `PR_REVIEW_ASSESSMENT.md` 移入 design-docs/ | 根目录 | 减少根目录混乱 |
| **P3** | 清理 `e2e_demo/run_20260901/` 运行产物（~8MB） | 磁盘 | 减少仓库体积 |

---

## 六、规范化后的目录结构总览

```
screenshot-to-code/
├── .github/workflows/ocr-review.yml   # CI（fork 新增）
├── .claude/  .vscode/  .zed/          # IDE 配置（上游+fork）
├── AGENTS.md  CLAUDE.md               # AI Agent 指令（fork 新增）
├── README.md  LICENSE  QA.md  ...     # 上游文档（保留）
├── docker-compose.yml  package.json   # 配置（保留）
├── design-docs/                       # 设计文档（fork 扩展，分子目录）
│   ├── architecture/
│   ├── stacks/
│   ├── research/
│   └── ops/
├── docs/                              # 运维文档（fork 新增）
├── scripts/                           # CI 脚本（上游 cursor-cloud-install.sh）
├── backend/
│   ├── agent/         # 上游核心，fork 扩展
│   ├── capture/       # ADB 截屏（fork 新增）
│   ├── codegen/       # 上游核心，fork 扩展
│   ├── costs/         # Token 治理（fork 新增）
│   ├── e2e/           # E2E 验证（fork 新增，规范化后）
│   ├── evals/         # 上游评测（保留）
│   ├── fs_logging/    # 上游日志（保留）
│   ├── image_generation/  # 上游图片生成（保留）
│   ├── preview_screenshot/  # 上游预览（保留）
│   ├── prompts/       # 上游核心，fork 扩展
│   ├── routes/        # 上游核心，fork 扩展
│   ├── scripts/      # 骨架/主题提取（fork 新增）
│   ├── tests/         # 上游测试（保留）
│   ├── uploaded_assets/  # 上游资源（保留）
│   ├── video/         # 上游视频（保留）
│   ├── ws/            # 上游 WebSocket（保留）
│   ├── llm.py  config.py  main.py  ...  # 上游核心文件（保留/扩展）
│   └── pyproject.toml  poetry.lock     # 依赖管理
├── frontend/
│   └── src/
│       ├── components/  # 上游组件 + variants/（fork 新增）
│       └── App.tsx      # fork 扩展
├── e2e_demo/          # E2E 演示（fork 新增，清理产物后保留）
│   ├── templates/     # 模板（保留）
│   └── scripts/       # 脚本（保留）
├── e2e_test/          # E2E 测试数据（fork 新增）
└── outputs/           # 分析输出（.gitignore，不入库）
```

---

## 七、与上游的架构差异总结

| 差异点 | 上游 | Fork | 集成方式 |
|---|---|---|---|
| **文件状态模型** | 单文件 (`path` + `content`) | 多文件 (`AgentFileState`) | 向后兼容（property 兼容旧接口） |
| **Stack 类型** | 6 种 web stack | + `android_compose` | `prompt_types.py` Literal 扩展 |
| **系统提示** | `system_prompt.py` | + 3 个专用 system prompt | 独立模块，按 stack 选择 |
| **代码验证** | 无 | `validate_code.py` (6 栈) | agent tools 扩展 |
| **LLM 模型** | OpenAI/Anthropic/Gemini | + Qwen + 5 个 Doubao | `llm.py` Enum + `MODEL_PROVIDER` 扩展 |
| **Token 治理** | 无 | `costs/` 子包 | 独立子包，无循环依赖 |
| **ADB 截屏** | 无 | `capture/` + `routes/adb.py` | 独立子包 + 路由 |
| **CI** | 无 workflow | `ocr-review.yml` | GitHub Actions |
| **工具调用解析** | 标准 OpenAI tool_calls | + `seed_tool_call.py` (Ark XML) | agent tools 扩展 |

---

## 八、与 E2E 整理方案的衔接（状态同步 2026-09-02）

> 本节将本 Fork 方案与 `e2e-artifacts-organization.md`（E2E 生成代码/测试结果整理）合并分析，消除两份文档之间的冲突与失效点，并给出统一行动清单。

### 8.1 两份方案的定位与关系

| 方案 | 关注范围 | 产物类型 | 当前状态 |
|---|---|---|---|
| 本文（Fork 目录规范化） | 整个 fork 相对上游的**新增文件/目录**怎么归位 | 源码、子包、脚本、文档、CI、临时文件 | 文档化，部分执行 |
| `e2e-artifacts-organization.md` | 仅 **E2E 运行产物**（生成的代码 + 测试结果 + 渲染图） | 运行期产物（`e2e_runs/`） | 首轮迁移已完成 |

**职责划分（关键）**：
- **代码/脚本归 `backend/e2e/`**（Fork 方案 §3.1）—— 这是*可执行的 Python 包*。
- **数据/产物归 `e2e_runs/`**（E2E 方案）—— 这是*脚本跑出来的运行结果*。
- 二者**不冲突**：脚本住在 `backend/e2e/`，跑完把结果写到仓库根的 `e2e_runs/<run_id>/`。

### 8.2 冲突 / 失效点矩阵

| 主题 | Fork 方案原表述 | E2E 方案实际情况 | 校正结论 |
|---|---|---|---|
| `e2e_demo/run_20260901` | §3.2 "删除或移入 outputs/" | 已迁移至 `e2e_runs/20260901_...`，源已删 | **已迁移**（§3.2 已改） |
| `.gitignore` | §3.3 列 `e2e_runs/`、`ocr_logs2/` | `.gitignore` 第 83 行**本就有**这两行 | 提案冗余，仅需补漏网项（§3.3 已改） |
| `backend/e2e/` | §3.1 规划 17 个脚本迁入 | 目前仅 `organize_runs.py` 1 个文件 | **未执行**，17 脚本仍在 `backend/` 根 |
| `0_review.txt` / `ocr_logs2.zip` | §3.2/§3.3 列删除/忽略 | `git check-ignore` 验证**未忽略**，可被 `git add` | **高危漏网**，必须补 `.gitignore` + 删文件 |
| `e2e_demo/` 遗留产物 | §6 概览称清理后只留 `templates/`+`scripts/` | 根目录仍有 ~30 散落文件（见 8.4） | **新缺口**，需二次清扫 |
| `_templates`/`_fixtures` | 未提及 | E2E 方案 P2 拟迁 `e2e_demo/templates/`→`e2e_runs/_templates/`，`e2e_test/settings_*`→`e2e_runs/_fixtures/` | E2E 方案扩展了本方案范围 |

### 8.3 当前真实状态快照（2026-09-02 实测）

**✅ 已完成**
- E2E 首轮迁移：`e2e_demo/run_20260901` → `e2e_runs/20260901_doubao-seed-2-1-turbo-260628/`（code/reports/renders/inputs/subruns/misc + manifest.json），备份 `.bak_e2e_run_20260901_before_organize/` 保留。
- `.gitignore` 已含 `e2e_runs/`、`ocr_logs2/`、`nul`、`aqtinstall.log`、`*.bak`、`backend/local_assets/*`、`.env`。

**⛔ 仍开放（高危）**
- **P0** `backend/.env` 明文火山引擎 Key 未轮换 —— 仍在 `OPENAI_API_KEY=ark-REDACTED`。
- **P0** 主仓库 `.git` object store 仍损坏（`git fsck` 全 invalid）；`C:/Code/screenshot-to-code-fresh` 为独立 fresh clone（缓解但不治本）。
- **P1** 根目录临时文件 `0_review.txt`(14KB)、`aqtinstall.log`、`nul`、`ocr_logs2.zip` 仍在，且 `0_review.txt`/`ocr_logs2.zip` **未 gitignore**。
- **P1** `backend/` 根仍有 49 个 `.py`：17 个 E2E 脚本 + 14 个临时 `test_*` + 6 个渲染脚本，均未迁入 `backend/e2e/`。
- **P2** 重复文件 `gen_a2ui_html.py` vs `generate_a2ui_html.py` 未合并；`design-docs/` 未分子目录。
- **P2** `.gitignore` 漏网项未补（见 §3.3）。
- **P3** `plan.md`/`PR_REVIEW_ASSESSMENT.md` 仍在根目录。

**🆕 新缺口（两份方案均未覆盖）**
1. `e2e_demo/` 根 ~30 散落产物（见 8.4），非 `run_*` 模式，E2E 迁移脚本 `discover_run_sources` 只扫 `run_*`，故未处理。
2. `e2e_demo/screenshots/run_20260901/` 残留（迁移只取走了 `source_screenshot_1024.png`，目录未清）。
3. `outputs/screencoder-analysis/` 仍存在（Fork 方案 §3.2 说删/归档，未执行）。

### 8.4 `e2e_demo/` 根目录遗留产物分类（需二次清扫）

| 类别 | 文件 | 建议处置 |
|---|---|---|
| 持久模板 | `templates/`(a2ui/android_xml/kotlin_compose/qt_qml/windows_html/winui3) | 迁 `e2e_runs/_templates/`（E2E P2） |
| 持久脚本 | `scripts/quick_verify.py` | 保留或迁 `backend/e2e/run/` |
| 生成代码（散落） | `llm_a2ui.jsonl` `llm_android_compose.kt` `llm_android_xml.xml` `llm_qt_qml.qml` `llm_windows_html.html` `llm_windows_wpf.xaml` | 归入某 run 的 `code/`，或直接删（疑似早期手动跑的重复产物） |
| 测试结果（散落） | `validation_report.json` `validate_code_results.json` `test_report.json` `model_test_results.json` `final_report.json` `validation_results.json` `e2e_full_validation_report.html` `compilation_report.md` `final_test_report.md` `raw_output.txt` | 归入 run 的 `reports/`，或删 |
| 渲染/工具 | `render_kotlin_output.cjs` `render_screenshots.cjs` `render_ui_effects.cjs` `ark_api_log.md` | 工具脚本→`backend/e2e/render/`；日志→`misc/` 或删 |
| 构建工程 | `android_app/` `android_project/` `template_build_test/` | 属"可构建验证工程"，建议迁 `e2e_demo/build_projects/` 或单独 `android_verification/` |
| 截图 | `screenshots/`(含 `run_20260901/` 残留) | 整体迁 `e2e_runs/_fixtures/screenshots/` 或删；清 `run_20260901/` 子目录 |

### 8.5 统一优先级行动清单（合并两份方案）

| 优先级 | 动作 | 来源 | 状态 |
|---|---|---|---|
| **P0** | 轮换 `backend/.env` 火山引擎 Key | Fork §3.4 | ⛔ 未做 |
| **P0** | 修复主仓库 `.git` object store（fresh clone 已存在，需重建提交历史） | Fork §四 | ⛔ 未做 |
| **P0** | 补 `.gitignore` 漏网项（`0_review.txt`/`ocr_logs2.zip`/`e2e_demo/run_*`/`outputs/`/`.bak_e2e_run_*`） | Fork §3.3 + E2E §5 | ⛔ 未做 |
| **P1** | 删除根目录临时文件（`0_review.txt` `aqtinstall.log` `nul` `ocr_logs2.zip`） | Fork §3.2 | ⛔ 未做 |
| **P1** | 将 17 个 E2E 脚本迁入 `backend/e2e/{verify,generate,pipeline,report,render,run}/` | Fork §3.1 | ⛔ 未做 |
| **P1** | 将 14 个临时 `test_*` 脚本删或迁 `backend/scripts_tmp/` | Fork §3.1 | ⛔ 未做 |
| **P1** | 改造 `e2e_unified_verify.py` 等：`RUN_DIR` → `make_run_dir()` 自动生成 run | E2E §三 | ⛔ 未做（根治散落） |
| **P2** | 二次清扫 `e2e_demo/` 根 ~30 散落产物（8.4） | 新缺口 | ⛔ 未做 |
| **P2** | 合并重复文件 `gen_a2ui_html.py`/`generate_a2ui_html.py` | Fork §3.5 | ⛔ 未做 |
| **P2** | `design-docs/` 按主题分子目录 | Fork §3.6 | ⛔ 未做 |
| **P2** | `_templates`/`_fixtures` 归位（`e2e_runs/_templates`、`e2e_runs/_fixtures`） | E2E §2 P2 | ⛔ 未做 |
| **P3** | `plan.md`/`PR_REVIEW_ASSESSMENT.md` 迁 `design-docs/` | Fork §3.6 | ⛔ 未做 |
| **P3** | 确认迁移无误后删 `.bak_e2e_run_20260901_before_organize/` | E2E §四 | ⛔ 未做 |

> **执行顺序建议**：P0（安全+仓库）→ P1（清理+脚本归位+前向改造）→ P2（二次清扫+重复合并+文档）→ P3（收尾）。E2E 方案的首轮迁移（P1）已完成，是上述清单里唯一打勾项。
