# GUI Agent 感知与记忆方案调研

> 日期：2026-09-02 · 调研人：WorkBuddy
> 范围：GUI Agent（桌面/Web/移动/TV）的 **感知（Perception）** 与 **记忆（Memory）** 两大模块的业界方案、代表工作、开源可复用项，以及对本项目（screenshot-to-code / ADB UI 遍历管线）的落地映射。

---

## 0. 结论速览（TL;DR）

| 维度 | 业界共识 | 对本项目的映射 |
|---|---|---|
| 感知输入 | 结构树（AXTree/XML/DOM）与截图双通道**混合**是工程最优；纯视觉是模型前沿路线 | ✅ 已是双通道（ui_tree.xml + screenshot），架构判断正确 |
| 感知瓶颈 | **GUI grounding**（语言→屏幕坐标）是第一瓶颈；icon 识别（ScreenSpot-Pro 上仅 ~4%）是未解难题 | 我们的场景不依赖坐标 grounding（有 bounds），但 icon 语义标注可借 UI 检测模型补 |
| 状态识别 | 结构签名 vs 感知哈希 vs 树编辑距离之争；**没有单一算法能抓住所有功能近重复**（ICSE'20 十算法对比结论） | ✅ 结构签名已实测跨运行稳定；建议**加 pHash 作第二通道**兜底（布局同、内容异） |
| 短期记忆 | 5 种实现模式，从「无记忆」演进到「专职 Memory Agent 滚动摘要」 | 遍历器不需要 LLM 决策即无 STM 问题；接入 LLM 引导探索时用 Action-Thought 模式起步 |
| 长期记忆 | 两大范式：**AppAgent 式逐元素文档库**（探索产物→RAG 检索）与 **Mobile-Agent-E 式 Tips+Shortcuts**（经验反思→复用） | UTG + state 数据集天然可**自动蒸馏成元素文档库**（OS-Genesis 反向任务合成思路），这是最值得做的一步 |
| 自进化 | Mobile-Agent-E +Evo 提升 6.5%，Shortcuts 把每操作延迟 43.5s→27.4s | 对应 Fastbot `max.xpath.actions` 手工引导配置；我们在 P2 引入 |

---

## 一、感知（Perception）方案

### 1.1 三条技术路线

| 路线 | 输入 | 代表 | 优势 | 劣势 |
|---|---|---|---|---|
| **文本结构** | AXTree / XML / DOM / HTML | AutoDroid（UI→HTML 化）、WebArena（DOM）、SeeAct | 精确 bounds、无视觉误差、便宜 | 冗余/噪声大；部分平台拿不到完整树；**丢像素级信息**（图标图片、Canvas） |
| **纯视觉** | 截图 | CogAgent（双分辨率 1120×1120）、UI-TARS、Aria-UI、SeeClick | 平台无关、泛化强（端到端训练） | grounding 精度是瓶颈；小 icon 定位差；4K 屏 token 开销大 |
| **混合 / 工具增强** | 截图 + 树 + OCR + 检测 | AppAgent（XML 过滤 clickable + 截图数值标注）、M3A（screenshot+AXTree）、OmniParser（YOLO 检测+BLIP 描述+OCR+SoM） | 工程上当前最优；各取所长 | 管线复杂；工具链误差累积 |

**关键判断依据**（来自 2504.13865 综述 + liqing.io CUA 调研）：
- 纯文本路线三大痛点：**冗余、噪声、可得性**（很多平台 XML 不完整——我们 TEQU-S2C 的 uiautomator dump 就是完整可用的好情况）。
- 纯视觉路线的 grounding 精度与下游任务成功率**强正相关**（SeeClick 结论）；但 ScreenSpot-Pro 揭示专业软件 icon 识别准确率仅 ~4%。
- **数据质量 > 数据规模**：GroundCUA 用 700K 高质量样本打败 9M 自动采集；TongUI 143K 轨迹数据集被认为「可能比模型更有价值」。

### 1.2 代表模型/工具速查

