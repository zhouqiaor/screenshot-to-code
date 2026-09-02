# WinUI 3 支持规划 + 多模态 Token 优化规划

## Part 1: WinUI 3 支持规划

### 1.1 背景：WinUI 3 vs 现有 WPF 栈

| 维度 | WPF (现有) | WinUI 3 (新增) |
|---|---|---|
| 命名空间 | `http://schemas.microsoft.com/winfx/2006/xaml/presentation` | `Microsoft.UI.Xaml` (Windows App SDK) |
| 根元素 | `Window`, `Page`, `UserControl` | `Microsoft.UI.Xaml.Window` |
| 控件前缀 | 无前缀 (默认命名空间) | `` 或 `muxc:` |
| 控件来源 | `System.Windows.Controls.*` | `Microsoft.UI.Xaml.Controls.*` |
| 运行时 | .NET Framework / .NET Core | Windows App SDK 1.x |
| 打包 | EXE + DLL | MSIX 打包 / 免安装 |
| 代码绑定 | `x:Class` + code-behind (.cs) | `x:Class` + code-behind (.cs) |

### 1.2 现有基础设施盘点

**可直接复用：**
- `capture/win_uia.py` — Windows UI Automation 截图 + UIA tree dump（已含 mock 模式）
- `capture/pipeline.py` 的 `WinUiaCapturePipeline` — 已注册到 `CAPTURE_PIPELINES`
- `scripts/skeleton_parser.py` — UI tree XML 解析器（需扩展 Windows 类名映射）
- `scripts/theme_extractor.py` — 像素采样提取 theme.json（与平台无关）
- `agent/tools/validate_code.py` 的 `_validate_wpf_xaml()` — XAML 结构验证（需扩展 WinUI 3 命名空间）

**需新建：**
- `prompts/winui3_system.py` — WinUI 3 专用 system prompt
- `skeleton_parser.py` 的 Windows UIA 类名映射表

**需修改：**
- `validate_code.py` — 扩展 `windows_wpf` 或新增 `winui3` 栈
- `prompt_types.py` — Stack Literal 加 `"winui3"`
- `frontend/src/lib/stacks.ts` — Stack enum + STACK_DESCRIPTIONS
- `agent/state.py` — `default_path_for_stack()` 加 winui3 默认文件名
- `costs/model_router.py` — STACK_MODEL_PREFERENCE 加 winui3

### 1.3 实施计划

#### Phase W1: 验证器扩展 (validate_code)

**目标**：让 `validate_code` 能区分 WPF 和 WinUI 3 XAML。

**方案**：新增 `winui3` 栈，而非修改 `windows_wpf`。

```python
# validate_code.py 修改
Stack = Literal["html", "android_compose", "android_xml", "qt_qml", "a2ui", "windows_wpf", "winui3"]

# 新增 WinUI 3 常量
_WINUI3_NS = "http://schemas.microsoft.com/winfx/2006/xaml/presentation"
# WinUI 3 实际使用 Microsoft.UI.Xaml 命名空间，但 XAML 中常以 xmlns 声明
_WINUI3_NS_ALT = "using:Microsoft.UI.Xaml.Controls"
_WINUI3_ROOT_TAGS = {"Window", "Page", "UserControl", "Application"}

def _validate_winui3_xaml(code: str) -> tuple[...]:
    # 复用 _validate_wpf_xaml 逻辑，修改命名空间检查
    # 检查 Microsoft.UI.Xaml.Controls 控件名
```

**关键差异**：WinUI 3 XAML 中 `muxc:` 前缀控件来自 `Microsoft.UI.Xaml.Controls`，而 WPF 控件来自默认命名空间。验证器需检查 `using:Microsoft.UI.Xaml` 声明。

#### Phase W2: Skeleton Parser 扩展

**目标**：让 `skeleton_parser.py` 能解析 Windows UIA tree XML。

