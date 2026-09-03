# 一键生成编码流水线（固化生成流程）方案

> 目标：把当前散落在 17+ 个脚本、硬编码 `RUN_DIR` 的多栈生成流程，**固化为单一可重用入口**。
> 后续只需「传入截图图片 + 需要的栈」，直接调用生成；生成结果通过**固定脚本替换到框架脚手架**，实现一键产出可运行/可预览工程。
> 状态：需求整理 + 设计分析 + 实施计划（**待用户确认后执行**）。
> 前置文档：`fork-normalization-plan.md` §八（目录规范化）、`e2e-artifacts-organization.md`（产物整理）。

---

## 一、需求整理

### 1.1 用户原话拆解
- **「固化生成流程」**：不再每次临时写脚本，生成逻辑沉淀为稳定可调用模块。
- **「后续只需传入图片和需要的栈 直接调用生成」**：入口 = `(image, stacks[])`，内部自动完成 vision→多栈代码。
- **「生成结果也通过固定脚本替换到框架」**：生成的各栈代码，用**固定 patcher** 注入到对应的框架脚手架目标文件（如 Android 的 `MainActivity.kt`、WPF 的 `MainWindow.xaml`）。
- **「一键生成编码」**：一次命令产出"每个栈的可运行工程"，而非零散文件。

### 1.2 现状痛点（为何要固化）
| 痛点 | 证据 |
|---|---|
| 每脚本硬编码输出目录 | `generate_5stacks_combined.py:21` `OUTPUT_DIR = .../run_20260901`；`e2e_unified_verify.py:42` `RUN_DIR = .../run_20260901` |
| vision 分析与多栈生成拆成两步，中间 `ui_description.json` 依赖手工预设 | `generate_5stacks_combined.py:22-25` 直接 `open(UI_DESC_PATH)` |
| 17 个 E2E 脚本 + 14 个 `test_*` 散在 `backend/` 根 | Fork §2.2 D/E |
| 生成结果无统一"注入框架"步骤，需手工替换 | 无 inject 脚本；`seed_tool_call.py` 仅解析未落地为命令 |
| 每次换图/换栈都要改脚本 | 同上硬编码 |

### 1.3 范围界定
- **做**：单一 CLI 编排 + 生成核心改造 + 注入框架固定脚本 + 输出布局（`e2e_runs/`）。
- **复用（不重写）**：`backend/llm.py`、`agent/providers/openai.py`（模型调用）、`generate_5stacks_combined.py`（生成核心）、`seed_tool_call.py`（注入解析）、`organize_runs.py` 的 `make_run_dir()`（布局）。
- **不做**：不改上游核心；不重写模型推理；不接新的 LLM provider（沿用已注册 doubao/qwen/Ark）。

---

## 二、设计分析

### 2.1 总体架构（3 阶段，单一 CLI 编排）

```
screenshot.png
   │
   ▼  [Phase 1 · Vision]   describe_image()  →  ui_description   （1 次视觉调用）
   │
   ▼  [Phase 2 · Generate] 对所选 stack 发文本调用（共 N 次，复用 ui_desc，不重复视觉）
   │                         ← 或复用现有 combined 一次出全部所选栈
   ▼
   e2e_runs/<run_id>/code/<stack>.<ext>   +  generation_report.json
   │
   ▼  [Phase 3 · Inject]   固定 patcher 按 stack→scaffold 映射，把 code 写入框架目标文件
   │
   ▼
   各栈可运行/可预览工程（android_app/、windows_wpf/、qt/、a2ui/、html preview …）
```

**Token 策略（延续既有规范，见项目记忆）**：1 次 vision 出 `ui_description`；后续 stack 生成只发 text，不重复视觉 → 约 26K vs 75K，省 ~65%。图片压缩到 768px 宽 JPEG（~50KB）再 base64。

### 2.2 单一入口 CLI

`backend/e2e/cli.py`（新增，作为 `backend/e2e/` 包的统一入口）：

```bash
python -m e2e.cli \
  --image path/to/screenshot.png \
  --stacks android_compose,android_xml,qt_qml,windows_html,a2ui,windows_wpf,winui3 \
  --model doubao-seed-2-1-turbo-260628 \
  --inject \            # 是否执行 Phase 3 注入（默认只生成代码）
  --scaffold auto       # 注入目标；auto = 按 stack 选默认脚手架
```

