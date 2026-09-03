# GUI Agent 整体流程调研与开源复用地图

> 续篇：`gui-agent-perception-memory-survey.md`（感知/记忆两专项）→ 本文补全**整体流程闭环**与**可完全复用的开源项目清单**。
> 日期：2026-09-02 · 调研范围：2024-2026 代表性综述与系统

---

## 一、GUI Agent 整体流程：业界统一的闭环模型

四篇代表性综述对流程的拆法高度收敛（模块名不同、信息流一致）：

| 来源 | 拆法 |
|---|---|
| GUI Agents with Foundation Models (arXiv 2411.4890) | **五模块**：GUI Perceiver → Task Planner → Decision Maker → Memory Retriever → Executor |
| Survey on (M)LLM-Based GUI Agents (2504.13865) | **四模块**：Perception → Exploration → Planning → Interaction |
| GUI Agents: A Survey (2412.13501) | **四能力**：Perception / Reasoning / Planning / Acting |
| 手机自动化综述 (2504.19838) | **POMDP 建模**：感知(树+截图+SoM+OCR) / 大脑(记忆+规划+反思) / 行动(触摸+手势+系统命令) |

统一成一个执行循环：

```
        ┌────────────────────────────────────────────────┐
        │                    记忆/知识                     │
        │   STM(轨迹上下文)  LTM(元素文档/经验/UTG)  外部知识  │
        └───────────────▲──────────────────▲─────────────┘
                        │                  │
 用户指令 ──► ①感知 ──► ②规划 ──► ③决策 ──► ④执行 ──► 环境状态变化
 (截图+UI树)   (CoT分解/   (grounding:   (点击/滑动/
               子任务)     语言→元素→坐标)  输入/系统键)
                        │                  │
                        └── ⑤反思(Reflection)：验证执行结果、
                            检测死胡同、修正计划、回溯 ──┘
```

### 各阶段的工程要点（对 2504.13865 / 2411.4890 的提炼）

| 阶段 | 关键工程决策 | 代表做法 |
|---|---|---|
| ① 感知 | 文本树 vs 纯视觉 vs **混合**；上下文压缩（10万 token HTML → 精简元素表） | M3A(AndroidWorld)、SoM 标注(OmniParser)、A11y 树 + 截图双通道 |
| ② 规划 | ReAct 逐步 vs Plan-Then-Act 分层 vs MCTS/搜索式回溯；长任务是公认瓶颈 | UFO 双 agent 分层、DroidRun Manager+Executor、Mobile-Agent-v3 Notetaker 进度管理 |
| ③ 决策 | grounding 两步法：planner 出语义动作 → grounding 模型出坐标 | SeeAct-V + UGround（两模型解耦，AndroidWorld 30.6→44.0） |
| ④ 执行 | 结构化原子动作集（click/swipe/type/open_app/…）；GUI-API 混合动作层 | DroidRun 原子动作、UFO2 GUI+原生 API 统一层 |
| ⑤ 反思 | 步级 Critic（动作前后界面变化）+ 轨迹级 Critic（任务成败）；死胡同检测与回溯 | GUI-Critic-R1、Mobile-Agent-v3 双层 Critic、UFO2 speculative multi-action |

### 架构演进的三条主线

1. **单体 → 多智能体**：UFO（AppAgent+ActAgent）→ UFO2（HostAgent + 应用专用 AppAgent 池）→ Mobile-Agent-v3（planner/executor/reflector/notetaker 多角色，单一 GUI-Owl 模型实例化不同角色）
2. **截图-only → 混合感知**：UFO2 用 UIA(结构) + vision(视觉) 融合检测；DroidRun 主打 accessibility 结构化输入（token 少 12 倍、$0.075/任务）
3. **手工框架 → 数据自进化**：Mobile-Agent-v3 的「自我进化 GUI 轨迹生产链路」（任务生成 → 执行 → 双 Critic 筛选 → RL 微调闭环），与本 fork 的 OS-Genesis 反向任务合成路线同构

---

## 二、可完全复用的开源项目（许可证已核验）

「完全复用」= 许可证允许闭源/商用集成 + 代码可直接拿来做子系统，而非只借鉴思路。

### P0 级：直接拿来做「采集/探索/验证」子系统

