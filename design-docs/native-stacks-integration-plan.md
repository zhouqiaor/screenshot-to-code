# 原生栈统一接入规划：Android Compose 主线 + 其余 4 栈 + WinUI 3

> 本文档整合了 Phase 1（Android Compose 主线）、Phase 2（其余 4 栈）、WinUI 3 支持，
> 以及配套的 Token 优化策略，形成一份完整的原生栈接入路线图。

## 1. 现状总览

### 1.1 11+1 栈矩阵

| 栈 | 验证器 | System Prompt | 前端可选 | Agent Engine | Capture Pipeline |
|---|---|---|---|---|---|
| html_tailwind | — (web) | SYSTEM_PROMPT | Yes | Yes (index.html) | None |
| html_css | — | SYSTEM_PROMPT | Yes | Yes | None |
| react_tailwind | — | SYSTEM_PROMPT | Yes | Yes | None |
| bootstrap | — | SYSTEM_PROMPT | Yes | Yes | None |
| vue_tailwind | — | SYSTEM_PROMPT | Yes (Beta) | Yes | None |
| ionic_tailwind | — | SYSTEM_PROMPT | Yes (Beta) | Yes | None |
| **android_compose** | validate_code | **缺失** | **No** | Yes (多文件) | AdbCapture |
| **android_xml** | validate_code | android_xml_system.py (已写) | **No** | **No** | AdbCapture |
| **qt_qml** | validate_code | **缺失** | **No** | **No** | None |
| **windows_wpf** | validate_code | **缺失** | **No** | **No** | WinUiaCapture |
| **a2ui** | validate_code | a2ui_system.py (已写) | **No** | **No** | None |
| **winui3** (新) | **需新建** | **需新建** | **No** | **No** | WinUiaCapture |

### 1.2 三条断点（当前阻止原生栈走主管线）

| 断点 | 位置 | 现状 | 影响 |
|---|---|---|---|
| **B1: System Prompt 硬编码** | `create/image.py` L67, `create/text.py` L34, `update/from_history.py` L30, `update/from_file_snapshot.py` L51 | 4 处写死 `system_prompt.SYSTEM_PROMPT`（web only） | 原生栈收到 web 指令 |
| **B2: Stack Literal 缺原生栈** | `prompt_types.py` L34-41, `frontend/src/lib/stacks.ts` L3-10 | 只有 6 个 web 栈 | 前端不可选，后端白名单拒绝 |
| **B3: ADB 数据未注入** | `policies.py` 的 `build_adb_data_policy()` 无调用方 | 函数已就绪 | theme.json + skeleton.json 进不了 prompt |

### 1.3 已有但未接入的资产

| 资产 | 文件 | 状态 |
|---|---|---|
| Android XML system prompt | `prompts/android_xml_system.py` | 完整 92 行，含 Material Design 3 指令 |
| A2UI system prompt | `prompts/a2ui_system.py` | 完整 125 行，含 JSONL 协议规范 |
| ADB 数据格式化 | `policies.py` 的 `build_adb_data_policy()` | 完整 60 行 |
| Skeleton 截断 | `costs/prompt_compressor.py` | 完整 37 行，未接入 |
| Capture pipeline | `capture/pipeline.py` | AdbCapture + WinUiaCapture 已注册 |
| Skeleton parser | `scripts/skeleton_parser.py` | Android 类名映射完整 |
| Theme extractor | `scripts/theme_extractor.py` | 平台无关，像素采样 |
| 5 栈生成脚本 | `generate_5stacks.py` | 1-V+N-T 策略已验证 |
| Seed tool call 解析 | `agent/tools/seed_tool_call.py` | 火山引擎 XML 格式解析 |

---

## 2. 统一架构设计：System Prompt 路由器

### 2.1 核心改造：按栈分流 System Prompt

当前 4 处硬编码的根因是缺少一个"system prompt 路由器"。新增一个函数，按 stack 返回对应的 system prompt。