内部流程：
1. `run_dir = make_run_dir(model)` → `e2e_runs/<YYYYMMDD>T<HHMMSS>_<slug>/`（前向真实时间戳，便于同模型多轮对比）
2. Phase 1：`image → base64(768px JPEG) → vision model → inputs/ui_description.json`
3. Phase 2：对所选 stack 调生成，写 `code/<stack>.<ext>` + `reports/05_generation.json`
4. Phase 3（可选 `--inject`）：调用 patcher 注入脚手架
5. 写 `manifest.json`（model / stacks / code map / injection status / reports）

### 2.3 生成核心改造（`generate_5stacks_combined.py` → `e2e/generate/gen_stacks.py`）

抽离为可调用函数，去除硬编码：

```python
def generate_stacks(ui_desc: str, stacks: list[str], model: str, code_dir: Path) -> dict:
    """返回 {stack: code_str}；所选栈缺失则标记 missing。"""
    # 复用现有 COMBINED_PROMPT 模板，仅保留 stacks 子集
    # 或逐栈 text 调用（见待确认点 2）
```

- 入参 `ui_desc`（Phase 1 产物）或 `image`（内部先跑 Phase 1）。
- 出参写 `code/<stack>.<ext>`，严格对齐 `e2e-artifacts-organization.md` §2.2 的栈→扩展名映射。
- 不再写死 `OUTPUT_DIR`。

### 2.4 「注入到框架」固定脚本（`e2e/inject.py`）—— 核心创新点

维护一张 **`STACK → 脚手架目标`** 映射表，patcher 据此把 `code/<stack>.<ext>` 整文件替换到框架：

| stack | 脚手架目录 | 目标文件 | 注入方式 |
|---|---|---|---|
| `android_compose` | `e2e_demo/android_app` / `android_project` | `MainActivity.kt`（+ `preview.html`） | 整文件替换 |
| `android_xml` | `e2e_demo/android_project` | `res/layout/activity_main.xml` | 整文件替换 |
| `qt_qml` | qt 脚手架 | `main.qml` | 整文件替换 |
| `windows_html` | standalone | `index.html` / `preview.html` | 整文件替换 |
| `windows_wpf` | wpf 脚手架 | `MainWindow.xaml` | 整文件替换 |
| `winui3` | winui3 脚手架 | `MainPage.xaml` | 整文件替换 |
| `a2ui` | a2ui renderer | `*.jsonl` | 整文件替换 |

**优先用模型输出里的 `<seed:tool_call path="真实框架相对路径">content</seed:tool_call>`**（复用 `seed_tool_call.py` 的 `extract_seed_tool_calls`）——模型自己声明落点；若无 `path` 则回退到上表默认路径。这把"替换到框架"变成确定性的、可重复的固定动作。

### 2.5 复用资产清单（不重写）

| 现有模块 | 复用方式 |
|---|---|
| `backend/llm.py` / `agent/providers/openai.py` | 模型调用（已注册 doubao/qwen + Ark key） |
| `backend/generate_5stacks_combined.py` | 抽 `generate_stacks()` 核心 |
| `backend/agent/tools/seed_tool_call.py` | 解析 `<seed:tool_call path content>`，注入落点 |
| `backend/e2e/organize_runs.py` 的 `make_run_dir()` | 输出布局 + manifest |
| `backend/e2e/verify/*`（待迁自散落脚本） | Phase 后校验（validate/unified/deep/compile） |

---

## 三、实施计划（分阶段，确认后执行）

| 阶段 | 内容 | 依赖 | 产出 |
|---|---|---|---|
| **Phase 0** | 安全与目录前置：补 `.gitignore` 漏网、删根目录临时文件、轮换 `.env` key；17 个 E2E 脚本迁入 `backend/e2e/{verify,generate,pipeline,report,render,run}/` | Fork §八 | 干净可提交状态 |
| **Phase 1** | 固化生成核心：抽 `generate_stacks(image/desc, stacks, model, code_dir)`，去硬编码，内置 `describe_image()`（1 vision 调用），输出写 `e2e_runs/<run_id>/code/` | Phase 0 | 可参数化生成模块 |
| **Phase 2** | 单一 CLI 编排 `e2e/cli.py`：`--image/--stacks/--model/--inject` + 三阶段 + manifest；替换 `e2e_unified_verify.py:42` 等硬编码 RUN_DIR | Phase 1 | `python -m e2e.cli` 一键入口 |
| **Phase 3** | 注入框架固定脚本 `e2e/inject.py`：STACK→脚手架映射表 + 整文件替换 + `seed_tool_call` 解析回退；为缺脚手架的栈（wpf/winui3/qt/a2ui）建最小脚手架 | Phase 1 | 注入 patcher |
| **Phase 4** | 验证与文档：一张截图 + 选定栈跑 `cli.py --inject`，确认生成+注入+manifest 正确；旧 17 脚本归档/删除，消除"重复写脚本" | Phase 2,3 | 端到端可用 |