| 项目 | 许可证 | 是什么 | 本项目复用方式 |
|---|---|---|---|
| **X-PLUG/MobileAgent**（阿里通义，含 Mobile-Agent-v1/v2/v3/E、GUI-Critic-R1） | **MIT** | 最强开源 GUI Agent 家族：GUI-Owl 7B/32B 模型 + v3 多智能体框架（规划/进度管理/反思/记忆/Notetaker）；AndroidWorld 73.3 | ① v3 的**多角色 prompt 与进度管理**结构直接套到遍历器升级（LLM 引导探索）；② **GUI-Critic-R1 反思模块**复用为生成代码的验证器；③ 中文文档/中文 App 生态最贴合国产模型 |
| **droidrun/droidrun** | **MIT** | Android/iOS LLM Agent 框架：ManagerAgent(规划)+ExecutorAgent(执行)+CodeActAgent(直接执行代码)+ScripterAgent(设备外计算)；原子动作集；多 LLM 后端(OpenAI/Anthropic/DeepSeek/Ollama) | **最值得整建制复用**：LLM-agnostic 设计可直连火山引擎/百炼；Manager/Executor 分层 + 原子动作与我们 `AdbBackend` 抽象一一对应——用 `UiBackend` 替换其 Portal APK 通道即可。AndroidWorld 声称 91.4% / $0.075/任务 |
| **microsoft/UFO (UFO2)** | **MIT** | Windows 桌面 AgentOS：HostAgent + AppAgent 池、UIA+视觉混合检测、GUI-API 统一动作层、PiP 隔离虚拟桌面 | **WinUI3 栈的现成答案**：fork 的第 6 栈 WinUI3 验证器可直接用其 UIA 控件检测 + 控制自动化模块（`ufo/` 下 AgentOS 组件按需摘取），省掉自研 Windows UIA 管线 |
| **google-research/android_world** | **Apache-2.0** | 116 任务 × 20 App 的动态基准环境 + M3A agent（a11y 树+截图混合感知的参考实现）+ 持久奖励信号 + 任务/评测框架 | ① **M3A 的感知格式化代码**直接搬（JSON 元素表+截图双输入，是混合感知的标准写法）；② 任务体系与 `step()` agent 接口作为遍历器「LLM 引导模式」的评测床 |
| **openatx/uiautomator2 + adbutils** | **MIT** | 常驻 JSONRPC 服务，dump ~200ms；设备管理 | 已在既定路线（P0-1），确认可整包复用 |
| **bytedance/Fastbot** | **MIT** | 高吞吐模型驱动遍历 + max.xpath.actions 手工引导配置 | 已既定，hyper-event 与引导配置格式可移植 |

### P1 级：感知增强与桌面/浏览器扩展

| 项目 | 许可证 | 复用方式 | 注意 |
|---|---|---|---|
| **microsoft/OmniParser V2/V3** | 代码 MIT；**icon_detect 权重 AGPL**（YOLOv8 遗传）；icon_caption (Florence-2) MIT；V3 的 YOLOv9-E detector **MIT** | 图标检测+功能描述，增强 SoM 导出与无 ui_tree 栈（如游戏/Canvas 界面）的感知 | **AGPL 权重不可闭源集成**——只可用 V3 YOLOv9-E（MIT 实现链）或自训；caption 模型无此问题 |
| **Genymobile/scrcpy**（server 部分） | Apache-2.0 | 视频流帧抓取替代 4K screencap+pull | 已在既定路线 |
| **UGround / SeeAct-V**（boyugou/android_world_seeact_v） | 学术开源 | planner+grounding 两步解耦的参考实现（30.6→44.0 的依据） | 权重许可需逐个核验，代码结构可借鉴 |
| **browser-use** | MIT | 若做 Web 栈（HTML 已支持）的 agent 验证 | 未在本轮逐一核验，落地前确认 |
| **DroidBot / DroidBot-LLM** | MIT | UTG 数据结构 + LLM 引导探索参考 | 已调研（前篇） |

### 明确**不可**复用（只可借鉴思路）

| 项目 | 许可证 | 原因 |
|---|---|---|
| UIHash | **GPL-3.0** | 传染性，不可集成进本 fork |
| OpenAI Operator / Claude Computer Use / AutoGLM | 闭源 | 只可对照其公开技术报告设计 |
| OmniParser V1/V2 icon_detect 权重 | AGPL | 见上 |

---

## 三、对本项目（screenshot-to-code fork）的落地映射

当前定位：**采集（ADB 遍历）→ 生成（6 栈代码）→ 验证（渲染截图比对）**。GUI Agent 整体流程的复用点按此分三段：

