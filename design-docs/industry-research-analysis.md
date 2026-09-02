# 业界开源项目调研分析报告

> 调研日期：2026-09-01（初版） · 2026-09-02（增补：App Builder 生态 / 纯本地路线 / 停更确认 / GitHub API 一手验证 / 学术项目 / Figma MCP 生态）
> 调研目标：对比 screenshot-to-code 与业界优秀开源项目，从需求/架构/方案/模块设计/开发/测试/维护/体验/迭代质量等角度分析（区分存量 vs 增量）
> 数据来源：GitHub API 直接验证（2026-09-02 08:18 GMT+8），非搜索引擎二手转述

## 1. 调研对象

### 1.1 直接竞品（图片/设计 → 前端代码，单次生成）

| 项目 | 定位 | 技术栈 | Stars | 关键特性 |
|---|---|---|---|---|
| screenshot-to-code (abi) | 截图→前端代码 | Python/FastAPI + React/Vite + 多模型 | 76,987 | 多 LLM 多变体、Agent 工具调用、Playwright 自检、录屏→原型、MIT |
| Flame-Code-VLM | 专用 VLM 截图→代码 | Siglip + DeepSeek Coder | 562 | 3 阶段训练、数据合成管线（进化/瀑布/增量）、权重开源、Apache 2.0 |
| emilwallner/Screenshot-to-code | 深度学习老祖宗 | Keras + TensorFlow + pix2code | 16,497 | **2024-08 后无新提交**、Bootstrap 版 97% 准确但仅 16 token |
| gojodennis/OpenKombai | 纯本地 LLM 截图→代码 | FastAPI + Ollama + Llama 3.2 Vision + Qwen 2.5 | 18 | 零 API 成本、隐私优先、React+Tailwind+Lucide、MIT |
| tldraw/make-real (原 draw-a-ui) | tldraw 画布手绘→HTML | Next.js + tldraw 4.4 + React 19 + AI SDK | 5,425 | **Public archive**（2026-02-18 归档）、fork 自 SawyerHood/draw-a-ui(13,582) |

### 1.2 AI App Builder（截图/prompt → 完整应用）

| 项目 | 定位 | 技术栈 | Stars | 关键特性 |
|---|---|---|---|---|
| wandb/openui | 描述 UI→实时渲染→多框架导出 | Python + uv + LiteLLM + React 前端 | 22,531 | v0 的开源替代、支持 Ollama/Groq/Gemini/Anthropic 等、Apache 2.0、2026-08 活跃 |
| dyad-sh/dyad | 本地优先 AI app builder | Electron + TS + React + Lexical + Drizzle | 21,365 | Lovable/v0/Bolt 的本地替代、版本历史+Git+E2E 测试、2026-09 活跃 |
| stackblitz-labs/bolt.diy | 开源版 bolt.new | Remix + Vite + WebContainers + Electron | 19,833 | **19 个 provider**、动态模型发现、MIT、2026-02 后无新提交 |
| onlook-dev/onlook | "设计师的 Cursor" | Next.js + Tailwind + tRPC + Supabase + Bun | 26,621 | 类 Figma 可视化编辑、分支化设计实验、Apache 2.0、2026-08 活跃 |

### 1.3 视觉闭环（生成→截图→对比→迭代）

| 项目 | 定位 | 技术栈 | Stars | 关键特性 |
|---|---|---|---|---|
| BuilderIO/micro-agent | TDD + 视觉匹配循环 | LLM + Playwright 视觉匹配 | 4,327 | 生成→测试→视觉对比→迭代、**2024-11 后停更**、MIT |
| imugi | SSIM + 像素差异热图 | Python | - | 局部裁剪 + DOM computed styles |
| screenshot-to-html | Playwright 迭代渲染 | Playwright | - | 按布局/间距/颜色/字体迭代 |
| visual-diff | 实现 vs Figma 并排对比 | - | - | 叠加 / difference-mode 比较 |

### 1.4 学术/论文路线（2026-09-02 增补）

