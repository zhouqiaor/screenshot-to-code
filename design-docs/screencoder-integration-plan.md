# ScreenCoder 固化生成流程 — 需求 / 设计 / 计划

> 目标：把 ScreenCoder 的「高保真截图→HTML（真实图片裁剪回填）」能力固化成可复用管线，
> 后续**只传「图片 + 栈」**即可一键生成对应栈代码，并把结果按固定规则接入 fork 框架。

---

## 一、需求整理

### 1.1 用户诉求（原文意图）
- 把 ScreenCoder 的截图→高保真 HTML 流程**固化成不变量管线**，不再每次临时写脚本。
- 后续使用：**只传入「截图图片 + 目标栈」**，一键调用即生成该栈代码。
- 生成结果**通过固定脚本自动替换/接入 fork 框架**（screenshot-to-code），实现「一键生成编码」。

### 1.2 功能需求（FR）
- **FR1 单一入口**：一条命令 `gen --image <截图> --stack <栈>`，支持 `--stack all`。
- **FR2 输入仅两变量**：图片路径 + 栈名（见下方枚举）。
- **FR3 流程固化**：ScreenCoder 三阶段 + fork 各栈生成封装成不变量，不再手写 patch。
- **FR4 结果自动落盘到框架**：产物按固定规则写入 fork 产出目录，省略手动拷贝。
- **FR5 配置外置**：API Key / 模型名 / 路径集中在单一配置（不落盘到仓库或记忆），换 key 不碰源码。

### 1.3 栈枚举（fork 的权威来源 `backend/agent/tools/validate_code.py:28`）
`html` · `android_compose` · `android_xml` · `qt_qml` · `a2ui` · `windows_wpf`

### 1.4 非功能需求（NFR）
- **NFR1 幂等**：同输入 + 同栈 + 同配置 → 可复现产物。
- **NFR2 依赖隔离**：ScreenCoder 重依赖（TF/Paddle/Playwright）跑在自身 venv；fork 生成跑在 backend poetry env；CLI 跨进程编排。
- **NFR3 可观测**：每阶段打印耗时 / token 用量 / 产物路径，失败可定位到具体阶段。
- **NFR4 易扩展**：新增栈 / 换模型只改配置，不动编排逻辑。

---

## 二、设计分析

### 2.1 整体架构（两阶段混合）
```
截图 ──▶ [Stage A: ScreenCoder 高保真 HTML] ──▶ [Stage B: fork 各栈生成] ──▶ 落盘到框架
```

- **Stage A（ScreenCoder，自身 venv）** — 输出高保真 HTML 是核心增量价值：
  1. `block_parsor`：VLM 检测 sidebar/header/nav/main 区块框
  2. `html_generator`：分区并行生成含灰色占位符的 HTML
  3. `image_box_detection` + `UIED/run_single` + `mapping` + `image_replacer`：真实图片裁剪回填 → **高保真 HTML**
- **Stage B（fork，poetry env）**：
  - stack = `html`：直接采用 Stage A 的 HTML（轻量适配/校验）作为 html 栈产物
  - stack = 其他：以「Stage A 高保真 HTML + 原图」作为**富参考**，调用 fork 栈生成逻辑（`make_stack_prompt` + Ark）产出 Compose/QML/XML/WPF/A2UI

> 为什么是「混合」而非「全用 ScreenCoder」：ScreenCoder 只产出 Tailwind HTML；fork 已具备 6 栈生成能力。
> 把 ScreenCoder 的强项（图片 100% 视觉还原）补进 fork 的弱项（原仅靠 vision 描述、图片易丢），是最省事且增益最大的组合。

### 2.2 模块划分（建议放在 fork `backend/screencoder_integration/`）
| 模块 | 职责 |
|---|---|
| `cli.py` | 单一入口，解析 `--image / --stack / --config`，编排两阶段 |
| `screencoder_runner.py` | 封装 ScreenCoder 六脚本调用（subprocess → ScreenCoder/.venv），**固化已知坑的补丁**（UIED `is_ip`/`test4`、模型名两处），不再临时改源码 |
| `stack_generator.py` | 从 `generate_5stacks.py` 抽取 `make_stack_prompt` + `call_ark`，改为接收 Stage A HTML 作为参考 |
| `ingest.py` | 固定「替换到框架」脚本：按约定写入 `e2e_runs/<run_id>/code/variants/<stack>/` |
| `config.py` | 读取 `config.yaml`（key/model/paths），不落盘记忆 |
| `screencoder/`（子模块） | ScreenCoder 本体，建议 `git submodule` 或 vendored 拷贝到本目录 |

### 2.3 关键设计决策（⚠️ 需你确认）
- **D1 非 HTML 栈如何生成**：
  - (A) Stage A 高保真 HTML 当富参考 → fork LLM 出各栈【推荐：复用既有能力、增量最小】
  - (B) 改造 ScreenCoder 提示词直接出各栈【侵入大、需重测】
  - (C) 仅固化 HTML 栈，其他栈走 fork 原生（不整合 ImageReplacement）【最简单但放弃图片增益】
- **D2 产物落盘位置**：
  - (A) `e2e_runs/<run_id>/code/variants/<stack>/`【推荐：与现有 E2E 整理一致，便于对比】
  - (B) ScreenCoder 自身 `data/output/`
  - (C) fork backend 生成路由（Web 一键预览）
