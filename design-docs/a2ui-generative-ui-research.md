# A2UI 生成方案确认 + 业界开源项目调研

> 调研日期：2026-09-02
> 调研目标：
> 1. 确认本 fork 当前 A2UI 生成的整体方案流程（证据来自代码，非推测）
> 2. 调研业界与 A2UI / Agent-Driven 生成式 UI 相关的优秀开源项目
> 数据来源：本仓库代码 grep + 官方 a2ui.org / Google A2UI 仓库 / InfoQ 2026-07 报道（一手）

---

## 一、当前 A2UI 生成整体方案流程（已确认）

入口为固化的一键流水线：

```
screenshot.png
   │  [Phase 1 · Vision]  describe_image()
   │     768px JPEG → base64 → doubao-seed-2-1-turbo-260628（1 次视觉调用）
   │     → inputs/ui_description.json
   ▼
   │  [Phase 2 · Generate]  generate_stacks(ui_desc, stacks=["a2ui", ...])
   │     对 a2ui 栈发 1 次纯文本调用（复用 ui_desc，不重复视觉）
   │     → e2e_runs/<run_id>/code/a2ui.jsonl
   ▼
   │  [Phase 3 · Inject]  当前仅落到 code/（决策 #1：仅生成代码，不接工程脚手架）
   ▼
   e2e_runs/<run_id>/code/a2ui.jsonl  +  manifest.json
   │
   ▼  [校验]  agent/tools/validate_code.py :: _validate_a2ui
   ▼  [预览]  e2e_demo/templates/a2ui/a2ui_runner.html（自研原生 JS 渲染器）
```

### 1.1 各阶段证据

| 阶段 | 实现位置 | 关键事实 |
|---|---|---|
| 入口 | `backend/e2e/cli.py` | `python -m e2e.cli --image X --stacks ...,a2ui --model M [--dry]`；a2ui 在 `ALL_STACKS` 注册表中 |
| Phase 1 视觉 | `backend/e2e/generate/core.py :: describe_image` | 1 次 vision 调用 → 结构化中文 UI 描述；图片压 768px JPEG |
| Phase 2 生成 | `backend/e2e/generate/core.py :: generate_stacks` | **逐栈 1 次 text 调用**，复用同一 `ui_desc`；单栈失败隔离；`finish_reason=="length"` 自动翻倍重试（封顶 24000 token）；httpx 超时 600s |
| A2UI prompt | `backend/e2e/common.py` STACKS["a2ui"].req | `JSONL 格式，每行一个 JSON 对象，合法类型: button/card/column/container/image/input/list/row/stack/text` |
| 校验 | `backend/agent/tools/validate_code.py :: _validate_a2ui` | 逐行 `json.loads` + jsonschema（allowed_types 同上 10 类）；空 / 非法 JSON 报错 |
| 渲染 | `e2e_demo/templates/a2ui/a2ui_runner.html` | 自研单文件原生 JS DOM 渲染器；`quick_verify.py` 转自包含 HTML 供 Edge headless 截图（CI 视觉闭环） |

> 注：早期还有 `generate_5stacks_combined.py`（一次性出 5 栈的 `===A2UI===` 段落）与 `gen_a2ui_html.py`（双栈 demo 脚本），属历史/验证性脚本，非主路径。

---

## 二、关键发现：本 fork 的 A2UI 是「自定义方言」，并非官方协议

### 2.1 与 Google 官方 A2UI 的差异