---

## 四、待确认点（需你拍板后再执行）

1. **注入目标脚手架**：`android_compose`/`android_xml` 用现有 `e2e_demo/android_app` + `android_project`？其余栈（wpf/winui3/qt/a2ui）是否要我**新建最小脚手架**，还是**仅生成代码文件、不接工程**？
2. **生成策略**：所选栈用「1 次 combined 调用出全部所选栈」（快、省 token）还是「每栈 1 次 text 调用」（更稳、可单独重试）？
3. **CLI 形态**：只要 `python -m e2e.cli`（命令行），还是要同时在前端生成对话框加按钮（复用 screenshot-to-code 现有 UI）？
4. **Phase 0 是否现在做**：先执行安全清理（删临时文件/补 gitignore/轮换 `.env`），还是先只做生成核心（Phase 1–3）？

> 确认后我将按阶段执行，并在每个 Phase 完成后用「执行→验证实际生效」闭环回报。

---

## 五、确认记录（2026-09-02）

用户已通过结构化提问确认以下 4 项，计划据此锁定：

| # | 决策点 | 确认值 | 对设计的影响 |
|---|---|---|---|
| 1 | 注入目标脚手架 | **仅生成代码文件**（不接工程脚手架） | Phase 3 `inject.py` 退化为「按固定 stack→path 映射把代码落到 `e2e_runs/<run_id>/code/`」，映射表保留以便后续接脚手架 |
| 2 | 生成策略 | **每栈 1 次 text 调用**（用户授权我定，取更稳/可重试项） | `generate_stacks()` 逐栈发 text 调用，复用同一 `ui_description`，不重复视觉 |
| 3 | CLI 形态 | **命令行 `python -m e2e.cli`** | 不做前端按钮，专注后端 CLI 入口 |
| 4 | Phase 0 | **先做安全清理** | 先补 `.gitignore` 漏网 + 删根目录临时文件 + 处理 `.env` 明文风险，再进生成核心 |

**执行顺序锁定**：Phase 0（安全+目录）→ Phase 1（生成核心）→ Phase 2（CLI 编排）→ Phase 3（inject 固定脚本，scope=仅落 code/）→ Phase 4（验证+旧脚本归档）。

**`.env` Key 轮换说明**：明文 `ark-ee42ad2d-...` 仍在 `backend/.env`（已被 `.gitignore` 忽略，不会入库；但本机文件系统的任何访问者可读）。彻底消除需在火山引擎控制台轮换该 Key，本agent 无控制台权限，仅能做本地提醒与 `.env` 处置建议。

---

## 六、执行记录（2026-09-02）

> 已按确认的设计推进 Phase 0–3（固化生成流程的代码骨架已落地并 dry 验证）。

### 6.1 Phase 0 安全清理
- ✅ `.gitignore` 漏网项补齐（第 91–94 行）：`0_review.txt`、`ocr_logs2.zip`、`ocr_logs2/`、`e2e_runs/` 等。`git check-ignore -v` 验证生效。
- ✅ 根目录 `0_review.txt` / `aqtinstall.log` / `ocr_logs2.zip` 已删除（高危漏网项消除）。
- ⚠️ `nul`、`ocr_logs2/` 物理删除被 **360 + Defender 锁住**（`Permission denied`，`nul` 为 Windows 保留设备名），已 gitignore 覆盖，转为手动清理项。
- ⛔ 主仓库 `.git` object store **仍损坏**：`git status` 报 `bad object HEAD`（Fork 方案 P0 未解）。
- ⛔ `.env` 明文 Key 轮换需在火山引擎控制台操作，本 agent 无权限，仅提醒。