| 项目 | 定位 | 技术栈 | Stars | 关键特性 |
|---|---|---|---|---|
| leigest519/ScreenCoder | UI 截图→HTML/CSS | Python + UIED + 多 agent | 2,973 | 港中文 MMLab 论文(arXiv:2507.22827)、多 agent 架构(Grounding→Planning→Generation)+ UIED 组件检测 + 匈牙利算法图片匹配、支持 Doubao/Qwen/GPT/Gemini、有 ScreenBench benchmark(1000 对)、Apache 2.0、**代码停在 2025-10 但 issue/PR 2026-08 仍活动** |
| tonybeltramelli/pix2code | 截图→GUI 代码 | Python + 深度学习 | 12,022 | emilwallner 的祖先项目、Apache 2.0、2024-05 后无新提交 |
| ashnkumar/sketch-code | 手绘草图→HTML | Python + Keras | 5,143 | MIT、2026-08 有提交(可能只是依赖升级) |
| mostafasadeghi97/design2code | 设计截图→HTML/CSS | Python | 680 | MIT、2026-07 活跃 |

### 1.5 Figma MCP 生态（2026-09-02 增补）

| 项目 | 定位 | 技术栈 | Stars | 关键特性 |
|---|---|---|---|---|
| GLips/Figma-Context-MCP | Figma 布局→MCP→AI agent | TypeScript + MCP | 15,752 | 给 Cursor 等 AI coding agent 提供 Figma 布局信息、MIT、2026-08 活跃 |
| grab/cursor-talk-to-figma-mcp | Agent ↔ Figma 双向 MCP | TypeScript + MCP | 6,988 | TalkToFigma:Agent 读写 Figma、修改设计、MIT、2026-07 活跃 |
| bernaferrari/FigmaToCode | Figma→多栈代码 | Figma 插件 + AltNode IR | 5,166 | 原 riccardoperra/FigmaToCode 转移、HTML/Tailwind/Flutter/SwiftUI、GPL-3.0、2026-08 活跃 |

### 1.6 纯文本 LLM 视觉增强（2026-09-02 增补）

| 项目 | 定位 | 技术栈 | Stars | 关键特性 |
|---|---|---|---|---|
| Anionex/agent-vision-toolkit | 给纯文本 LLM 装视觉能力 | Python + CLI 工具箱 + 本地代理 | 1,133 | 工具箱(glance/ground/detect/trace/crop)+ 代理、支持 Codex/Claude Code/Pi/OpenCode、MIT、2026-08 活跃 |

### 1.7 AI 设计 Skill 包（2026-09-02 增补，非直接竞品但相关）

| 项目 | 定位 | 技术栈 | Stars | 关键特性 |
|---|---|---|---|---|
| leonxlnx/taste-skill | AI 编程助手的设计品味 skill 包 | Skill 包 + Markdown | 83,318 | **非 screenshot-to-code 工具**,但含 `image-to-code-skill` 子模块(图片→分析→代码)、MIT、2026-08 活跃 |

### 1.8 已在前期调研中收录的项目（保留）

| 项目 | 定位 | 技术栈 | Stars | 关键特性 |
|---|---|---|---|---|
| FigmaToCode（即 bernaferrari/FigmaToCode） | Figma 设计稿→多框架代码 | Figma 插件 + AltNode IR | 5,166 | 框架无关中间表示、HTML/Tailwind/Flutter/SwiftUI |
| TRIM (Token Reduction) | VLM KV-cache 优化 | CLIP 指标 token 缩减 | 论文 | 67% KV cache 减少、30% 首 token 加速 |
| Text or Pixels (EMNLP 2025) | 文本渲染为图片 | 多模态 token 节省 | 论文 | ~50% token 节省 |

## 2. 多角度分析（存量 vs 增量）

### 2.1 需求

| 维度 | 存量（当前 fork 已有） | 增量（业界启发的新需求） |
|---|---|---|
| 输入源 | ADB 截屏 + UI Automator | Figma 插件直连（FigmaToCode 启发） |
| 输出栈 | 6 web + 5 native (fork 扩展) | 框架无关 IR 中间层（FigmaToCode AltNode） |
| Token 预算 | 无预算控制 | 多模态 token 预算上限（TRIM 启发） |
| 验证循环 | validate_code 语法检查 | 视觉匹配 TDD 循环（micro-agent 启发） |