**新建 `backend/prompts/system_prompt_router.py`：**

```python
from prompts.prompt_types import Stack
from prompts.system_prompt import SYSTEM_PROMPT
from prompts.android_xml_system import ANDROID_XML_SYSTEM_PROMPT
from prompts.a2ui_system import A2UI_SYSTEM_PROMPT

# Phase 2 扩展时在此导入新增的 prompt
# from prompts.qt_qml_system import QT_QML_SYSTEM_PROMPT
# from prompts.wpf_system import WPF_SYSTEM_PROMPT
# from prompts.winui3_system import WINUI3_SYSTEM_PROMPT

# 原生栈集合，用于判断是否需要原生 prompt
NATIVE_STACKS = {"android_compose", "android_xml", "a2ui", "qt_qml", "windows_wpf", "winui3"}

# Web 栈集合
WEB_STACKS = {"html_tailwind", "html_css", "react_tailwind", "bootstrap", "vue_tailwind", "ionic_tailwind"}


def get_system_prompt(stack: Stack) -> str:
    """按栈返回对应的 system prompt。

    Web 栈统一使用 SYSTEM_PROMPT（含各 CDN 引入指令）。
    原生栈各自使用专用 prompt。
    """
    if stack in ("android_xml",):
        return ANDROID_XML_SYSTEM_PROMPT
    if stack == "a2ui":
        return A2UI_SYSTEM_PROMPT
    # Phase 2 扩展
    # if stack == "qt_qml":
    #     return QT_QML_SYSTEM_PROMPT
    # if stack == "windows_wpf":
    #     return WPF_SYSTEM_PROMPT
    # if stack == "winui3":
    #     return WINUI3_SYSTEM_PROMPT
    # android_compose 在 Phase 1.2 中新建 prompt 后加入
    # if stack == "android_compose":
    #     return ANDROID_COMPOSE_SYSTEM_PROMPT
    return SYSTEM_PROMPT  # 默认 web
```

### 2.2 4 处调用点修改

| 文件 | 行号 | 当前 | 改为 |
|---|---|---|---|
| `prompts/create/image.py` | L67 | `system_prompt.SYSTEM_PROMPT` | `get_system_prompt(stack)` |
| `prompts/create/text.py` | L34 | `system_prompt.SYSTEM_PROMPT` | `get_system_prompt(stack)` |
| `prompts/update/from_history.py` | L30 | `system_prompt.SYSTEM_PROMPT` | `get_system_prompt(stack)` |
| `prompts/update/from_file_snapshot.py` | L51 | `system_prompt.SYSTEM_PROMPT` | `get_system_prompt(stack)` |

每处只改 1 行（import + 调用），零风险。

---

## 3. 分阶段实施

### Phase 1: 打通 Android Compose 主线

**目标**：从 ADB 截图到 Kotlin Compose 代码的完整端到端链路。

| 步骤 | 文件 | 改动 | 工作量 |
|---|---|---|---|
| **1.1 扩展 Stack 定义** | `backend/prompts/prompt_types.py` | Stack Literal 加 `"android_compose"` | 1 行 |
| | `frontend/src/lib/stacks.ts` | Stack enum + STACK_DESCRIPTIONS 加 `android_compose` | 3 行 |
| | `frontend/src/components/core/StackLabel.tsx` | COMPONENT_LOGOS 加 Kotlin 图标 | 2 行 |
| **1.2 新建 Compose system prompt** | `backend/prompts/android_compose_system.py` | 参考 `android_xml_system.py` 模式，@Composable + Material3 + Column/Row | ~100 行新建 |
| **1.3 接入路由器** | `backend/prompts/system_prompt_router.py` | 新建路由器（见上 §2.1） | ~30 行新建 |
| | `backend/prompts/create/image.py` | 改 1 行调用 `get_system_prompt(stack)` | 1 行 |
| | `backend/prompts/create/text.py` | 同上 | 1 行 |
| | `backend/prompts/update/from_history.py` | 同上 | 1 行 |
| | `backend/prompts/update/from_file_snapshot.py` | 同上 | 1 行 |
| **1.4 ADB 数据注入** | `backend/prompts/create/image.py` | design_system 参数注入 `build_adb_data_policy(theme_json, skeleton_json)` | ~5 行 |
| | `backend/prompts/policies.py` | 接入 `truncate_skeleton` 截断 skeleton | 1 行 |
| **1.5 model_router 扩展** | `backend/costs/model_router.py` | STACK_MODEL_PREFERENCE 已有 `android_compose` | 0 行 |
| **1.6 codegen/utils.py** | 已有处理 | `extract_html_content` 已处理非 web 栈 | 0 行 |
| **1.7 AgentFileState** | 已有处理 | `default_path_for_stack` 已返回 `MainActivity.kt` | 0 行 |