| 名称 | 机构/时间 | 规模 | 核心机制 | 许可 |
|---|---|---|---|---|
| CogAgent | 清华/智谱 2023.12 | 18B | 双分辨率 cross-attention（224+1120） | Apache-2.0（CogAgent-18B 开源） |
| SeeClick | 南大 2024.01 | 9B | 首个把 grounding 定为核心瓶颈的持续预训练 + ScreenSpot 基准 | 开源 |
| OS-Atlas | 上海AI Lab 2024.10 | 4B/7B | 最大开源 grounding 语料（13.58M 元素 / 2.24M 截图），7B zero-shot 超 GPT-4o | 开源 |
| ShowUI | NUS/MS 2024.11 | 2B | UI-guided token selection，减 33% token，256K 数据达 75.1% | 开源 |
| Aria-UI | HKU/Rhymes 2024.12 | 3.9B | 纯视觉 + **文本/图文交错动作历史**（上下文感知 grounding） | 开源 |
| UI-TARS | 字节 2025.01 | 2B/7B/72B | System-2 reasoning + 反思微调 + 在线自举 | UI-TARS-1.5 开源 |
| OmniParser | 微软 2024.08 | 工具 | YOLO 检测 + BLIP icon 描述 + OCR + **Set-of-Mark**，即插即用增强任意 VLM | MIT |
| Ferret-UI 2 | Apple 2024.10 | — | 多平台高分辨率编码，referring/grounding | 部分开源 |

### 1.3 状态识别与去重（感知的「记忆入口」）

ICSE'20（Yandrapally 等）对比 10 种近重复检测算法的结论：**没有一种跨域算法能准确抓住所有功能近重复**：

| 算法族 | 输入 | 特点 |
|---|---|---|
| simhash / TLSH | DOM 内容 | 64/256 位指纹，快 |
| RTED（树编辑距离） | DOM 树 | 结构感知强，慢 |
| pHash / block-mean | 截图 | 抗轻微视觉差异 |
| SSIM / 直方图 / PDiff | 截图 | 结构性/颜色相似度 |
| **Tree Kernel**（arXiv 2108.13322） | DOM 树 | 把 clone/near-dup/distinct 建成分类问题，优于上述启发式 |
| **UIHash**（USENIX Sec'24，GPL-3.0） | XML+截图 | 网格化视觉外观表示 + CNN 视图重识别，专攻 Android UI 相似性 |
| Google Similarity Transformer（CHI'22） | 截图 | Faster-RCNN 元素检测 + transformer 联合编码，学屏幕关系 |

**对本项目的启示**：我们的结构签名（class|resource-id|归一化 text|desc）≈ simhash 思想，实测跨运行稳定。已知盲区是「结构同、内容异」（如同一列表页不同数据页），pHash 第二通道可兜底；更激进的 Tree Kernel / UIHash 留作 P2。

---

## 二、记忆（Memory）方案

### 2.1 分类学（LLM-Brained GUI Agents 综述，2411.18279）

| 记忆元素 | 类型 | 内容 | 存储介质 |
|---|---|---|---|
| Action / Plan / 执行结果 / 环境状态 | 短期 | 任务内轨迹 | 上下文窗口（受长度限制，需摘要/裁剪） |
| Self-experience | 长期 | 历史任务完成轨迹 | 数据库/磁盘 |
| Self-guidance | 长期 | 从轨迹蒸馏的规则/指引 | 数据库/磁盘 |
| External Knowledge | 长期 | API 文档、搜索等外部知识 | 外部知识库 |
| Task Success Metrics | 长期 | 跨会话成败率指标 | 数据库/磁盘 |

### 2.2 短期记忆的 5 种实现模式（MemGUI-Bench 对 11 个系统的实证归纳）

| 模式 | 代表系统 | 机制 | 评注 |
|---|---|---|---|
| ① 无历史 | CogAgent | 只看当前帧+指令 | 基线；长程任务必败 |
| ② 规则拼接 | SeeAct、AutoDroid | 每步「选元素+动作」字符串拼接 | 刚性、不可扩展 |
| ③ Action-Thought | AppAgent、UI-Venus、GUI-Owl、UI-TARS | 每步输出动作+思考，结构化历史 | 性价比最高，工程首选 |
| ④ 多轮上下文 | UI-TARS | 把历史当多轮对话滚动 | 受上下文长度限制（实测仅条件于最近 N≈5 帧） |
| ⑤ 专职 Memory Agent | T3A、M3A、Agent-S2、Mobile-Agent-V2/E | **主决策 Agent + 副记忆 Agent 持续滚动摘要** | 最强也最贵（多一次 LLM 调用/步） |

### 2.3 长期记忆的两大范式

**范式 A：AppAgent 探索式知识库（探索→文档→RAG 检索）**