**关键发现**：FigmaToCode 的 AltNode 中间表示是架构级启示——一次解析，多栈输出，比当前"每栈独立 prompt"更 DRY。

### 2.2 架构

| 维度 | 存量 | 增量 |
|---|---|---|
| 提示词架构 | 4 文件硬编码 `SYSTEM_PROMPT` → 已修复为 `get_system_prompt(stack)` 路由 | FigmaToCode IR 架构：解析层 → IR → 多栈 codegen |
| 模型路由 | `model_router.py` 按 stack 路由 | 火山引擎模型自动路由（按 token 预算选模型） |
| Agent 状态 | `AgentFileState` 多文件模型 | 扩展为多文件 + 多视图（如 Compose 的 .kt + preview.html） |
| Token 治理 | `costs/` 模块已建但未接入 | 6 项优化策略已实现（T1-T5 接入、T6 扩展路由） |

**架构断点修复**：
- B1 系统提示硬编码 → `system_prompt_router.py` ✅
- B2 Stack Literal 缺原生栈 → `prompt_types.py` 扩展 12 栈 ✅
- B3 ADB 数据未注入 prompt → `policies.py` 的 `build_adb_data_policy` + T4 截断 ✅

### 2.3 方案

| 维度 | 存量 | 增量 |
|---|---|---|
| 图片处理 | `detail: "high"` 全分辨率发送 | T1: 768px JPEG 压缩 → ~80% token 减少 |
| 历史 token | 保留全部历史图片 | T5: 截断旧图片，保留最近 2 轮 |
| Skeleton 截断 | `truncate_skeleton` 定义但未调用 | T4: 接入 `build_adb_data_policy` ✅ |
| 多模态调用 | 每栈独立 vision 调用 | T2: 1-Vision + N-Text 批处理（待实现） |
| Prompt caching | 无 | T3: 前缀缓存（待实现） |
| 国产模型 | 8 个 doubao/qwen 模型已注册 | T6: `model_router` 扩展 6 个新栈路由 ✅ |

### 2.4 模块设计

| 维度 | 存量 | 增量 |
|---|---|---|
| `system_prompt_router.py` | 不存在 | **新建**：`get_system_prompt(stack)` 路由 12 栈 |
| `image_compressor.py` | 不存在 | **新建**：768px JPEG 压缩 + PIL 优雅降级 |
| `history_truncator.py` | 不存在 | **新建**：按轮次截断历史图片 |
| `prompt_compressor.py` | `truncate_skeleton` 未接入 | **接入** `policies.py` |
| `validate_code.py` | 6 栈验证 | **扩展**：+winui3 XAML 验证 |
| `codegen/utils.py` | 仅 HTML 提取 | **扩展**：多栈代码提取（Kotlin/QML/JSONL/XAML） |
| `model_router.py` | 7 栈路由 | **扩展**：+6 个原生栈路由 |
| `stacks.ts` (前端) | 6 web 栈 | **扩展**：+6 个原生栈下拉选项 |
| `prompt_types.py` | 6 栈 Literal | **扩展**：+6 个原生栈 |

### 2.5 开发

| 维度 | 存量 | 增量 |
|---|---|---|
| 分支策略 | 单目录切分支 | **Git worktree 并行开发**（3 个 worktree） |
| 代码隔离 | 无 | 3 个独立 worktree：`-spr` / `-tok` / `-compose` |
| CI/CD | OCR review workflow 已建 | PR 触发 OCR 检视合入主干 |

### 2.6 测试

| 维度 | 存量 | 增量 |
|---|---|---|
| 单元测试 | 9 个 pre-existing errors（`ANTHROPIC_BASE_URL` 缺失） | 本次修改未引入新错误 |
| 模块测试 | 无 | **新增**：8 栈系统提示路由测试、4 项 token 优化测试、4 栈 codegen 提取测试、winui3 验证测试 |
| 类型检查 | pyright + tsc | stacks.ts 无类型错误 |
| 视觉回归 | 无 | micro-agent 启发：截图 vs 渲染对比（待实现） |