```python
# skeleton_parser.py 新增 Windows UIA 类名映射
_WIN_CLASS_MAPPING: dict[str, str] = {
    "Text": "text",
    "Button": "button",
    "Edit": "text_input",
    "CheckBox": "checkbox",
    "RadioButton": "radio_button",
    "ComboBox": "dropdown",
    "Slider": "slider",
    "ProgressBar": "progress",
    "Image": "image",
    "List": "list",
    "ListItem": "list_item",
    "Tree": "tree",
    "TreeItem": "tree_item",
    "MenuItem": "menu_item",
    "Tab": "tab",
    "TabItem": "tab_item",
    "Pane": "container",
    "Group": "container",
    "Window": "container",
    "ToolBar": "toolbar",
    "StatusBar": "status_bar",
    "ScrollBar": "scroll",
    "Custom": "unknown",  # WinUI 3 自定义控件
}

def parse_ui_tree(xml_path: str, platform: str = "android") -> dict[str, Any]:
    """解析 UI tree XML，按平台选择类名映射表。"""
    class_mapping = _WIN_CLASS_MAPPING if platform == "windows" else _CLASS_MAPPING
    # ... 后续逻辑不变
```

**注意**：`capture/pipeline.py` 的 `WinUiaCapturePipeline` 已调用 `parse_ui_tree`，但当前 `parse_ui_tree` 只识别 Android 格式。需加 `platform` 参数或自动检测 XML 根元素。

#### Phase W3: System Prompt 编写

**目标**：`prompts/winui3_system.py`，参考 `android_xml_system.py` 模式。

核心内容：
- 输出文件：`MainWindow.xaml` + `MainWindow.xaml.cs` (code-behind)
- 根元素：`<winui:Window>` (xmlns:winui="using:Microsoft.UI.Xaml")
- 控件：`Button`, `TextBlock`, `TextBox`, `CheckBox`, `ComboBox`, `Slider`, `ListView`
- 布局：`Grid`, `StackPanel`, `RelativePanel`
- 样式：`Style` + `StaticResource`
- 字符串资源：`x:Uid` + `.resw` 文件

#### Phase W4: 管线接入

| 文件 | 修改 |
|---|---|
| `prompt_types.py` | Stack Literal 加 `"winui3"` |
| `frontend/src/lib/stacks.ts` | Stack enum + STACK_DESCRIPTIONS 加 `winui3` |
| `agent/state.py` | `default_path_for_stack()` 加 `winui3 → "MainWindow.xaml"` |
| `costs/model_router.py` | `STACK_MODEL_PREFERENCE` 加 `"winui3": Llm.GEMINI_3_6_FLASH_LOW` |
| `create/image.py` | 按 stack 分流 system prompt（Phase 1 通用改造） |

---

## Part 2: 多模态 Token 优化规划

### 2.1 当前 Token 消耗分析

#### 基线：单次截图 → 单栈代码生成

| 消耗源 | Token 量 | 文件位置 | 优化空间 |
|---|---|---|---|
| 图片 base64 (PNG) | ~15K tokens | `create/image.py` 第 55 行 | 压缩到 JPEG 768px → ~3K |
| 图片 detail=high | ×1.5 倍率 | `create/image.py` 第 55 行 | 改 auto/low 省 30-50% |
| System prompt | ~3K tokens | `system_prompt.py` (96 行) | 缓存命中后 ~0.3K |
| User prompt 模板 | ~1.5K tokens | `create/image.py` 第 18-44 行 | 精简指令 |
| 设计系统块 | 0-2K tokens | `design_system.py` | 按需注入 |
| Agent 循环历史 | 每轮 +2-5K | `from_history.py` | 截断旧图片 |
| **单次总计** | **~22-25K** | | 可降到 **~8-12K** |

#### 最差场景：5 栈独立 vision 调用

| 调用 | Token 量 | 说明 |
|---|---|---|
| 5 × vision 调用 | 5 × 15K = 75K | 每栈各发一次截图 |
| 5 × system prompt | 5 × 3K = 15K | 重复发送 |
| 5 × output | 5 × 4K = 20K | 各栈代码输出 |
| **总计** | **~110K** | |

