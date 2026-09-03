# 截图转 Ark-UI 开源项目复用调研报告

> 调研日期：2026-09-02
> 目标：补充 `reuse-reference-report.md` 缺失的 **Ark-UI（HarmonyOS 方舟框架）** 栈。从"截图/设计稿/源码 → ArkUI/ArkTS 代码"的视角，筛出可直接复用 / 适配 / 架构参考 / 竞品参考的方案，并给出对本 Fork 的集成点。
> 重要区分：**ArkUI（鸿蒙方舟）≠ A2UI（本 Fork 已有的 Android Agent-to-UI 栈）**，两者是完全不同的目标框架，不要混淆。

---

## 0. 一句话结论

本 Fork 的基座 `abi/screenshot-to-code` **上游不支持 ArkUI/HarmonyOS**（仅 HTML/Tailwind/React/Vue/Bootstrap/Ionic/SVG 六栈）。把 ArkUI 作为第 7 个目标栈接入，是差异化价值点。可复用的开源资产分两类：

1. **渲染验证后端** —— `ArkUI-X`（OpenHarmony 官方跨平台框架，Apache 2.0，开源），相当于 Compose 栈的 Compose Driver，用来把生成的 ArkUI 代码真正渲染出来截图验证。
2. **生成方法论** —— 两篇 2025–2026 学术论文 `ArkTrans` / `DeclarUI`，提出"骨架提取 + LLM 生成 + 规则后修复 + 编译器驱动迭代"的管线，可直接映射为本 Fork 的 `get_system_prompt("arkui")` + `validate_code.py` 的 ArkUI 分支。

闭源的华为 CodeGenie / DevUI Generator、墨刀 D2C 仅作竞品参考，**不可直接复用代码**。

---

## 1. 项目总览

| # | 项目 | 类型 | 开源？ | 与本 Fork 的关系 | 复用等级 |
|---|---|---|---|---|---|
| 1 | **ArkUI-X** | ArkUI 跨平台渲染框架 | ✅ Apache 2.0 (Gitee) | 直接复用：生成代码后的渲染/截图验证后端 | ⭐⭐⭐ 立即 |
| 2 | **ArkTrans** (arXiv 2606.07085) | 源码→ArkUI 翻译方法 | ⚠️ 论文+arXiv 源码 | 方法论参考：骨架引导 + 规则后修复 | ⭐⭐ 架构 |
| 3 | **DeclarUI** (ACM 2025) | 设计稿→声明式 UI（含 ArkUI） | ⚠️ 论文 | 方法论参考：CV+MLLM+编译驱动迭代 | ⭐⭐ 架构 |
| 4 | **abi/screenshot-to-code 上游** | 截图→多栈代码基座 | ✅ MIT (GitHub) | 基座：本 Fork 即其 fork，加 ArkUI 栈 | ⭐⭐⭐ 基座 |
| 5 | **DevEco CodeGenie** | 华为官方 AI 编程（图生 ArkTS） | ❌ 闭源 IDE 插件 | 竞品参考 | ⭐ 竞品 |
| 6 | **DevUI Code Generator** | 设计稿(Sketch/Figma)→ArkUI | ❌ 闭源（DevEco 内置） | 竞品参考 | ⭐ 竞品 |
| 7 | **墨刀 D2C** | 设计稿→ArkUI 工程（SaaS） | ❌ 商业闭源 | 竞品参考 | ⭐ 竞品 |
| 8 | **img2cook / pix2code** | 早期设计稿→代码研究 | ⚠️ 偏 React/Rax | 历史参考（非 ArkUI） | ⭐ 参考 |

---

## 2. 直接复用项目（⭐⭐⭐）

### 2.1 ArkUI-X — 生成代码的"眼睛和手"

**仓库**：https://gitee.com/arkui-x （OpenHarmony TSC 跨平台应用开发框架 TSG 孵化，华为/阿里/美的共建）
**协议**：Apache License 2.0 | **版本**：6.0.0 Release（配套 OpenHarmony 6.0.0 API 20，2025-12-31 发布）
**Stars**：1.4K+（2024 年数据）