- 生命周期两阶段：**Exploration**（自主试错 or 人类演示）→ **Deployment**（带知识库执行）。
- 元素文档 schema：`element_id`（数值标注）/ `element_type`（XML class）/ `visual_description`（VLM 语义摘要）/ `action_effect`（触发后发生什么，如 "Opens the settings menu"）。
- **信息合并（Consolidation）**：同一元素被多次操作时，让 LLM 把过去 N 次观察合成一条综合描述——防止知识库退化成噪声日志，变成高保真「应用说明书」。
- 感知侧配套：XML 过滤 clickable 节点 → 截图中心点渲染**半透明数值标签** → LLM 动作空间离散化为 `click(5)`、`long_press(12)`——把连续空间推理变成离散符号选择，消除「空间漂移」这一最常见失败模式。
- 探索策略：目标导向（LLM 判断当前页与任务无关则 BACK），优于盲 DFS/BFS；自主探索成功率 73.3%。
- 开源：`TencentQQGYLab/AppAgent`（MIT 旧版 / 新版 License 需确认）。

**范式 B：Mobile-Agent-E 自进化记忆（Tips + Shortcuts）**

- 五角色分层：Manager（规划）/ Perceptor（OCR+grounding）/ Operator（执行）/ Action Reflector（前后截图比对验证，失败→Error Escalation 上报 Manager 重规划）/ Notetaker（聚合任务事实，如价格）。
- 两个 Experience Reflector 在**任务完成后**更新长期记忆：
  - **Tips**（情景记忆式教训）：自然语言通用指导，如「页面完全加载后再搜索」。
  - **Shortcuts**（程序性知识）：JSON 格式可复用原子操作序列 + 前置条件，如「点击输入并搜索」= tap→type→enter 三步合一。
- 实证：Mobile-Eval-E 上 Satisfaction Score 75.1%→**86.9%（+Evo）**；Shortcuts 把每操作延迟 **43.5s→27.4s**；终止错误率 52%→12%。
- ⚠️ 争议（pith.science 质证）：自进化收益是在 Experience Reflector 能看到同场景未来任务 query 的前提下测的，对完全未见任务的泛化收益可能缩水——复用该设计时要按「未见任务」评估。

**其他值得记的**：
- **Agent S / S2**：narrative + episodic memory，经验蒸馏成 actionable tips；Mixture of Grounding（视觉/文本/结构化三专家）。
- **UI-TARS**：把经验隐式编码进模型参数（迭代微调交互轨迹）——数据飞轮路线（UI-TARS-2 已闭环）。
- **OS-Genesis（ACL 2025）**：**反向任务合成**——先自由探索记录 ⟨s_pre, action, s_post⟩ 三元组 → GPT-4o 生成低阶指令 → 合成高阶任务 → 轨迹奖励模型（TRM，评 completion+coherence）过滤 → 训练数据。AndroidWorld 成功率近任务驱动方法 2 倍。**这条对我们价值极大：遍历数据集天然就是 ⟨s,a,s'⟩ 三元组库。**
- **MemGUI-Bench**（2602.06075）：首个专门测「记忆」的基准——动态环境（内容随时间变化）下的记忆型任务，暴露 11 个主流系统的记忆短板；设计记忆评估时可参考其任务套件思路。

---

## 三、开源可复用清单（按优先级）

| 优先级 | 项目 | 许可 | 与本项目的关系 |
|---|---|---|---|
| P0 | **AppAgent 元素文档 schema + Consolidation** | MIT（旧版） | UTG 边的 `action_effect` 可从 `to-state` 摘要自动生成 → 元素文档库 → 反哺 LLM 生成 prompt |
| P0 | **Set-of-Mark 数值标注**（AppAgent/OmniParser 实践） | — | 截图 + bounds 渲染数值标签，导出给 LLM（生成/校验两用），把 grounding 变成选择题 |
| P1 | **OS-Genesis 反向任务合成** | 开源 | 遍历 ⟨s,a,s'⟩ → 低阶/高阶指令数据 → 训练/评估国产 GUI 模型的数据源（匹配 fork 的国产模型定位） |
| P1 | **OmniParser** | MIT | icon 语义描述（截图里没有 text/desc 的图标），补 ui_tree 盲区 |
| P2 | **UIHash** | GPL-3.0 | 第二代状态去重（结构+视觉联合），license 需注意只可借鉴思路或独立实现 |
| P2 | **Mobile-Agent-E Tips/Shortcuts** | 论文（代码部分开源） | 跨运行经验复用：对应 Fastbot `max.xpath.actions` 手工引导；遍历器可先落「Shortcuts = UTG 中的高频边序列」 |
| P2 | **pHash（imagehash 库）** | MIT | 立刻可加的第二签名通道，一天工作量 |

---

## 四、对本项目 ADB 遍历管线的落地映射

### 4.1 感知侧