#### 已有优化：5 栈脚本 (generate_5stacks.py)

| 步骤 | Token 量 | 说明 |
|---|---|---|
| 1 × vision 分析 | ~15K | 1 次截图 → UI 描述 JSON |
| 5 × text 生成 | 5 × 2K = 10K | 纯文本调用，无图片 |
| output | 5 × 4K = 20K | 各栈代码输出 |
| **总计** | **~45K** | **省 59%** |

### 2.2 六大优化策略

#### 策略 T1: 图片压缩 (省 60-80% 图片 token)

**现状**：`create/image.py` 直接传 data URL，`detail: "high"`。
**已有参考**：`generate_5stacks.py` 用 768px JPEG（~50KB → ~65KB base64）。

**实施方案**：

```python
# 新建 backend/costs/image_compressor.py
from PIL import Image
import io, base64

def compress_screenshot(image_data_url: str, max_width: int = 768, quality: int = 80) -> str:
    """压缩截图为 JPEG base64 data URL。

    PNG 1080×2400 (~872KB) → JPEG 768×1707 (~50KB)
    Token: ~15K → ~3K，省 80%
    """
    # 解码 base64 → PIL Image → resize → JPEG → base64
    ...
    return f"data:image/jpeg;base64,{b64}"

# 修改 create/image.py
image_data_urls = [compress_screenshot(url) for url in image_data_urls]
# detail 改为 "auto"（让模型按需选分辨率）
```

**改动文件**：
- 新建 `backend/costs/image_compressor.py`
- 修改 `backend/prompts/create/image.py` 第 51-57 行

**预估收益**：单次 vision 调用省 12K tokens (15K→3K)

#### 策略 T2: 1-Vision + N-Text 批量生成 (省 65% 多栈总 token)

**现状**：`generate_5stacks.py` 已验证此策略，但未接入主管线。
**问题**：主管线 (`create/image.py`) 每个栈独立发 vision 请求。

**实施方案**：在 `prompts/pipeline.py` 层面引入"批量生成模式"。

```python
# prompts/pipeline.py 新增
async def build_batch_prompt_messages(
    stacks: list[Stack],
    input_mode: InputMode,
    prompt: UserTurnInput,
    ...
) -> list[Prompt]:
    """1 次 vision → N 次纯文本的批量生成管线。

    Step 1: 调用 vision 模型分析截图 → ui_description (JSON)
    Step 2: 对每个 stack，用 ui_description 构建纯文本 prompt（无图片）
    """
    # Step 1: 复用 generate_5stacks.py 的 VISION_PROMPT
    # Step 2: 对每个 stack 调用 make_stack_prompt(stack, ui_desc)
```

**改动文件**：
- 修改 `backend/prompts/pipeline.py` — 新增 `build_batch_prompt_messages`
- 修改 `backend/routes/generate_code.py` — 支持多栈批量请求
- 前端新增"多栈生成"模式选项

**预估收益**：5 栈总 token 110K → 45K (省 59%)

#### 策略 T3: Prompt Caching (省 90% system prompt token)

**现状**：`TokenUsage` 已跟踪 `cache_read` / `cache_write`，但代码不主动管理 cache key。
**Anthropic 支持**：prompt prefix 缓存（5 分钟 TTL，1.25× input 写入费率，0.1× 读取费率）。

**实施方案**：

```python
# 修改 prompts/create/image.py
# 将 system prompt + design_system_block 合并为 cacheable prefix

# Anthropic provider 已支持 cache_control 标记
# 修改 backend/agent/providers/anthropic.py
# 在 system message 上加 cache_control: {"type": "ephemeral"}
{
    "role": "system",
    "content": [
        {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}},
    ],
}
```