**核心机制**：
- 基于 OpenHarmony 原生 ArkUI 框架扩展，让**一套 ArkTS 主代码**运行在 OpenHarmony / HarmonyOS / **Android** / **iOS** 多端。
- 非 WebView 渲染，各平台**原生渲染引擎**，性能接近原生。
- 完整支持 Stage 开发模型、UI 基础组件跨平台、状态管理。
- 配套 `ACE Tools` 命令行（Windows / Ubuntu / macOS 可跑），用于构建与运行。

**为什么是 ArkUI 栈的"Compose Driver 等价物"**：

| 维度 | Compose 栈（已有） | ArkUI 栈（新增） |
|---|---|---|
| 渲染后端 | Compose Driver（JVM Robolectric，无需设备） | ArkUI-X（需构建到 Android/iOS/OH 后运行） |
| 是否需要设备/模拟器 | ❌ | ✅（OpenHarmony 模拟器 或 Android 设备/模拟器跑 ArkUI-X APK） |
| 截图方式 | HTTP `/screenshot` | 渲染后 `componentSnapshot` / 系统截图 |
| CI 友好度 | ⭐⭐⭐ | ⭐⭐（需构建环境，较重） |

**本 Fork 集成点**：

| 集成位置 | 用途 | 改动量 |
|---|---|---|
| `backend/validate_code.py` | 新增 `arkui` 分支：ArkTS 语法/结构静态校验（不依赖渲染，立即可用） | +60 行 |
| `backend/e2e_compile_verify.py` | 生成 ArkUI 代码后，经 ArkUI-X 构建 Android APK → 模拟器截图（中期） | +120 行 |
| `backend/agent/state.py` | 多文件 AgentFileState 增加 ArkUI 入口页（`Index.ets` + 组件） | +20 行 |
| `frontend` 栈下拉 | 增加 "ArkUI" 目标栈选项 | +10 行 |

**立即可落的轻量路径（无需 ArkUI-X 构建环境）**：

先在 `validate_code.py` 里做**结构化校验**（参考 ArkTrans 的 ArkUI 约束清单），不等渲染：
- 仅允许 `Stack/Column/Row/Grid/List/Text/Button/Image/Progress/Slider/Blank/Divider/TextInput`；
- `List` 子项必须 `ListItem` 包裹，`Grid` 子项必须 `GridItem` 包裹；
- `Column`/`Row` 构造函数用 `{ space: N }` 传间距，修饰符链式调用；
- 状态变量用 `this.` 前缀引用；
- `@Entry @Component struct` 骨架完整。

### 2.2 abi/screenshot-to-code 上游（本 Fork 基座）

**仓库**：https://github.com/abi/screenshot-to-code （MIT，72k+ stars）

**关键事实**：上游支持的 6 个输出栈为 `HTML+Tailwind / HTML+CSS / React+Tailwind / Vue+Tailwind / Bootstrap / Ionic+Tailwind / SVG`，**不包含 ArkUI**。本 Fork 已自行扩展出 Android XML / Compose / Qt QML / WPF / A2UI 等栈（见 `validate_code.py`），**ArkUI 是第 7 个待补栈**。

**集成方式**：沿用现有 `get_system_prompt(stack)` 路由模式，新增 `arkui` prompt，不改动既有栈。

---

## 3. 方法论参考项目（⭐⭐ 架构级）

### 3.1 ArkTrans — 启发式引导 LLM 的声明式 UI 移植

**来源**：arXiv 2606.07085（2026-06-05，cs.SE），作者 Zheng 等。**源码随 arXiv 提供**（"Source files are served from arXiv.org"），但属研究级代码，非生产可用。
**输入/输出**：Kotlin Jetpack Compose / SwiftUI → **ArkUI**（文件级翻译，100 条并行基准）。
**核心指标**：直接 one-shot prompt 编译成功率 **0%**；ArkTrans 达 **90.67%** 可编译 + 高视觉保真。

**三步管线（对本 Fork 直接可借鉴）**：
```
1. UI Tree 构建：从源码抽取 UI 树 {comp, props, mod, children}，定位 EntryPoint，收集自定义组件定义
2. 骨架引导：用源码元数据生成 ArkUI skeleton（含 unmapped 元素注释），约束 LLM 初翻
3. 规则后修复：pattern-matching 应用经验规则修语法错误（常量内联、布局属性校正、结构完整性校验）
```