### 2.7 维护

| 维度 | 存量 | 增量 |
|---|---|---|
| 模型变更 | 手动改 `llm.py` 枚举 | `MODEL_PROVIDER` 字典已集中管理 |
| 新栈接入 | 改 4+ 文件 | **路由模式**：`get_system_prompt(stack)` 1 处 |
| 提示词更新 | 散布在 4 个文件 | **集中**到 `system_prompt_router.py` |
| Fork 同步 | upstream remote 已配 | upstream/main = merge base（无上游新 commit） |

### 2.8 体验

| 维度 | 存量 | 增量 |
|---|---|---|
| 栈选择 | 6 个 web 栈 | **12 个栈**（6 web + 6 native，native 标记 inBeta） |
| 响应速度 | 全分辨率图片 → 慢 | T1 压缩 → 更快 |
| 成本 | 无控制 | T1+T4+T5 → ~65% token 节省 |

### 2.9 迭代质量

| 维度 | 存量 | 增量 |
|---|---|---|
| OCR 检视 | PR #5 已验证 | 本次 PR 将触发 OCR 自动检视 |
| 代码质量 | 无系统检查 | pyright + pytest + pnpm lint + OCR |
| 知识积累 | `.workbuddy/memory/` | 每日工作日志 + 项目记忆 |

## 3. 核心启示

### 3.1 FigmaToCode AltNode IR（架构启示）
- **当前痛点**：每栈独立系统提示，12 栈 = 12 套指令维护
- **业界方案**：Figma → AltNode IR → 多栈 codegen（一次解析，多栈输出）
- **适用性**：中短期保持路由模式；长期可引入 IR 层

### 3.2 micro-agent TDD 循环（质量启示）
- **当前痛点**：`validate_code` 仅做语法检查，无法验证视觉一致性
- **业界方案**：生成 → Playwright 截图 → 与设计稿对比 → 迭代修复
- **适用性**：web 栈可直接复用；native 栈需自定义预览渲染

### 3.3 TRIM + Text-or-Pixels（Token 启示）
- **当前痛点**：多模态 token 消耗大（每截图 ~1-2K tokens）
- **业界方案**：CLIP 指标筛选关键 token（67% KV cache 减少）、文本渲染为图片（~50% 节省）
- **本次实现**：T1 图片压缩 + T4 skeleton 截断 + T5 历史截断 → 预估 ~65% 节省

### 3.4 Flame-Code-VLM（训练启示）
- **当前痛点**：依赖通用 GPT-4/Gemini，非代码生成专用
- **业界方案**：Siglip 视觉编码 + DeepSeek Coder 解码，3 阶段训练，数据合成管线（进化/瀑布/增量）
- **适用性**：长期可训练 fork 专用 VLM；短期用国产模型路由降本
- **2026-09-02 更新**：实测 561 star，权重 + 数据集 + 评估套件全开源(Apache 2.0)；仍是唯一走"自研 VLM + 开源权重"路线的项目

### 3.5 App Builder 生态启示（2026-09-02 增补）
- **当前痛点**：abi 仅生成单页代码片段，不生成完整应用 + 版本管理 + 数据库
- **业界方案**：
  - **dyad**：Electron 本地应用 + Git 版本历史 + AI E2E 测试 + Supabase/Neon 集成
  - **bolt.diy**：19 个 provider 动态模型发现 + 文件锁定(防 AI 改指定文件) + Web URL 内容抓取
  - **onlook**：类 Figma 可视化画布 + 分支化设计实验 + 检查点恢复
- **适用性**：
  - 短期：借鉴 bolt.diy 的"文件锁定"机制(保护已稳定的代码段不被 AI 覆盖)
  - 中期：借鉴 onlook 的"分支化设计实验"思路，与 fork 已有的 variants 系统对齐
  - 长期：借鉴 dyad 的"版本历史 + 检查点"完整方案

### 3.6 纯本地路线启示（2026-09-02 增补）
- **业界方案**：OpenKombai 用 Llama 3.2 Vision + Qwen 2.5 Coder via Ollama，零 API 成本
- **适用性**：fork 已注册 8 个 doubao/qwen 国产模型；如需完全离线场景，可参考 OpenKombai 的 Ollama 集成方式
- **价值**：对数据隐私敏感的企业客户场景，提供"零外发"部署选项