**改动文件**：
- 修改 `backend/agent/providers/anthropic.py` — 加 cache_control 标记
- 修改 `backend/prompts/create/image.py` — 分离 cacheable prefix
- 修改 `backend/prompts/update/from_history.py` — 历史消息缓存

**预估收益**：system prompt 3K tokens → 0.3K (cache hit 90% off)，每次 update 省约 2.7K

#### 策略 T4: Skeleton 截断 (省 80% skeleton token)

**现状**：`prompt_compressor.py` 已实现 `truncate_skeleton()` 但未接入。
**问题**：复杂 UI skeleton 可达 20K+ tokens。

**实施方案**：

```python
# 修改 policies.py 的 build_adb_data_policy()
from costs.prompt_compressor import truncate_skeleton

def build_adb_data_policy(theme_json: str | None, skeleton_json: str | None) -> str:
    # 截断 skeleton 到 8K chars (~2K tokens)
    if skeleton_json:
        skeleton_json = truncate_skeleton(skeleton_json, max_chars=8000)
    # ... 后续不变
```

**更优方案**：不是简单截断，而是"扁平化"——只保留叶子节点（text/button/switch），去掉中间容器层。

```python
def flatten_skeleton(skeleton: dict, max_nodes: int = 50) -> dict:
    """提取叶子节点，丢弃中间容器层。"""
    leaves = []
    def collect_leaves(node):
        children = node.get("children", [])
        if not children:
            leaves.append(node)
        else:
            for c in children:
                collect_leaves(c)
    collect_leaves(skeleton.get("root", {}))
    return {"screen": skeleton.get("screen", {}), "leaves": leaves[:max_nodes]}
```

**改动文件**：
- 修改 `backend/prompts/policies.py` — 接入 `truncate_skeleton` 或 `flatten_skeleton`
- 扩展 `backend/costs/prompt_compressor.py` — 加 `flatten_skeleton`

**预估收益**：skeleton 20K → 2K tokens (省 90%)

#### 策略 T5: 历史图片截断 (省 60% update token)

**现状**：`from_history.py` 的 `build_update_prompt_from_history()` 重放完整历史，包括旧截图。
**问题**：第 3 轮 update 时，前 2 轮的截图仍以 base64 发送。

**实施方案**：保留历史文本，丢弃旧轮次的图片。

```python
# 修改 prompts/update/from_history.py
def build_update_prompt_from_history(...):
    for index, item in enumerate(history):
        item_copy = dict(item)
        # 只保留最近 1 轮的图片，丢弃更早的
        if index < len(history) - 2:
            item_copy["images"] = []
        prompt_messages.append(build_history_message(item_copy))
```

**改动文件**：
- 修改 `backend/prompts/update/from_history.py` — 截断旧图片

**预估收益**：3 轮 update 省 2 × 15K = 30K tokens

#### 策略 T6: 模型路由优化 (省 70% 成本)

**现状**：`model_router.py` 已按栈路由，但路由表未含原生栈。

**当前路由**：
| 栈 | 模型 | 输入费率 | 备注 |
|---|---|---|---|
| html_tailwind | Gemini 3.6 Flash HIGH | $1.50/M | 复杂布局 |
| react_tailwind | Gemini 3.6 Flash HIGH | $1.50/M | 复杂布局 |
| html_css | Gemini 3.6 Flash LOW | $1.50/M | 中等 |
| bootstrap | Gemini 3.6 Flash LOW | $1.50/M | 中等 |
| android_compose | Gemini 3.6 Flash MINIMAL | $1.50/M | 结构化 |