**对 ArkUI 生成的 Prompt 设计启示**（论文给出的结构化 prompt 模板，可直接转成本 Fork 的 arkui system prompt）：
```
System Role: 作为 ArkUI 代码生成专家，把 UI 骨架翻译为可执行 ArkTS，
             严格遵循 ArkUI 语法，保持源 UI 的布局与交互语义。
Context:     (a) ArkUI skeleton（带注释）(b) design tokens（#FF0000 / 16vp 等）
Explicit:    仅用指定组件集；{ space:N } 传间距；链式修饰符；
             List→ListItem / Grid→GridItem；状态变量 this. 前缀；
             只输出可编译 ArkTS，无解释文字。
One-shot:    提供 skeleton→correct code 单样本示例，覆盖常见语法错误类型。
```

**复用注意（评审已指出）**：论文的"经验规则"疑似从评测集内归纳，泛化性待验证；直接抄规则集有 in-sample 风险。建议只借鉴**骨架引导 + 单样本学习**的结构，规则集由本 Fork 在自己的 ArkUI 基准上重新归纳。

### 3.2 DeclarUI — CV + MLLM + 编译驱动迭代

**来源**：ACM PACMSE Vol.2 (2025)，"DeclarUI: Bridging Design and Development with Automated Declarative UI Code Generation"。
**输入/输出**：UI 设计稿 → 声明式 UI 代码；论文明确验证 **React Native / Flutter / ArkUI** 三框架泛化。
**核心机制**：
```
精确组件分割(CV) → Page Transition Graph(PTG) 建模跨页关系
  → MLLM 生成代码 → 迭代编译器驱动优化（编译报错回灌重生成）
```
**指标**：React Native 上 PTG 覆盖 96.8%、编译成功 98%，视觉相似度较 SOTA MLLM 提升最高 55%。

**对本 Fork 的架构价值**：
- 验证"截图→代码"走 **MLLM + 编译反馈闭环** 路线在 ArkUI 上可行（论文已泛化验证）。
- `Page Transition Graph` 概念可补本 Fork 当前缺失的**多页/多屏**生成能力（当前 fork 单页为主）。
- 与 `reuse-reference-report.md` 的 micro-agent 视觉匹配循环是同一思想，可统一为 `backend/agent/tools/visual_match.py`。

---

## 4. 闭源竞品 / 参考（⭐，不可复用代码）

### 4.1 DevEco CodeGenie（华为官方）
- 入口：DevEco Studio 右侧 CodeGenie 面板（IDE 内置，Alt/Option+U）。
- 能力：**图片输入 → ArkTS 页面代码**（"图生页面代码"），支持自然语言 + 图片双模态；5 大垂域（美食/旅游/购物/新闻/教育），基于 12 万+ 开源鸿蒙代码训练，生成页 100% 可预览运行。
- 闭源 IDE 插件，无法作为本 Fork 的依赖；但其"组件识别阈值 / 布局模式(线性·弹性) / 代码策略(完整·精简)"三参数设计，值得在本 Fork 的 ArkUI 生成 UI 上复刻。

### 4.2 DevUI Code Generator（DevEco Studio API 26 内置）
- 输入：设计稿（Sketch / Figma 导出的 JSON/XML）→ ArkUI 组件代码。
- 适合"设计稿规范"场景，批量生成高频组件（TopicCard / CheckInDialog / EmptyState），提效约 40%。
- 闭源；其"设计 token 抽取 → 组件自动抽取为可复用组件"思路可借鉴。

### 4.3 墨刀 D2C（商业 SaaS）
- 设计稿（Figma/Sketch/Adobe XD）→ 完整可编译 ArkUI 工程 ZIP，px 自动转 vp，自动抽取可复用组件，弹性布局优先。
- 闭源商业；参考价值在于"工程级代码包（非单页片段）"的交付形态 —— 本 Fork 生成 ArkUI 时也应输出**完整可运行工程**而非单文件片段。

---

## 5. 复用集成优先级矩阵