### 6.2 Phase 1–3 代码落地（新增 `backend/e2e/` 包）
| 文件 | 职责 |
|---|---|
| `backend/e2e/common.py` | `STACKS` 注册表（7 栈→扩展名/标签/需求）、`make_run_dir()`（替代所有硬编码 RUN_DIR）、`chat()`（Ark OpenAI 兼容调用）、`compress_image()`（768px JPEG base64）、`strip_fence()` |
| `backend/e2e/generate/core.py` | `describe_image()`（**1 次视觉调用**→ui_desc）、`generate_stacks()`（**逐栈 text 调用**，复用 ui_desc，不重复视觉；单栈失败不中断其余） |
| `backend/e2e/inject.py` | `STACK_TARGETS` 映射表 + `place_stack()` / `inject_run()`（按决策 #1 仅落 `code/<stack>.<ext>`，预留脚手架扩展点） |
| `backend/e2e/cli.py` | `python -m e2e.cli --image X --stacks a,b,c --model M [--dry]`，三阶段编排 + 写 `manifest.json` |

### 6.3 验证结果
- ✅ `py_compile` 四个模块全过。
- ✅ `--dry` 端到端跑通：生成 `e2e_runs/<run_id>/{code/<5栈文件>, inputs/ui_description.json, manifest.json}`，**零硬编码 RUN_DIR**，manifest 正确记录 model/stacks/code 映射。
- ✅ **真实 LLM 调用已跑通**（2026-09-02 深夜）：设备 `200.47.91.1:5555` 截屏 → `doubao-seed-2-1-turbo-260628` + 有效 Ark Key → 双栈生成 + `validate_code` 校验，**最终 ALL PASS**。

### 6.4 真实跑实战踩坑与修复（必读）
真跑不是一次过，连踩两个坑，已修复并固化：

1. **Ark 静默截断 → 产物不完整（致命）**
   - 现象：CLI 报 `ok:true` 写出残缺文件，`validate_code` 才抓到 `android_compose` 7 个未闭合 `{`、`android_xml` XML 未闭合。
   - 根因：`generate_stacks` 原 `max_tokens=4000` 远小于真实需求（compose/xml 实测需 ~5000–9000 token）；Ark 在 4000 处**静默截断（HTTP 200、不报错）**，且原 `chat()` 只返回 `(content, usage)`、**无 `finish_reason`**，无法感知截断。
   - 修复：`chat()` 返回 `(content, usage, finish_reason)`；`generate_stacks` 基础 `max_tokens=12000`，检测到 `finish_reason=="length"` 自动翻倍重试（封顶 24000），并把 `truncated` 写入结果。

2. **httpx 默认 300s 超时 → compose 单次请求超时失败**
   - 现象：`android_compose` 报 `The read operation timed out`（12000 token 输出模型较慢，单次 > 300s）。
   - 修复：`chat()` 默认 `timeout` 由 300.0 提到 **600.0**。

3. **校验与补跑工具固化**
   - `backend/e2e/_validate_run.py`：对 `<run>/code/*` 逐栈跑 `agent.tools.validate_code.validate_code`，结果写 `<run>/reports/{stack}.json` + `summary.json`，**FAIL 即非零退出**——这是"代码真能编译"的兜底，CLI 的 `ok` 标志不可信。
   - `backend/e2e/regen_stack.py`：复用 `<run>/inputs/ui_description.json`，只补生成失败的栈、写回原 run 目录（不重跑 vision/xml），解决了"一栈超时就要整轮重来"的浪费。

### 6.5 真实跑耗时参考
| 轮次 | 命令 | 耗时 | 结果 |
|---|---|---|---|
| 首轮（截断） | `python -m e2e.cli --stacks android_compose,android_xml` | **12m2s** | 双栈均被 4000 token 截断（`validate_code` 抓出） |
| 二轮（修 max_tokens） | 同上 | **11m43s** | xml 完整 PASS；compose 因 300s 超时失败 |
| 三轮（补 compose） | `python e2e/regen_stack.py <run> android_compose` | **4m4s** | compose 完整 PASS（`truncated=False`） |

> 结论：单栈 12000 token 生成约 4–6 分钟（doubao-seed-2-1-turbo-260628）；整轮 2 栈约 12 分钟。超时阈值必须 ≥ 600s。

### 6.6 剩余待办
- `backend/e2e/` 包已建，但原散落的 17 个 E2E 脚本尚未迁入（Fork §3.1，建议后续归并，避免与新建包重名冲突）。
- `.env` Key 轮换（控制台）、`nul`/`ocr_logs2/` 手动清理、主仓库 `.git` 修复（P0）。
- 决策 #1 范围内的"注入框架"当前仅落 `code/`；若后续要接 Android/WPF 等真实工程，扩展 `inject.STACK_TARGETS` 即可，无需改生成核心。