- **D3 调用入口形态**：
  - (A) fork backend 内 CLI 模块 `screencoder_integration/cli.py`【推荐：可脚本化、符合"固化"】
  - (B) 并入 fork 的 WebSocket 生成路由（前端 UI 一键）
  - (C) WorkBuddy 自动化 / 定时任务

### 2.4 风险与前置条件
- ⚠️ **前置阻塞**：当前**无可用 VLM Key**（仓库 `doubao_api.txt` 与 `backend/.env` 的 Ark key 均 401）。Stage A 阶段 1/2 强依赖在线 VLM，拿不到 key 无法跑通。需你提供任一有效视觉 Key（Ark / DashScope-Qwen / OpenAI / Gemini）。
- **依赖冲突**：ScreenCoder 需 TF+Paddle（自身 `.venv` 已装核心包 + Playwright，但 UIED 的 TF/Paddle 尚未装）；fork 用 poetry。跨进程编排规避冲突。
- **格式对齐**：ScreenCoder 输出 Tailwind HTML；fork 的 html 栈产物是自包含 HTML，需做轻量对齐（或 html 栈直接复用 Stage A 产物）。

---

## 三、实施计划（分阶段，每阶段用 git worktree 隔离）

- **Phase 0 — 前置解锁**：你提供 VLM Key → 验证 ScreenCoder 用已就位的 4K 设置页图单图跑通（现有 `run_screen2code.py` 已可一键，仅缺 key）。
- **Phase 1 — 固化 ScreenCoder 调用**：把 `run_screen2code.py` 的补丁逻辑搬进 `screencoder_runner.py`（输入图片+模型 → 输出高保真 HTML），验证可重复。
- **Phase 2 — 封装 fork 栈生成**：从 `generate_5stacks.py` 抽取 `make_stack_prompt`/`call_ark`，改为接收 Stage A HTML 参考，单栈可生成、可校验。
- **Phase 3 — 编写 `ingest.py`**：产物按约定写入 `e2e_runs/<run_id>/code/variants/<stack>/`（D2 选定位置）。
- **Phase 4 — 编写 `cli.py`**：统一 `--image --stack`，串联 Phase1–3，加耗时 / token 用量日志。
- **Phase 5 — 端到端验证**：用 4K 设置页图跑 `--stack all`，对比 6 栈产物与 fork 原生差异（重点验证图片保真度提升）。

> 实现时遵守项目强制规则：新功能分支走 `git worktree`（非同目录切分支），如
> `git worktree add -b feat/screencoder-pipeline ../screenshot-to-code-screencoder`。

---

## 四、确认项小结
请在下方选择 **D1 / D2 / D3** 三项决策（默认推荐项已标 ⭐），确认后我即按 Phase 0→5 推进。

---

## 五、确认后的最终范围（2026-09-02 用户拍板）

用户三项选择 → **范围显著收窄为「仅固化 ScreenCoder 高保真 HTML 产出」**：

| 决策 | 用户选择 | 落地结论 |
|---|---|---|
| D1 栈策略 | **先只出 HTML** | 不接 fork 多栈桥接；fork 各栈生成（Phase 2/3 原 fork 部分）**推迟到后续** |
| D2 落盘 | **只生成结果、不替换** | 产物 = `ScreenCoder/data/output/test1_layout_final.html`；**不写 ingest.py、不进 `e2e_runs`** |
| D3 入口 | **先保持现状** | 沿用 `ScreenCoder/run_screen2code.py` 作为固定入口；不新建 CLI 模块、不接 Web |

### 最终交付（已满足）
- **固化工具**：`C:/Code/ScreenCoder/run_screen2code.py`
  - 调用签名：`run_screen2code.py --image <截图> --model <视觉模型>`（`--stack` 预留接口，当前仅 `html`）
  - 自动解 5 坑（模型名两处 + UIED `is_ip/is_merge/input` 三处），跑完还原源码
  - key 走 env `SCREENCODER_ARK_KEY`，不落盘记忆/仓库
  - 产出：`data/output/test1_layout_final.html`（其余中间物在 `data/tmp`、`data/output`）
- **已验证**：语法 OK + 5 处补丁目标字符串均存在 + `--help` 正常。

### 唯一剩余阻塞（前置条件）
⚠️ **当前无可用 VLM Key**：仓库 `doubao_api.txt` 的 Ark key 与 `backend/.env` 的 Ark key 均实测 401「key status not active」；项目内/环境变量无 DashScope/Anthropic/Gemini 等其他 key。
Stage A 阶段 1（block_parsor）/ 阶段 2（html_generator）强依赖在线 VLM，缺 key 无法产出初始 HTML。
→ **拿到任一有效视觉 Key 即可一键跑通**：`set SCREENCODER_ARK_KEY=ark-xxx && .venv/Scripts/python.exe run_screen2code.py --image data/input/test1.png --model doubao-seed-2-1-turbo-260628`

### 后续（本次不做，待你授权）
- Phase 后续-A：把 Stage A 高保真 HTML 当富参考，接 fork 各栈生成（D1 的 A 方案）
- Phase 后续-B：写 `ingest.py` 把产物按约定落入 `e2e_runs/<run_id>/code/variants/<stack>/`（D2 的 A 方案）
- 实现时遵守 git worktree 规则（新功能分支走 worktree，不同目录切分支）