**国产模型替代方案**（火山引擎充值后）：
| 栈 | 当前模型 | 建议模型 | 输入费率 | 节省 |
|---|---|---|---|---|
| android_compose | Gemini Flash MINIMAL ($1.50) | doubao-seed-1.6-flash ($0.021) | 98% 省 |
| html_css | Gemini Flash LOW ($1.50) | doubao-seed-1.8 ($0.111) | 93% 省 |
| android_xml | (未路由) | doubao-seed-1.6-flash ($0.021) | 最便宜 |
| a2ui | (未路由) | doubao-seed-1.6-flash ($0.021) | 结构化 |
| winui3 | (未路由) | doubao-seed-1.8 ($0.111) | 中等 |
| html_tailwind | Gemini Flash HIGH ($1.50) | Gemini Flash HIGH (保留) | 复杂布局不省 |
| react_tailwind | Gemini Flash HIGH ($1.50) | Gemini Flash HIGH (保留) | 复杂布局不省 |

**改动文件**：
- 修改 `backend/costs/model_router.py` — STACK_MODEL_PREFERENCE 扩展

### 2.3 优化效果预估

#### 单栈单次生成 (html_tailwind)

| 优化前 | 优化后 | 节省 |
|---|---|---|
| 图片 15K | 图片 3K (T1 压缩) | -12K |
| System 3K | System 0.3K (T3 缓存) | -2.7K |
| Skeleton 0 | Skeleton 0 (web 无) | 0 |
| 总计 ~22K | 总计 ~8K | **-64%** |

#### 5 栈批量生成 (android_compose + xml + qml + html + a2ui)

| 优化前 (独立调用) | 优化后 (T1+T2+T3+T4+T6) | 节省 |
|---|---|---|
| 5 × 图片 75K | 1 × 图片 3K (T1+T2) | -72K |
| 5 × system 15K | 5 × 0.3K = 1.5K (T3) | -13.5K |
| 5 × skeleton 0 | 0 (原生栈无 skeleton) | 0 |
| 5 × output 20K | 5 × 4K = 20K (不变) | 0 |
| 模型费率 $1.50/M | 混合 $0.02-0.11/M (T6) | -90% 成本 |
| 总计 ~110K | 总计 ~25K | **-77%** |

#### 3 轮 update (带历史)

| 优化前 | 优化后 (T1+T3+T5) | 节省 |
|---|---|---|
| Round 1: 22K | Round 1: 8K (T1+T3) | -14K |
| Round 2: 37K (22+15历史图片) | Round 2: 11K (8+3压缩历史) | -26K |
| Round 3: 52K | Round 3: 14K (8+0.3缓存+0旧图) | -38K |
| 总计 111K | 总计 33K | **-70%** |

### 2.4 实施优先级

| 优先级 | 策略 | 改动量 | 预估收益 | 依赖 |
|---|---|---|---|---|
| P0 | T1 图片压缩 | 2 文件 (新建+改) | -12K/次 | 无 |
| P0 | T4 Skeleton 截断 | 2 文件 (改) | -18K/次 | 无 |
| P1 | T2 1-Vision+N-Text | 3 文件 (改) | -65K (5栈) | T1 |
| P1 | T5 历史图片截断 | 1 文件 (改) | -30K (3轮) | T1 |
| P2 | T3 Prompt Caching | 2 文件 (改) | -2.7K/次 | Anthropic provider |
| P2 | T6 国产模型路由 | 1 文件 (改) | -90% 成本 | 火山引擎充值 |

### 2.5 Token 治理仪表盘

已有基础设施（`costs/` 目录）：

| 模块 | 状态 | 接入情况 |
|---|---|---|
| `pricing.py` | 完整 | 33 个模型定价已录入 |
| `token_usage.py` | 完整 | input/output/cache_read/cache_write |
| `budget_checker.py` | 完整 | 50/75/90% 阈值告警 + 硬上限 |
| `model_router.py` | 部分 | 7 栈路由表（缺原生栈） |
| `prompt_compressor.py` | 定义未接入 | `truncate_skeleton` 已写 |
| `metrics.py` | 完整 | Prometheus 端点 7 指标 |
| `volcano_models.py` | 完整 | 18 个模型 + 额度 + 定价 |

**建议**：在 `/metrics` 端点基础上，前端新增 Token 消耗可视化面板（按栈/模型/时间维度）。