**Phase 1 完成后验证**：
```bash
# 启动后端
cd backend && poetry run uvicorn main:app --reload --port 7001

# 启动前端
cd frontend && pnpm dev

# 前端选 "Android Compose" 栈 → 上传截图 → 生成 Kotlin 代码
# 验证：MainActivity.kt 含 @Composable 注解
```

### Phase 2: 补齐其余 4 栈

复用 Phase 1 的路由器架构，逐栈接入。

| 步骤 | 栈 | System Prompt | 工作量 |
|---|---|---|---|
| **2.1** | android_xml | `android_xml_system.py` **已写好**，路由器加 1 行 | 1 行 |
| | | `prompt_types.py` + `stacks.ts` 各加 1 项 | 2 行 |
| | | `StackLabel.tsx` 加 Android 图标 | 2 行 |
| **2.2** | a2ui | `a2ui_system.py` **已写好**，路由器加 1 行 | 1 行 |
| | | `prompt_types.py` + `stacks.ts` 各加 1 项 | 2 行 |
| | | `StackLabel.tsx` 加 A2UI 标签 | 2 行 |
| **2.3** | qt_qml | **新建** `prompts/qt_qml_system.py` | ~90 行新建 |
| | | 路由器加 1 行 + prompt_types + stacks | 3 行 |
| | | `StackLabel.tsx` 加 Qt 图标 | 2 行 |
| **2.4** | windows_wpf | **新建** `prompts/wpf_system.py` | ~90 行新建 |
| | | 路由器加 1 行 + prompt_types + stacks | 3 行 |
| | | `StackLabel.tsx` 加 WPF 图标 | 2 行 |

**Phase 2 各栈默认文件名**（需修改 `agent/state.py` 的 `default_path_for_stack`）：

| 栈 | 默认文件 | 说明 |
|---|---|---|
| android_xml | `activity_main.xml` | 布局文件 + `strings.xml` |
| a2ui | `surface.jsonl` | JSONL 声明式 UI |
| qt_qml | `main.qml` | QtQuick ApplicationWindow |
| windows_wpf | `MainWindow.xaml` | WPF Window + code-behind |

### Phase 3: WinUI 3 支持

参见 `design-docs/winui3-and-token-optimization-plan.md` Part 1 的 W1-W4。

| 步骤 | 文件 | 改动 |
|---|---|---|
| **3.1** | `validate_code.py` | 新增 `winui3` 栈 + `_validate_winui3_xaml()` |
| **3.2** | `scripts/skeleton_parser.py` | 加 Windows UIA 类名映射 + `platform` 参数 |
| **3.3** | `prompts/winui3_system.py` | 新建 system prompt |
| **3.4** | 路由器 + prompt_types + stacks + StackLabel + state | 接入 |

---

## 4. 配套 Token 优化（与原生栈接入同步推进）