| 维度 | 官方 A2UI v0.9.1（Google，Apache 2.0） | 本 fork 的「A2UI」 |
|---|---|---|
| 消息信封 | `updateComponents` / `createSurface` / `dataModelUpdate` / `deleteSurface`，含 `"version":"v0.9"` + `catalogId` | 裸 JSONL 行，无信封、无 version、无 catalog |
| 组件模型 | 扁平 `"component":"Text"` + 属性平铺（`text`、`onClick` 动作名） | `"id"/"type"/"children"/"props"` 自定 type 集合 |
| 数据绑定 | JSON Pointer `{"path":"/user/name"}` + 独立 dataModel 消息 | 样本无绑定；prompt 未要求 |
| 树模型 | 邻接表（id 引用，✅ 思路一致） | 邻接表（id / `children`，思路一致） |
| 组件白名单 | 受信 catalog（Basic 目录：Row/Column/List/Text/Image/Icon/Video/Divider/Button/TextField/CheckBox/DateTimeInput/Slider/Card/Tabs/Modal），schema 校验 | 无 catalog / 无 schema 强制 |
| 渲染器 | 官方：Lit / Angular / Flutter(GenUI SDK) / React / Lynx + A2A / AG-UI / REST / WS / MCP 传输 | 自研单文件 `a2ui_runner.html`（vanilla JS）+ Python→HTML |
| Agent SDK | `pip install a2ui-agent-sdk`（版本协商、流式愈合、动态 catalog） | 无，全靠手写 prompt |

**结论**：本 fork 借用了 A2UI 的「邻接表 JSONL + 框架无关」核心思想并沿用了名字，但产物**不兼容官方协议、无法用任何官方渲染器/传输层渲染**，是平行发展的自定义方言。

### 2.2 仓库内三处 Schema 定义彼此不统一（已 grep 确认）

| # | 文件 | 字段约定 | 状态 |
|---|---|---|---|
| 1 | `backend/prompts/a2ui_system.py` | `id/type/children/style/bind/onClick`；文件 `surface.jsonl`；类型含 container/card/column/row/text/button/input/image/list/stack | **死代码**：文件头自注「not yet wired into the prompt builder」，全仓库无任何 import（已 grep 验证） |
| 2 | `backend/generate_5stacks_combined.py` + `backend/e2e/common.py` | 类型 10 类 `button/card/column/container/image/input/list/row/stack/text`；未规范 `style`/`props` 字段名 | 生成主路径（combined / 一键流水线） |
| 3 | `e2e_demo/templates/a2ui/a2ui_runner.html` + `llm_a2ui.jsonl` 样本 | `id/type/children/props`，额外类型 `switch/dropdown/divider`；树构建依赖 `parent` 字段 | 渲染器侧 |

**风险**：
- 生成侧（#2）教模型用 `children`/`props`，但渲染器侧（#3）的 `buildTree` 优先读 `parent` 字段；生成样本用 `children` 且**不写 `parent`** → 存在渲染树构建错位隐患，需实际跑通验证。
- `a2ui_system.py`（#1）定义的 `style` 字段与主路径 `props` 不一致，且始终未被使用。
- 三套定义并存，任何一处改了都不会联动，长期必然格式漂移。

---

## 三、业界相关优秀开源项目调研（A2UI / Agent-Driven UI 专项）

### 3.1 官方标准与核心生态（首选对齐对象）

| 项目 | 定位 | 技术栈 / 许可 | 亮点 | 与 fork 的关系 |
|---|---|---|---|---|
| **google/A2UI** | Agent-Driven 声明式 UI 协议（标准） | 规范 + 渲染器 + 传输，Apache 2.0 | v0.8 / v0.9.1(当前) / v1.0 RC；官方渲染器 Lit / Angular / Flutter(GenUI SDK) / React / Lynx；传输 A2A / AG-UI / REST / WS / MCP；`a2ui-agent-sdk`（pip，含版本协商、流式愈合、动态 catalog） | **直接对标**：fork 的 A2UI 应优先对齐此标准以复用生态 |
| **CopilotKit** | Agent↔前端 事件协议 + A2UI 集成 | TypeScript，MIT/Apache | AG-UI 协议（运行时事件传输，与 A2UI 互补：A2UI=UI 规范，AG-UI=传输）；A2UI Composer 可视化构建器；day-zero 兼容 | 接入即可获得完整「生成→传输→渲染」闭环 |
| **A2A (Agent2Agent) Protocol** | A2UI 消息的官方传输层 | 协议，Google | A2A 1.0 原生承载 A2UI 消息，跨信任边界 | 企业多 agent 场景的传输底座 |

