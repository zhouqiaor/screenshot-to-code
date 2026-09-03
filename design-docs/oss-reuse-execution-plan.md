# 开源项目复用执行计划（采集 → 生成 → 验证 全链路）

> 日期：2026-09-02 · 汇总三份调研：`reuse-reference-report.md`（验证侧）、`adb-traversal-progress-and-reuse.md`（采集侧）、`gui-agent-pipeline-and-reuse-map.md`（全流程）
> 本文回答一个问题：**后续每一步开发，具体从哪个项目拿什么、怎么拿、何时拿。**

---

## 一、复用方式四级分类

| 级别 | 含义 | 例子 |
|---|---|---|
| L1 整包引入 | 直接装依赖/推 jar，走其协议 | uiautomator2 常驻服务、Compose Driver Gradle 插件 |
| L2 模块移植 | 拷贝其源码模块/文件，适配到本仓库 | android_world M3A 感知格式化、UFO2 UIA 检测 |
| L3 机制/Prompt 移植 | 不拿代码，拿设计（配置格式、prompt 结构、算法机制） | Fastbot hyper-event、Mobile-Agent-v3 多角色、GUI-Critic-R1 |
| L4 架构参考 | 只对照设计校准自己的实现 | DroidBot UTG 分层、FigmaToCode AltNode IR |

**判断规则**：能 L1 不 L2，能 L2 不 L3；L3/L4 必须落到本仓库的具体文件，否则不算复用。

---

## 二、按阶段映射（对齐路线图 A/B/C 段）

### A 段 · 采集（当前 Sprint）

| 项目 | 级别 | 具体拿什么 | 落到哪 | 许可 | 前置 |
|---|---|---|---|---|---|
| **uiautomator2** | L1 | atx-agent/u2.jar 推设备 + `adb forward` + JSONRPC `dumpWindowHierarchy`；保留原生 dump 为 fallback | `adb_traversal.py` 的 `UiBackend` 第二实现 | MIT | **先在 TEQU-S2C 实测 app_process 常驻可行性**（唯一硬风险） |
| **Fastbot** | L3 | ① hyper-event：同构等价控件（九宫格图标）合并超事件；② `max.xpath.actions` 手工引导配置格式；③ `max.widget.black` 控件黑名单 | `adb_traversal.py` 去重逻辑 + 新增 `guide.json` 配置文件 | MIT | 无 |
| **scrcpy (server)** | L1 | 视频流抽帧替代 4K screencap+pull（~1MB/次） | `AdbBackend.screenshot` 的第二通道 | Apache-2.0 | A 段后置，P2 |
| **DroidBot** | L4 | UTG/DeviceState/InputPolicy 分层对照校准；补 DFS/BFS 双策略 | 对照现有 `graph.json` schema | 需核实 | 无 |

**A 段验收**：步均 ≤12s；30-60min 全量遍历产出首个数据集（states + UTG + 截图对）。

### B 段 · LLM 引导探索 + 生成增强（依赖 A 段数据集）

| 项目 | 级别 | 具体拿什么 | 落到哪 | 许可 |
|---|---|---|---|---|
| **android_world** | L2 | M3A 感知格式化代码：元素表 JSON + 截图双输入包（混合感知标准写法） | 新模块 `backend/capture/llm_perception.py` | Apache-2.0 |
| **droidrun** | L2 | ManagerAgent/ExecutorAgent 编排 + 原子动作集 + LLM-agnostic 多后端；`UiBackend` 替换其 Portal 通道 | `--strategy llm` 模式的编排层 | MIT |
| **Mobile-Agent-v3** | L3 | ① 多角色 prompt（规划/执行/反思/Notetaker）；② Notetaker 跨 App 状态摘要 → global_graph 语义索引 | prompt 模板目录 | MIT |
| **AppAgent 范式** | L3 | 元素文档库：UTG 边 `<s,a,s'>` 蒸馏为 action_effect 文档，注入生成 prompt | `backend/prompts/` 注入点 + 蒸馏脚本 | 思路 |