| 优化 | 何时接入 | 依赖关系 |
|---|---|---|
| **T1 图片压缩** | Phase 1.4 同步 | 新建 `costs/image_compressor.py`，在 `create/image.py` 调用 |
| **T4 Skeleton 截断** | Phase 1.4 同步 | `policies.py` 接入已有 `truncate_skeleton` |
| **T2 1-V+N-T 批量** | Phase 2 完成后 | 需要 5 栈都可路由后才有意义 |
| **T5 历史图片截断** | Phase 1 同步 | `update/from_history.py` 截断旧图片 |
| **T6 国产模型路由** | 火山引擎充值后 | `model_router.py` 扩展路由表 |

---

## 5. 改动量汇总

### 5.1 新建文件

| 文件 | 行数 | 阶段 |
|---|---|---|
| `prompts/system_prompt_router.py` | ~30 | Phase 1 |
| `prompts/android_compose_system.py` | ~100 | Phase 1 |
| `costs/image_compressor.py` | ~40 | Phase 1 |
| `prompts/qt_qml_system.py` | ~90 | Phase 2 |
| `prompts/wpf_system.py` | ~90 | Phase 2 |
| `prompts/winui3_system.py` | ~100 | Phase 3 |

### 5.2 修改文件

| 文件 | 改动行数 | 阶段 |
|---|---|---|
| `prompts/prompt_types.py` | +5 行 | Phase 1-3 |
| `frontend/src/lib/stacks.ts` | +15 行 | Phase 1-3 |
| `frontend/src/components/core/StackLabel.tsx` | +12 行 | Phase 1-3 |
| `prompts/create/image.py` | +5 行 | Phase 1 |
| `prompts/create/text.py` | +2 行 | Phase 1 |
| `prompts/update/from_history.py` | +3 行 | Phase 1 |
| `prompts/update/from_file_snapshot.py` | +2 行 | Phase 1 |
| `prompts/policies.py` | +3 行 | Phase 1 |
| `agent/state.py` | +4 行 | Phase 2-3 |
| `agent/tools/validate_code.py` | +30 行 | Phase 3 |
| `scripts/skeleton_parser.py` | +25 行 | Phase 3 |
| `costs/model_router.py` | +4 行 | Phase 2-3 |

### 5.3 总计

- 新建：6 文件 ~450 行
- 修改：12 文件 ~110 行
- **总改动量：~560 行代码**

---

## 6. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 原生栈 prompt 质量不达标 | 先跑 `run_validate_e2e.py` 验证 6 栈通过 |
| 前端新增栈导致 UI 拥挤 | 用 SelectGroup 分组：Web / Android / Desktop / Declarative |
| 火山引擎欠费导致 T6 不可用 | T6 标记为 P2（待条件），不阻塞 Phase 1-2 |
| Skeleton 过大导致 token 爆炸 | T4 截断在 Phase 1.4 同步接入 |
| 原生栈不支持 screenshot_preview | Compose 的 preview.html 已有处理逻辑，其他栈后续扩展 |
| update 模式对原生栈不可用 | Phase 1 先打通 create 模式，update 模式 Phase 2 后补 |

---

## 7. 验收标准

| 阶段 | 验收项 | 验证方法 |
|---|---|---|
| Phase 1 | 前端可选 Android Compose | 下拉菜单出现该项 |
| Phase 1 | 截图 → Kotlin 代码生成 | 上传截图 → 输出含 @Composable |
| Phase 1 | ADB 数据注入 | theme.json 颜色出现在生成代码中 |
| Phase 1 | 图片压缩生效 | base64 长度 < 70KB |
| Phase 1 | Skeleton 截断生效 | prompt 总长 < 15K tokens |
| Phase 2 | 5 栈全部前端可选 | 下拉菜单 11 项 |
| Phase 2 | 5 栈 validate_code 通过 | `run_validate_e2e.py` 6/6 PASS |
| Phase 3 | WinUI 3 验证器通过 | mock UIA tree → 验证 XAML 结构 |
| Phase 3 | skeleton_parser 解析 Windows XML | mock capture → skeleton.json 非空 |