### 3.2 同类「声明式 UI IR / 生成式 UI」方案

| 项目 | 定位 | 许可 | 亮点 | 与 fork 的关系 |
|---|---|---|---|---|
| **FigmaToCode (bernaferrari)** | Figma→框架无关 IR→多栈 codegen | GPL-3.0 | AltNode 中间表示：一次解析多栈输出（HTML/Tailwind/Flutter/SwiftUI） | **最贴近本 fork「多栈输出」目标**；已在 `industry-research-analysis.md` 收录为 P2 架构参考（IR 层） |
| **Mesop (Google)** | Python 声明式 UI 框架，面向 AI/agent | Apache 2.0 | 用 Python 直接描述 UI，快速搭 agent 界面（非线协议，单框架） | 同赛道轻量替代，适合内部工具 |
| **Vercel AI SDK generative UI / json-renderer** | Web 端生成式 UI | MIT | RSC 流式生成组件，json-renderer 参考实现 | Web 端生成式 UI 参考 |
| **Oracle Agent Spec / MCP Apps** | agent UI 相邻协议 | — | 企业 agent 交互规范 | 相邻标准，可对比取舍 |
| **syntux** | 反向视角 | — | 质疑 chatbot 式生成 UI 的「一次性 / 不可缓存」问题，主张确定性 Web 组件 | 设计哲学提醒：避免过度依赖 LLM 即兴生成 UI |

### 3.3 与「截图转代码」主线相关（已在 `industry-research-analysis.md` 收录，交叉引用）

| 项目 | 可借鉴点 |
|---|---|
| **abi/screenshot-to-code**（本 fork 上游） | 6 web + 6 native 栈、多模型路由、Playwright 自检 |
| **leigest519/ScreenCoder** | 多 agent（检测→分块→生成）+ ScreenBench 评估集；RL 奖励 ℛ=-MSE 可直接用于本 fork 视觉闭环 |
| **BuilderIO/micro-agent + Roborazzi** | 生成→截图→对比→迭代闭环（本 fork 缺，可补） |

---

## 四、建议（对齐 vs 自研 决策）

| 选项 | 内容 | 适用时机 | 收益 |
|---|---|---|---|
| **A（推荐中期）** | 把 fork 的 A2UI 输出对齐到官方 **v0.9.1 schema**（信封 `updateComponents` + `version` + `catalogId` + JSON Pointer 绑定） | 需要跨平台渲染 / 接真实客户端时 | 直接复用官方 Lit/React/Flutter 渲染器 + `a2ui-agent-sdk`，省自研 runner 维护，与业界工具链互通 |
| **B（短期必做）** | 先统一仓库内三处 schema 定义；将 `a2ui_system.py` 真正接入 prompt 路由（或删除死代码）；明确 `style` vs `props`、`children` vs `parent` | 本周 | 消除格式漂移，避免生成/渲染错位 |
| **C（长期）** | 引入 FigmaToCode 式 **IR 层**：截图→IR→A2UI + 其他栈，一次解析多栈输出 | 多栈规模上来后 | DRY，比「每栈独立 prompt」更省 token、更易维护 |
| **D（质量）** | 视觉闭环：借鉴 ScreenCoder RL 奖励 + micro-agent 截图对比，补「生成→渲染→diff→修复」 | 与 validate_code 集成 | 把验证从「语法正确」提升到「视觉一致」 |

---

## 五、一句话定位

> 本 fork 已跑通「截图 → 1 次视觉 → A2UI JSONL → 自研渲染器」的工程链路，但 A2UI 产物是**自定义方言**，与 Google 官方协议不互通、且内部三套 schema 未对齐；业界已有成熟标准（google/A2UI + CopilotKit AG-UI + 官方多框架渲染器 + Agent SDK），建议中期对齐、短期先统一内部定义。