### 3.7 视觉闭环生态现状（2026-09-02 增补）
- **现状**：micro-agent 2024-11 后停更，imugi/screenshot-to-html/visual-diff 采用量都远小于 abi
- **判断**：视觉 diff 闭环仍是方向，但开源生态无成熟主力，需自研
- **本 fork 进展**：已加 Playwright 截图预览(自检)，但仍缺"diff → 反馈 → 修复"完整循环

### 3.8 ScreenCoder 多 agent 架构启示（2026-09-02 增补，深度验证）
- **业界方案**：港中文 MMLab 论文(arXiv:2507.22827 v2, 2025-10-20)，模块化多 agent 架构
  - **三阶段 agent**：
    - **Grounding**：MLLM 通过文本提示(如"Where is the sidebar?")检测组件，返回边界框+标签，NMS 去重+启发式回退
    - **Planning**：确定性 Visual-to-Structural Tree Mapping 算法，绝对像素→响应式百分比，指定 CSS Grid 容器
    - **Generation**：遍历布局树，自适应提示生成 HTML/CSS
  - **补充**：Placeholder Mapping 用 UIED 模型 + 匈牙利算法做最优匹配，恢复原始图片素材
- **ScreenBench 性能对比（关键数据）**：
  - ScreenCoder (Agentic) 在 Block/Text/Position/Color/CLIP **五项全部 SOTA**
  - vs GPT-4o：Block +0.023，Position +0.030
  - vs Gemini-2.5-Pro：Block +0.027，Color +0.039
  - ScreenCoder (Finetuned) 略低于 Agentic 版本，但仍超 GPT-4o
- **后训练收益**（Qwen2.5-VL 基座，SFT+RL）：
  - SFT（9,000 对）：Position +0.092（最大提升）
  - RL（1,000 对，GRPO 算法）：Block +0.017，Position +0.037
  - **RL 奖励函数**：ℛ(x,y) = -MSE(x, Render(y))，直接优化像素级视觉保真度
  - 总计 Base→Final：Position +0.129，Color +0.086
- **ScreenBench**：1,000 对 image-code pairs，来自当代 web 应用，比 Design2Code 的 484 样本更大更现代
- **活跃度判断（2026-09-02 验证）**：
  - stars=2,973, forks=317, 3 人团队(leigest519 + Jimmyzhengyz + yxwan123)
  - **代码提交停在 2025-10-22**（已 10 个月无新代码）
  - 但 issue/PR 在 2026-08 仍有活动（主要是外部 PR #22 asset-aware pipeline、PR #23 项目页面链接）
  - HF Space lastModified=2026-08-24，likes=83（demo 可用）
  - 作者对 issue 回应少（大部分 0 评论）
  - **判断：学术发布型项目，非持续维护的工程项目**
- **与 abi 差异**：abi 是一次性整页生成；ScreenCoder 是分块检测+分块生成+图片复用
- **适用性**：中期可借鉴 ScreenCoder 的"组件检测→分块生成"思路，提升复杂页面还原度；RL 奖励函数 ℛ=-MSE 可直接用于本 fork 的视觉闭环
- **价值**：ScreenBench 可作为本 fork 评估集的补充；RL 奖励函数设计是视觉闭环的关键参考

### 3.9 Figma MCP 生态启示（2026-09-02 增补）
- **业界方案**：
  - `GLips/Figma-Context-MCP`(15.7k star)：MCP server，给 AI coding agent 提供 Figma 布局信息
  - `grab/cursor-talk-to-figma-mcp`(7k star)：Agent ↔ Figma 双向 MCP，可读写修改
- **与 fork 的关系**：fork 当前从截图提取，Figma MCP 路线是直接从设计源文件提取，精度更高
- **适用性**：中期可引入 Figma MCP 输入源，作为截图输入的补充(参考 reuse-reference-report.md §4.2 FigmaToCode)
- **价值**：Figma 设计稿 → MCP → AI agent → 代码，跳过"截图"中间环节，减少信息损失