### 3.1 采集段：遍历器从「盲 DFS」升级为「LLM 引导探索」

```
现状：Traverser(结构签名去重 + DFS + BACK 回溯)  ← 纯规则，无认知
目标：+ LLM Explorer（可选模式）
      ├─ 感知：复用 M3A 格式（元素表 JSON + 768px 截图，已有 SoM 计划）
      ├─ 决策：LLM 对候选 Action 打分（未访问优先 + 语义价值）
      ├─ 反思：动作后 LLM 判断「状态变化是否符合预期」→ 预筛 UTG 边的 action_effect
      └─ 记忆：元素文档库（AppAgent 范式，前篇已规划）
```

- **第一优先复用 DroidRun 的 agent 编排**（Manager/Executor + 原子动作 + LLM-agnostic），我们的 `AdbBackend`/`UiBackend` 抽象恰好是其 Portal 通道的等价物
- Mobile-Agent-v3 的 Notetaker（跨应用任务的关键信息记录）对应遍历器的「跨 App 状态摘要」，可做 global_graph 的语义索引
- 模型：百炼 `glm-5.2`/`qwen3.7-max` 或火山 `doubao-seed-2-1-turbo`（均已有 key），不需要 GUI-Owl 专用模型即可起步

### 3.2 生成段：Agent 流程反向喂给代码生成

- UTG 边的 `action_effect`（元素文档库初版，前篇 P0）注入生成 prompt：「这个按钮点击后跳转站点选择页」→ 生成的代码行为与真实 UI 对齐
- Mobile-Agent-v3 的「操作前/后截图对比理解动作语义」思路：我们的 `<s, a, s'>` 三元组天然就是前后截图对

### 3.3 验证段：GUI Agent 作为「行为等价性」验证器

```
生成代码 → 渲染截图 → (现) 像素/骨架比对
                     → (增) GUI Agent 走查：
                        对生成 UI 做 SoM 标注 → LLM 逐元素回答
                        「与真机截图语义是否一致」→ 结构化差异报告
```

- GUI-Critic-R1（MIT，步级 Critic）的 prompt 结构可直接改造为「渲染前后语义比对」验证器
- UFO2 的 UIA 检测模块同时服务 WinUI3 栈的**采集**（桌面应用结构树）与**验证**

### 3.4 建议路线（增量、每步可独立交付）

| 步 | 内容 | 复用来源 | 规模 |
|---|---|---|---|
| 1 | SoM 标注导出（前篇已列 P0） | 自研（~半天） | 小 |
| 2 | M3A 感知格式化模块移植：元素表 JSON + 截图 → LLM 输入包 | android_world | 小 |
| 3 | LLM 引导探索模式（`--strategy llm`）：候选动作打分 + 动作后反思 | DroidRun 编排 + v3 prompt | 中 |
| 4 | 元素文档库 action_effect 蒸馏 → 生成 prompt 注入 | AppAgent 范式 | 中 |
| 5 | WinUI3 采集/验证器 | UFO2 UIA 模块 | 中 |
| 6 | 渲染 UI 语义走查验证器 | GUI-Critic-R1 prompt 改造 | 中 |
| 7 | 自进化轨迹生产（任务合成 → 执行 → 双 Critic → 数据集） | Mobile-Agent-v3 链路 + OS-Genesis | 大（战略级） |

---

## 四、结论

1. **流程共识**：感知(混合)→规划(分层)→决策(grounding 两步)→执行(原子动作)→反思(双级 Critic) 五段闭环 + 记忆回路，是 2025-2026 业界收敛形态；无争议。
2. **复用判断**：MIT/Apache 阵营（DroidRun、Mobile-Agent 家族、UFO2、AndroidWorld、uiautomator2、Fastbot）覆盖了本 fork 采集→生成→验证全链路所需的所有子系统，**无需自研任何 agent 框架本体**；自研工作只剩「把这些组件接到我们的 AdbBackend 与 6 栈管线上的胶水层」。
3. **许可证红线**：OmniParser V1/V2 检测权重 AGPL（用 V3 YOLOv9-E 或自训替代）、UIHash GPL-3.0（只借鉴）。
4. **战略机会**：Mobile-Agent-v3 的「自我进化轨迹生产」与本 fork 的 OS-Genesis 任务合成在思路上汇合于同一点——**把遍历数据升级为国产 GUI 模型训练数据工厂**，这是 fork 差异化定位的最大杠杆。
