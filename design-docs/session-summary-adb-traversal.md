# ADB UI 遍历会话总结：需求 · 设计 · 计划

> 会话日期：2026-09-02 · 分支：`adb-ui-traversal`（worktree `C:/Code/screenshot-to-code-adb-traversal`）
> 目标设备：`200.47.94.166:5555`（TEQU-S2C 华为定制 TV ROM，3840×2160 @480dpi，D-Pad 导航）

---

## 一、需求（用户原始指令）

| 轮 | 指令 | 落点 |
|---|---|---|
| 1 | 拉取 worktree 规划方案、遍历截图和抓取 ADB 界面树、详细设计方案、按需调研业界方案 | worktree 搭建 + 遍历工具 + 设计文档 |
| 2-3 | 继续推进；总结进展、分析下一步优化、调研业界开源项目复用 | v2 优化轮（8 项修复）+ 复用报告 |
| 4 | 完整总结当前方案设计后优化 | 修复全部落地 + 回归验证 |
| 5 | 调研 GUI Agent 的感知与记忆方案 | 专项调研报告 |
| 6 | 调研 GUI Agent 整体流程 + 哪些开源项目可完全复用 | 全流程复用地图 |
| 7 | 分析下一步 | 路线图（Step 0 → A/B/C 三段） |
| 8 | 后续如何复用业界开源项目 | 复用执行计划（四级复用 × 三段映射） |

**需求本质**：为 screenshot-to-code fork 补上「真机 UI 采集」能力 —— 从 Android TV 设备自动遍历界面，产出 states + UTG + 截图对数据集，作为「截图→代码」生成与验证闭环的数据底座，并以 MIT/Apache 开源项目为组件来源，避免自研 agent 框架本体。

## 二、设计（核心决策）

### 2.1 架构分层

```
adb_traversal.py (~1093 行，单文件自包含)
├── AdbBackend      adb 连接 / dump / screencap / input（dpad+tap 双模）
├── UiBackend 抽象  dump 通道可替换（为 uiautomator2 常驻服务预留）
├── 结构签名        class|resource-id|归一化text|desc → 跨运行稳定去重
├── Traverser       DFS + BACK 回溯 + HOME 兜底 + 先查再按
├── extract_actions 动作抽取与去重（focusable 只出 dpad、容器紧包裹约束）
└── write_outputs   manifest / graph(UTG) / states/<idx>_<sig>/ 产物树
```

管线接入：`capture/pipeline.py` 注册 `adb_traversal`（key: `adb-traversal`）。

### 2.2 TV 双模导航（正确性核心）

- **nav_mode 自动判定**：TV 特征（无 touchscreen + dpad）→ `dpad` 模式
- **dpad 靶向**：焦点判定用**包含性判定**（焦点 bounds 落在目标内 ±8px 即命中）；巨大目标（>1/3 屏）仍要求精确匹配
- **共享祖先约束**：祖先仅当「紧包裹」（面积 ≤ 目标 2×）才可作 aim 点 —— 消除「九宫格 CENTER 永远激活同一项」
- **回溯三保险**：先 dump 确认当前态 → BACK 耗尽 → HOME 兜底 → --package 重启兜底

### 2.3 产物契约（数据集格式）

```
runs/adb_traversal/<device>_<ts>/
├── manifest.json   # 设备/配置/汇总/nav_mode
├── graph.json      # UTG：states(全量带 captured 标记) + edges(action 完整序列化 + effective 导航法)
└── states/<idx>_<sig>/
    ├── screenshot.png / screenshot_768.jpg  # 768px 压缩版供 LLM（token 治理规范）
    ├── ui_tree.xml / skeleton.json          # 原始树 + 组件树（喂 A2UI/LLM）
    └── meta.json                            # 包名/activity/签名/文本
```

### 2.4 修复过的 8 个缺陷（v2 轮）

dpad 靶向失效 / 共享祖先重定向 / 动作去重 / UTG 悬空边 / 边丢失导航法 / 回溯先查再按 / HOME 兜底 / 运行期关动画（结束恢复）。

## 三、验证结果

| 指标 | v1 基线 | v2 当前 |
|---|---|---|
| 步均耗时 | 73.3s | **20.7s（-72%）** |
| UTG 悬空边 | 1 | **0** |
| dpad 靶向 | 4 条边全误指同一状态 | 第1瓦片→云会议、第2瓦片→白板、退出→launcher（正确） |
| 跨运行签名稳定性 | — | 4 次运行同签名 |
| pytest / pyright | — | 27 passed / 0 errors（3 个 pyright 1.1.411 dataclass 怪癖告警，非代码问题） |

## 四、计划（路线图 + 复用执行）

### 4.1 路线图

```
Step 0  提交现有代码（当前全部未 commit）→ PR + OCR
A 采集段   A1 u2 常驻服务实测（唯一硬风险：TEQU-S2C 定制 ROM）
           A2 Fastbot hyper-event + 引导配置
           A3 30-60min 全量遍历 → 首个可用数据集
B 生成段   B1 SoM 标注 → B2 M3A 感知移植 → B3 --strategy llm → B4 元素文档库蒸馏喂生成 prompt
C 验证段   C1 Compose Driver → C2 Roborazzi AI 断言 → C3 GUI-Critic-R1 语义走查 → C4 UFO2 WinUI3
依赖：B 依赖 A3 数据集；C1 不依赖任何前置，可随时插入
```

### 4.2 复用四级分类（详见 oss-reuse-execution-plan.md）

| 段 | L1 整包 | L2 模块移植 | L3 机制/Prompt | L4 参考 |
|---|---|---|---|---|
| A 采集 | uiautomator2、scrcpy server | — | Fastbot hyper-event + max.xpath.actions | DroidBot UTG |
| B 生成 | — | android_world M3A、droidrun 编排 | Mobile-Agent-v3 多角色、AppAgent 元素文档库 | DroidRun 成本经验 |
| C 验证 | Compose Driver、PreviewScanner | Roborazzi、Paparazzi、UFO2 UIA | GUI-Critic-R1 | — |

**许可证红线**：OmniParser V1/V2 icon_detect 权重 AGPL（改用 V3 YOLOv9-E）；UIHash GPL-3.0 只借鉴；DroidBot 待核实只做 L4。

## 五、产出物清单

| 文件 | 内容 |
|---|---|
| `backend/scripts/adb_traversal.py` | 遍历器核心（未提交） |
| `backend/capture/pipeline.py` | 管线注册（未提交） |
| `design-docs/adb-ui-traversal-design.md` | 架构/算法/UTG schema/验收标准 |
| `design-docs/adb-traversal-progress-and-reuse.md` | 进展 + v2 优化轮记录 |
| `design-docs/gui-agent-perception-memory-survey.md` | 感知/记忆双线调研 |
| `design-docs/gui-agent-pipeline-and-reuse-map.md` | 整体流程 + 可完全复用项目清单 |
| `design-docs/oss-reuse-execution-plan.md` | 复用执行计划（四级 × 三段） |
| `runs/adb_traversal/` | 真机采集产物（不进版本库） |

## 六、风险与未决

1. **u2 常驻服务在 TEQU-S2C 的可行性未实测** —— A 段唯一硬风险，应最先验证；fallback（原生 dump）已保留
2. **当前工作全部未提交** —— Step 0 优先级最高（建议拆 feat + docs 两个 commit，`runs/` 进 .gitignore）
3. pyright 3 个怪癖告警 —— 升级 pyright 后自消，非阻塞
4. touch 模式路径未在触屏设备上采样验证（P2）