### 3.10 纯文本 LLM 视觉增强启示（2026-09-02 增补）
- **业界方案**：`Anionex/agent-vision-toolkit`(1.1k star) 给纯文本 LLM 装视觉能力
  - 5 个 CLI 工具：glance(问答/OCR) / ground(定位) / detect(清点) / trace(SVG 提取) / crop(裁剪)
  - 任务感知描述：提取"为什么要看这张图"的意图，生成焦点提示
  - 代理方式：透明本地代理，让 Codex/Claude Code 等纯文本 agent 也能"看图"
- **与 fork 的关系**：fork 已注册 8 个 doubao/qwen 国产模型，部分是纯文本模型
- **适用性**：可借鉴 agent-vision-toolkit 的工具箱设计，让纯文本国产模型也能处理图片输入
- **价值**：降低多模态模型依赖，让纯文本模型也能参与截图转代码工作流

### 3.11 taste-skill 设计品味启示（2026-09-02 增补，非直接竞品）
- **业界方案**：`leonxlnx/taste-skill`(83k star) 是 AI 编程助手的设计 skill 包
  - 含 `image-to-code-skill` 子模块：图片→生成参考网站→分析→实现前端
  - 3 个核心 dial：VARIANCE / MOTION / DENSITY
  - 多种风格：soft-skill / minimalist-skill / brutalist-skill 等
- **与 fork 的关系**：不是直接竞品，是给 AI coding agent 用的"设计品味"skill
- **适用性**：fork 的 prompt 工程可借鉴其"设计 dial"概念，让用户调节生成风格
- **价值**：83k star 说明"AI 生成代码的视觉品味"是巨大需求，fork 可在 prompt 层做风格化

## 4. 本次实现总结

### 4.1 System Prompt Router (feature-system-prompt-router)
- **新建** `system_prompt_router.py`：`get_system_prompt(stack)` 路由 12 栈
- **替换** 4 处硬编码 `system_prompt.SYSTEM_PROMPT`
- **扩展** `prompt_types.py` Stack Literal（+6 原生栈）
- **扩展** `validate_code.py`（+winui3 XAML 验证）
- **扩展** `model_router.py`（+6 原生栈路由）
- **扩展** `stacks.ts`（+6 原生栈前端选项）

### 4.2 Token Optimization (feature-token-optimization)
- **T1** `image_compressor.py`：768px JPEG 压缩，接入 `image.py`
- **T4** `truncate_skeleton` 接入 `policies.py` 的 `build_adb_data_policy`
- **T5** `history_truncator.py`：历史图片截断，接入 `from_history.py`
- **T6** `model_router.py` 扩展（已在 SPR worktree 完成）

### 4.3 Compose Mainline (feature-compose-mainline)
- **复制** SPR 路由模式（保持 worktree 独立）
- **扩展** `codegen/utils.py`：多栈代码提取（HTML/Kotlin/QML/JSONL/XAML）
- **保留** `AgentFileState` 多文件模型（已有，无需改）

---

## 5. 2026-09-02 增补：选型矩阵与交叉引用

### 5.1 按场景选型矩阵