**B 段顺序**：SoM 标注导出（自研半天）→ M3A 移植（小）→ `--strategy llm`（中）→ 元素文档库蒸馏（中，**采集↔生成的连接点**）。模型直连百炼 glm-5.2 / 火山 doubao-seed-2-1-turbo，已有 key，无需 GUI-Owl。

### C 段 · 验证（可与 B 并行，不阻塞）

| 项目 | 级别 | 具体拿什么 | 落到哪 | 许可 |
|---|---|---|---|---|
| **Compose Driver** | L1 | Gradle Settings Plugin + HTTP 端点（`/screenshot` `/printTree` `/click`），无设备 JVM 截图 | `e2e_demo/android_project/settings.gradle.kts` +3 行；`backend/e2e_compile_verify.py` +50 行 | Apache-2.0 |
| **ComposablePreviewScanner** | L1 | @Preview 自动扫描（含 Glance App Widget）→ 截图 | Compose 验证器流水线 | 见报告 |
| **Roborazzi** | L2 | Robolectric 截图 + AI 断言（接火山引擎做语义断言） | Compose 栈验证第二层 | Apache-2.0 |
| **Paparazzi** | L2 | JVM Layoutlib 像素回归基线 | 像素 diff 层 | Apache-2.0 |
| **GUI-Critic-R1** | L3 | 步级 Critic prompt 改造为「渲染前后语义比对」验证器 | 渲染 UI 走查验证器 | MIT |
| **UFO2** | L2 | UIA 控件检测 + 控制自动化模块（`ufo/` AgentOS 按需摘取） | **WinUI3 栈**采集 + 验证器，省掉自研 Windows UIA 管线 | MIT |

### 横切 · Token 与成本

| 项目 | 级别 | 拿什么 |
|---|---|---|
| **TRIM/Text-or-Pixels** | 已落地 | T1 压缩 + T4 截断 + T5 历史（已实现，无需动作） |
| **DroidRun 成本经验** | L4 | a11y 结构化输入比截图省 ~12× token（$0.075/任务）→ B 段感知默认走结构化优先 |

---

## 三、许可证红线（集成前必查）

| 项目 | 问题 | 处置 |
|---|---|---|
| OmniParser V1/V2 icon_detect 权重 | AGPL（YOLOv8 遗传），传染 | 只用 V3 YOLOv9-E（MIT 链）或自训；caption 模型无此问题 |
| UIHash | GPL-3.0 | 永不集成，仅借鉴思路 |
| DroidBot | 许可待核实 | 核实前只做 L4 架构参考，不拷代码 |
| OpenAI Operator / Claude Computer Use / AutoGLM | 闭源 | 只对照公开技术报告 |

---

## 四、执行节奏（与路线图对齐）

```
Step 0  提交现有代码 → PR + OCR          （无复用项）
A1      u2 可行性实测（L1）               ← 硬风险最先验证
A2      hyper-event + 引导配置（L3）      ← Fastbot 格式
A3      全量遍历跑数据集                  ← 依赖 A1/A2
B1      SoM 标注导出（自研）
B2      M3A 感知格式化移植（L2）          ← android_world
B3      --strategy llm（L2+L3）          ← droidrun + v3 prompt
B4      元素文档库蒸馏（L3）              ← AppAgent 范式，喂生成 prompt
C1      Compose Driver 接入（L1）         ← 验证段最先动
C2      Roborazzi AI 断言（L2）
C3      渲染语义走查（L3）                ← GUI-Critic-R1
C4      WinUI3 采集/验证（L2）            ← UFO2
```

每步独立可交付；B 依赖 A3 数据集；C1 随时可做（不依赖 A/B）。

---

## 五、复用检查清单（每项集成时过一遍）

1. 许可证是否允许本 fork 的集成方式（L1/L2 需逐文件核对 NOTICE）？
2. 是否保留了 upstream 的版权声明？
3. L2 模块移植是否在文件头标注来源仓库 + commit hash？
4. fallback 路径是否保留（如 u2 → 原生 dump）？
5. 引入依赖是否进入 `backend/pyproject.toml` / `frontend/package.json`（而非裸 pip/npm）？