| 优先级 | 项目 | 本 Fork 集成点 | 预期收益 | 工作量 |
|---|---|---|---|---|
| P0 | **ArkUI-X** | `validate_code.py` 加 arkui 静态校验 + `e2e_compile_verify.py` 中期接 ArkUI-X 构建 | 生成代码可被渲染/截图验证（ArkUI 栈闭环） | 校验 4h / 渲染 2d |
| P0 | **上游加 ArkUI 栈** | `get_system_prompt("arkui")` + frontend 栈选项 | 第 7 个目标栈，差异化价值 | 1d |
| P1 | **ArkTrans prompt 模板** | arkui system prompt（骨架引导 + 单样本 + 组件白名单） | 一次生成可编译率显著提升 | 4h |
| P2 | **DeclarUI 编译闭环** | `visual_match.py` 接 ArkUI 编译反馈 | 多轮自修复、视觉保真 | 2d |
| P3 | **PTG 多页生成** | 长期架构（多屏/路由） | 超越单页生成 | 1w+ |

---

## 6. 推荐实施路径（落到本 Fork）

### Sprint 1（立即，纯代码不依赖鸿蒙环境）
1. **加 ArkUI 栈**：`backend/prompts/` 新增 arkui system prompt（组件白名单 + `this.` 状态 + ListItem/GridItem 约束 + 链式修饰符），frontend 栈下拉加 "ArkUI"。
2. **`validate_code.py` 加 arkui 分支**：结构化静态校验（无需渲染即可拦截 ~90% 语法错误，呼应 ArkTrans"直接 prompt 0% 可编译"的痛点）。

### Sprint 2（短期，接验证后端）
3. **ArkUI-X 渲染验证**：在 Windows 上装 ArkUI-X + ACE Tools，生成 ArkUI → 构建 Android APK → 模拟器截图，闭环补入 `e2e_compile_verify.py`（复用现有 Android 基础设施）。
4. **单样本 few-shot**：用 ArkTrans 的 skeleton→code 单样本模板，给 ArkUI 生成器喂 3–5 个高质量范例，提升首轮可编译率。

### Sprint 3+（中期）
5. **编译驱动迭代闭环**：DeclarUI 思想 + micro-agent 视觉匹配，生成 → ArkUI-X 编译报错回灌 → 重生成。
6. **PTG 多页**：从单页走向多屏/路由生成。

---

## 7. 风险与缺口

- **端到端开源"截图→ArkUI"尚无人做透**：上游不支持 ArkUI，ArkTrans 是"源码→ArkUI"非"截图→ArkUI"，DeclarUI 是学术代码。本 Fork 若补齐，即占据该空白。
- **ArkUI 渲染验证重**：不同于 Compose Driver 的 JVM 无设备方案，ArkUI-X 需要构建环境 + 模拟器/设备，CI 成本高；先用 `validate_code.py` 静态校验兜底。
- **鸿蒙 SDK / ArkUI-X 工具链在受限 Windows（8GB 内存 + 双杀软）下构建可能慢**，需评估是否用 Linux 子系统或云端构建。
- **闭源竞品强**（CodeGenie 已 100% 可运行生成），本 Fork 的差异化应放在"自托管 + 国产模型 + 多栈统一 + 可审计验证"而非单纯质量对标。
- **法律边界**：鸿蒙相关代码生成需遵守 OpenHarmony 开源协议（Apache 2.0）与华为开发者协议，生成的 ArkUI 工程如基于 ArkUI-X 须保留对应 LICENSE 声明。

---

## 8. 与 `reuse-reference-report.md` 的关系

| 报告 | 覆盖栈 | 定位 |
|---|---|---|
| `reuse-reference-report.md` | Compose / 截图测试(Paparazzi/Roborazzi) / FigmaToCode / A2UI 等 | 已有栈复用 |
| 本报告 `screenshot-to-arkui-reuse-report.md` | **ArkUI / ArkTS（HarmonyOS）** | 新增栈补篇 |

两报告共用同一集成骨架：`get_system_prompt(stack)` 路由 + `validate_code.py` 校验 + `e2e_compile_verify.py` 渲染验证。ArkUI 栈的验证后端用 **ArkUI-X**，等价于 Compose 栈用 **Compose Driver**。