| 场景 | 推荐 | 理由 |
|---|---|---|
| 多栈 + 多模型对比 + 自托管 | **abi/screenshot-to-code**（本仓库） | 76,987 star，6 web + 6 native 栈，多模型路由，Playwright 自检 |
| 零成本 + 隐私 + 纯本地 | **gojodennis/OpenKombai** | Llama 3.2 Vision + Qwen 2.5 via Ollama，零 API key |
| 自研模型 / 训练数据合成研究 | **Flame-Code-VLM** | 唯一开源 VLM 权重 + 数据集 + 评估套件 |
| 从想象描述生成 UI + 实时对话改 | **wandb/openui** | v0 开源替代，LiteLLM 接任意模型 |
| 生成完整应用 + 版本管理 + 本地控制 | **dyad-sh/dyad** | Lovable/v0/Bolt 本地替代，Electron+TS |
| 任意 LLM + 最多 provider + 全栈 | **stackblitz-labs/bolt.diy** | 19 个 provider，动态模型发现 |
| 设计师向可视化编辑(Figma 式) | **onlook-dev/onlook** | 类 Figma 画布 + 分支化设计实验 |
| 追求高还原(像素级一致) | **abi + 外层叠视觉 diff 闭环** | 单次生成 70-80%，必须叠 micro-agent / imugi 模式 |
| 手绘草图 → 代码 | **tldraw/make-real**(已 archive) 或 **ashnkumar/sketch-code** | make-real 不再更新；sketch-code 仍可参考 |
| 学术研究 / 多 agent 架构参考 | **leigest519/ScreenCoder** | 港中文论文，组件检测→分块生成，有 ScreenBench |
| Figma 设计稿直连(非截图) | **GLips/Figma-Context-MCP** | 15.7k star，MCP 跳过截图环节 |
| 纯文本 LLM 处理图片 | **Anionex/agent-vision-toolkit** | 工具箱+代理，让纯文本模型"看图" |
| AI 设计风格化 | **leonxlnx/taste-skill** | 83k star，设计 dial(VARIANCE/MOTION/DENSITY) |

### 5.2 与 reuse-reference-report.md 的交叉引用

本文档新增的项目，在 `reuse-reference-report.md` 中的对应关系：

| 本文档项目 | reuse-reference-report 中的定位 | 复用等级 |
|---|---|---|
| **micro-agent** | §4.1 TDD + 视觉匹配循环 | ⭐⭐ 架构参考 |
| **FigmaToCode** (bernaferrari) | §4.2 AltNode IR 中间表示 | ⭐⭐ 架构参考 |
| **Flame-Code-VLM** | §5 长期参考 | ⭐ 长期 |
| **Compose Driver** | §2.1 直接复用 | ⭐⭐⭐ 立即 |
| **ComposablePreviewScanner** | §2.2 直接复用 | ⭐⭐⭐ 立即 |
| **Paparazzi** | §3.1 短期适配 | ⭐⭐ 短期 |
| **Roborazzi** | §3.2 短期适配 | ⭐⭐ 短期 |
| **OpenKombai**（新） | 未收录，建议新增 §3.3 | ⭐⭐ 短期(离线场景) |
| **onlook**（新） | 未收录，建议新增 §4.3 架构参考 | ⭐⭐ 架构(分支化设计) |
| **bolt.diy**（新） | 未收录，建议新增 §4.4 架构参考 | ⭐⭐ 架构(文件锁定+多 provider) |
| **ScreenCoder**（新） | 未收录，建议新增 §4.5 架构参考 | ⭐⭐ 架构(组件检测→分块生成) |
| **GLips/Figma-Context-MCP**（新） | 未收录，建议新增 §4.6 | ⭐⭐ 架构(Figma 直连) |
| **agent-vision-toolkit**（新） | 未收录，建议新增 §3.3 | ⭐⭐ 短期(纯文本模型视觉) |
| **taste-skill**（新） | 未收录，建议新增 §4.7 参考 | ⭐ 参考(设计风格化) |

### 5.4 建议后续动作

- [ ] 在 `reuse-reference-report.md` §3 新增 OpenKombai 离线方案
- [ ] 在 `reuse-reference-report.md` §3 新增 agent-vision-toolkit 纯文本模型视觉增强
- [ ] 在 `reuse-reference-report.md` §4 新增 onlook 分支化设计参考
- [ ] 在 `reuse-reference-report.md` §4 新增 bolt.diy 文件锁定机制参考
- [ ] 在 `reuse-reference-report.md` §4 新增 ScreenCoder 组件检测→分块生成架构
- [ ] 在 `reuse-reference-report.md` §4 新增 GLips/Figma-Context-MCP Figma 直连方案
- [ ] 考虑为本 fork 设计 `visual_match.py` 视觉闭环模块(参考 micro-agent + Roborazzi AI 断言)
- [ ] 评估 ScreenBench 作为本 fork 评估集的补充
- [ ] 研究 taste-skill 的 VARIANCE/MOTION/DENSITY 三个 dial，看能否引入 fork 的 prompt 工程