现状对照业界：我们已经是「混合路线」（ui_tree.xml 结构通道 + 4K/768px 截图视觉通道 + skeleton 抽象层），架构无需推翻。增量建议：

1. **SoM 标注导出（P0，~半天）**：`adb_traversal.py` 已有每个 state 的 actions + bounds，写一个小工具把数值标签渲染到 768px JPEG 上（Pillow 画框+编号），产出 `screenshot_som.jpg`。该产物：
   - 给下游 LLM 代码生成用（模型指认「组件 3 是 Grid」比给坐标可靠）；
   - 给 OCR/检测通道做对齐基准。
2. **pHash 第二签名通道（P1，~1 天）**：`meta.json` 增加 `phash` 字段（imagehash，768px JPEG 上算）。去重规则升级为：结构签名相同 **且** pHash 汉明距离 ≤ 8 → 同状态；结构签名不同但 pHash 相同 → 标记「布局同内容异」的疑似近重复（当前盲区）。
3. **icon 语义标注（P2）**：TV launcher 大量无 text/desc 的 ImageView，ui_tree 无语义。可用 OmniParser 思路（检测+VLM 描述）或直接用 doubao vision（已开通）批量打标，写回 skeleton。

### 4.2 记忆侧

我们的遍历器是**确定性算法**（无 LLM 决策循环），所以 STM 模式暂不适用；记忆的价值在**跨运行（LTM）**：

1. **元素文档库（P0，最值得做）**：每个 run 结束后，把 UTG 边蒸馏成 AppAgent 式元素文档——
   - `element_id` ← action 的 bounds+class；
   - `action_effect` ← to-state 的 texts/skeleton 摘要（无需 LLM 也能生成初版；接 doubao vision 可生成视觉描述版）；
   - 同一元素跨 run 出现 → 走 Consolidation 合并。
   - 用途：a) 生成 prompt 的上下文注入（「点击此按钮会进入 XX 页」）；b) 下次遍历的启发式（已知的死路/危险按钮直接跳过——比 _RISKY_TEXT 黑名单精确得多）。
2. **UTG 即跨 run 记忆（P0）**：把多次 run 的 graph.json 合并成全局 UTG 存 `runs/adb_traversal/global_graph.json`，遍历启动时加载——已探过的边直接复用签名，不重复探索。这是最便宜的「记忆」，纯工程。
3. **Shortcuts（P1）**：全局 UTG 中高频出现的边序列（如 launcher→白板→退出）固化为 shortcut，Fastbot 的 `max.xpath.actions` 就是这个思想的手工版；遍历器可以用它做「快速回位」。
4. **指令合成（P1，OS-Genesis 路线）**：⟨s,a,s'⟩ 三元组 → 低阶指令（「点击白板图标」）→ 高阶任务（「新建一个白板并退出」）。这给 fork 的国产模型生态提供了训练/评测数据出口，把采集管线升级成数据工厂。

### 4.3 风险与注意

- AppAgent 自主探索的成功率建立在 GPT-4V 级 VLM 上；我们若用 doubao-seed-2-1-turbo（已验证可用）做反思/描述，质量需抽查（建议每 run 人工看 3-5 条元素文档）。
- Mobile-Agent-E 的自进化收益存在「预知未来任务」争议，我们落地时按保守预期（Tips 收益 > Shortcuts 收益）。
- UIHash 是 GPL-3.0，只能借鉴思路，不可直接复制代码进本项目（本项目 MIT 系）。

---

## 五、参考

- A Survey on (M)LLM-Based GUI Agents — arXiv 2504.13865
- LLM-Brained GUI Agents: A Survey — arXiv 2411.18279（§5.6 Memory 分类学）
- LLM-Powered GUI Agents in Phone Automation — arXiv 2504.19838
- MemGUI-Bench — arXiv 2602.06075（记忆基准 + 11 系统记忆实现实证）
- AppAgent — arXiv 2312.13771 / github.com/TencentQQGYLab/AppAgent
- Mobile-Agent-E — arXiv 2501.11733（Tips+Shortcuts 自进化）
- OS-Genesis — arXiv 2412.19723 / ACL 2025（反向任务合成）
- Near-Duplicate Detection in Web App Model Inference — ICSE'20（十算法对比）
- Tree Kernels for Near-duplicate States — arXiv 2108.13322
- UIHash — USENIX Security'24
- CUA 领域调研笔记 — liqing.io/mindflow/Topics/ComputerUseAgents-Survey（含 UI-TARS-2 / Agent S3 / ComputerRL / DART-GUI 前沿）
