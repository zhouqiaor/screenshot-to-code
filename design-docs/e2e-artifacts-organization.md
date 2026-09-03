# E2E 生成代码与测试结果的整理方案

> 聚焦 `e2e_demo/`、`e2e_test/`、`outputs/` 中"生成的代码"和"测试结果"两类产物。
> 生成时间：2026-09-02（末次刷新：2026-09-02，已执行首轮迁移）
> 前置文档：`fork-normalization-plan.md`（整体目录规范化）

---

## 一、现状问题

### 1.1 产物混在一起，没有 run 维度索引

当前所有脚本（`e2e_unified_verify.py` 第 42 行、`quick_verify.py`）都把三类产物**平铺**到同一个 `RUN_DIR`：

```
e2e_demo/run_20260901/
├── llm_android_compose.kt     ← 生成的代码
├── llm_android_xml.xml        ← 生成的代码
├── llm_qt_qml.qml            ← 生成的代码
├── llm_windows_html.html      ← 生成的代码
├── llm_a2ui.jsonl            ← 生成的代码
├── ws_compose.kt             ← 生成的代码（WebSocket 路径变体）
├── e2e_unified_report.json   ← 测试结果
├── validation_report.json     ← 测试结果
├── generation_report.json     ← 测试结果（含 model/tokens/cost）
├── unified_kt_screenshot.png  ← 渲染产物
├── unified_xml_screenshot.png ← 渲染产物
├── compose_render.html        ← 渲染产物
└── ...（40+ 文件混排）
```

**问题**：
- 生成代码、测试结果、渲染图、输入截图，全部混在一个平面目录
- 同一 run 的子批次（`deep_verify/`、`kotlin_pipeline/`）嵌套在里面，但命名规则不一致
- 没有 `manifest.json` 把"这次跑的什么模型、哪个截图、5 栈代码在哪、结果 PASS/FAIL"串起来
- 跨 run 无法对比（只有一个 `run_20260901`）

### 1.2 命名不统一

| 类型 | 现有命名 | 问题 |
|---|---|---|
| 生成代码 | `llm_<stack>.<ext>` / `ws_compose.kt` / `MainActivity.kt` / `settings_page.xaml` | 同一类产物 4 种命名 |
| 渲染图 | `unified_<stack>_screenshot.png` / `render_<stack>_screenshot.png` / `xml_device_screenshot.png` | 3 种前缀 |
| 测试报告 | `<name>_report.json` / `<name>_report.html` / `analysis.json` / `validation_results.json` | 无统一类型标识 |
| 输入截图 | `screenshots/run_20260901/source_screenshot_1024.png` | 在另一个目录 |

### 1.3 测试结果的 JSON schema 不统一

实际读到的 4 种报告结构各不相同：

| 报告 | 顶层结构 | 包含信息 |
|---|---|---|
| `validation_report.json` | `{total_stacks, valid, failed, results[]}` | 仅 PASS/FAIL |
| `e2e_unified_report.json` | `{timestamp, all_pass, environment, stacks{...}}` | 每栈详细 checks |
| `deep_verify/e2e_deep_report.json` | `{stack{checks, ok, screenshot, device_render}}` | 深度验证+aapt2+真机 |
| `generation_report.json` | `{model, base_url, calls[], total_tokens, total_cost_cny, stacks}` | 模型/Token/费用 |
| `e2e_test/validation_results.json` | `{stack{ok, stack, errors, warnings}}` | 仅 PASS/FAIL |

---

## 二、目标结构（以 run 为中心）

核心思想：**一次"截图 → 多栈生成 + 验证"= 一个 run**。所有产物归入该 run 目录，用 `manifest.json` 串联。

```
e2e_runs/                              # 所有 run 产物根目录（gitignored）
├── _templates/                        # 可复用模板（持久，不随 run 清理）— 待迁移
│   ├── android_xml/  kotlin_compose/  qt_qml/  a2ui/  windows_html/  winui3/
├── _fixtures/                         # 可复用测试输入（持久）— 待迁移
│   ├── settings_android_compose.kt  settings_android_xml.xml
│   ├── settings_qt_qml.qml  settings_a2ui.jsonl  settings_windows_win32.html
└── 20260901_doubao-seed-2-1-turbo-260628/   # ← run_id（{YYYYMMDD}_{model_slug}）
    ├── manifest.json                  # run 索引（模型/各栈文件/报告列表/子流程）
    ├── code/                          # 生成的代码（事实来源，llm_<stack> → <stack>.<ext>）
    │   ├── android_compose.kt
    │   ├── android_xml.xml
    │   ├── qt_qml.qml
    │   ├── windows_html.html
    │   ├── a2ui.jsonl
    │   └── variants/                  # 同栈不同路径的变体（ws_*/MainActivity/settings_page）
    │       ├── ws_compose_android_compose.kt
    │       └── settings_page_winui3.xaml
    ├── reports/                       # 测试结果（NN_<type>.json + 原始名 *.html）
    │   ├── 01_validation.json         # 5 栈 PASS/FAIL
    │   ├── 02_unified.json            # e2e_unified_report.json
    │   ├── 02_unified__1.json         # quick_verify_report.json（同名冲突自动加后缀）
    │   ├── 03_deep.json               # 深度验证（由 deep_verify/ 提升）
    │   ├── 04_compile.json            # 编译报告
    │   ├── 05_generation.json         # 模型/Token/费用
    │   ├── e2e_deep_report.html       # 人类可读报告保留原名
    │   ├── e2e_unified_report.html
    │   └── ...（其它 *_report.html 保留原名）
    ├── renders/                       # 渲染产物，保留原始文件名（避免覆盖）
    │   ├── unified_kt_screenshot.png
    │   ├── render_qml_screenshot.png
    │   ├── a2ui_render.html
    │   └── ...
    ├── inputs/                        # 本次 run 的输入
    │   ├── source_screenshot_1024.png
    │   └── ui_description.json
    ├── subruns/                       # 子流程产物整体保留（不拆平，避免冲突/丢嵌套目录）
    │   ├── deep_verify/               # 整体搬入；仅 e2e_deep_report.* 与 settings_page.xaml 被提升
    │   └── kotlin_pipeline/           # 整体搬入（pipeline 中间产物）
    └── misc/                          # 零散文件（预览/近似/对比/中间 dump 等）
        ├── a2ui_preview.html
        ├── compose_approximate.html
        └── ...
```

### 2.1 run_id 命名规则

**迁移（已执行）**：`{YYYYMMDD}_{model_slug}`
- 日期取自源目录名中的 `(\d{8})`（如 `run_20260901` → `20260901`）
- `model_slug` = `generation_report.json` 的 `model` 字段全小写、点已转连字符（如 `doubao-seed-2-1-turbo-260628`）
- 实际示例：`20260901_doubao-seed-2-1-turbo-260628`
- 不用时间戳，保证同一源目录重复整理得到稳定 id（幂等友好）

**未来脚本 `make_run_dir()`（前向改造）**：`{YYYYMMDD}T{HHMMSS}_{model_slug}`
- 新 run 带真实执行时刻，便于同一模型多轮对比

### 2.2 生成代码命名规则

| Stack | 文件 | 扩展名 |
|---|---|---|
| `android_compose` | `code/android_compose.kt` | .kt |
| `android_xml` | `code/android_xml.xml` | .xml |
| `qt_qml` | `code/qt_qml.qml` | .qml |
| `windows_html` | `code/windows_html.html` | .html |
| `a2ui` | `code/a2ui.jsonl` | .jsonl |
| `windows_wpf` | `code/windows_wpf.xaml` | .xaml |
| `winui3` | `code/winui3.xaml` | .xaml |
| 变体（同栈不同路径） | `code/variants/<stem>_<stack>.<ext>` | 同上 |

**映射依据**：`llm_<stack>` 主代码直接对应；其余 `ws_*`/`MainActivity`/`settings_page`/`kotlin_pipeline_*` 均为变体，归入 `variants/`。

### 2.3 测试结果命名规则

按"验证深度"编号前缀（数字保证阅读顺序），统一 `.json`；HTML 报告保留原始文件名：

| 编号 | 类型 | 内容来源 |
|---|---|---|
| `01_validation.json` | 语法层 | `validate_code.py` 输出 |
| `02_unified.json` | 结构层 | `e2e_unified_report.json` |
| `03_deep.json` | 深度层 | `deep_verify/e2e_deep_report.json`（提升） |
| `04_compile.json` | 编译层 | `e2e_compile_verify.py` |
| `05_generation.json` | 成本层 | `generation_report.json` |

> 多个 JSON 映射到同一编号时（如 `quick_verify_report.json` 也属 "unified" 层），自动加 `__N` 后缀消歧，绝不静默覆盖（见 2.5）。

### 2.4 manifest.json schema（v1，organize_runs.py 实际写入）

```json
{
  "run_id": "20260901_doubao-seed-2-1-turbo-260628",
  "created_at": "2026-09-02T12:11:28",
  "source": "e2e_demo/run_20260901 (migrated)",
  "code": {
    "a2ui": "code/a2ui.jsonl",
    "android_compose": "code/android_compose.kt",
    "android_xml": "code/android_xml.xml",
    "qt_qml": "code/qt_qml.qml",
    "windows_html": "code/windows_html.html"
  },
  "variants": {
    "settings_page": "code/variants/settings_page_winui3.xaml",
    "ws_compose": "code/variants/ws_compose_android_compose.kt"
  },
  "reports": [
    "reports/01_validation.json",
    "reports/02_unified.json",
    "reports/02_unified__1.json",
    "reports/03_deep.json",
    "reports/04_compile.json",
    "reports/05_generation.json",
    "e2e_deep_report.html",
    "e2e_unified_report.html"
  ],
  "renders": {
    "a2ui_render.html": "renders/a2ui_render.html",
    "unified_kt_screenshot.png": "renders/unified_kt_screenshot.png"
  },
  "subruns": ["deep_verify", "kotlin_pipeline"]
}
```

> 注：这是迁移脚本写入的 **v1 最小索引**。前向改造的 `make_run_dir()` 可在此基础扩展 `model` / `base_url` / `validation.per_stack` / `generation.total_cost_cny` 等字段（见原 2.4 设想，作为目标而非现状）。

### 2.5 冲突消解规则（零数据丢失）

`organize_runs.py` 在生成 moves 时检测目标路径冲突：
- 若两个源文件解析到同一目标路径：
  1. 优先用**源文件所在子目录名**做命名空间，如 `deep_verify/a2ui_render.html` → `renders/deep_verify/a2ui_render.html`，顶层同名文件保留在 `renders/a2ui_render.html`；
  2. 若源就在顶层（无子目录），则加 `__N` 数字后缀，如 `quick_verify_report.json` → `reports/02_unified__1.json`。
- 这一原则保证了"整体搬子流程目录"不会出现静默覆盖。

---

## 三、对脚本的改造建议（向前看）

现有脚本硬编码 `RUN_DIR = .../run_20260901`（第 42 行），应改为：

```python
from pathlib import Path
import os, time

def make_run_dir(model: str) -> Path:
    slug = model.replace(".", "-").lower()
    ts = time.strftime("%Y%m%dT%H%M%S")
    run_id = f"{ts}_{slug}"
    base = Path("e2e_runs") / run_id
    for sub in ("code", "code/variants", "reports", "renders", "inputs", "subruns", "misc"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    return base

RUN_DIR = make_run_dir(os.environ.get("E2E_MODEL", "doubao-seed-2-1-turbo"))
CODE_DIR = RUN_DIR / "code"
REPORTS_DIR = RUN_DIR / "reports"
RENDERS_DIR = RUN_DIR / "renders"
INPUTS_DIR = RUN_DIR / "inputs"
SUBRUNS_DIR = RUN_DIR / "subruns"
```

写入约定：
- 生成代码 → `CODE_DIR/<stack>.<ext>`
- 测试 JSON → `REPORTS_DIR/NN_<type>.json`
- 渲染图 → `RENDERS_DIR/<原始文件名>`（保留原名，避免覆盖）
- 输入截图 → `INPUTS_DIR/source_screenshot.png`
- 子流程中间产物 → `SUBRUNS_DIR/<name>/`（整体目录，不拆）
- 跑完写 `RUN_DIR/manifest.json`

这样每次跑自动成 run，无需手工命名目录，跨 run 天然可对比。`deep_verify` / `kotlin_pipeline` 类子流程产物**整体**落入 `subruns/`，只把规范化的 deep 报告与变体代码提升到第 1 级，避免冲突与嵌套目录丢失。

---

## 四、现有产物迁移方案（已执行 ✅）

迁移脚本 `backend/e2e/organize_runs.py`（默认 dry-run，加 `--apply` 执行）。首轮 `run_20260901` 已迁移完成。

| 来源 | 目标 | 动作 |
|---|---|---|
| `e2e_demo/run_20260901/llm_*` | `e2e_runs/<run>/code/<stack>.<ext>` | 移动 + 重命名 |
| `ws_compose.kt` | `e2e_runs/<run>/code/variants/ws_compose_android_compose.kt` | 移动 |
| `deep_verify/settings_page.xaml` | `e2e_runs/<run>/code/variants/settings_page_winui3.xaml` | 提升 + 移动 |
| `kotlin_pipeline/MainActivity.kt` | `e2e_runs/<run>/code/variants/MainActivity_android_compose.kt` | （在 subruns 整体内，见下） |
| `*_report.json`（validation/unified/deep/compile/generation） | `e2e_runs/<run>/reports/NN_<type>.json` | 移动 + 重命名 |
| `*_report.html` | `e2e_runs/<run>/reports/<原名>.html` | 移动（保留名） |
| `*_screenshot.png` / `*_render.html` / `render_*` | `e2e_runs/<run>/renders/<原名>` | 移动（保留名） |
| `ui_description.json` | `e2e_runs/<run>/inputs/` | 移动 |
| `screenshots/run_20260901/source_screenshot_1024.png` | `e2e_runs/<run>/inputs/` | 移动 |
| `deep_verify/`（整体，除已提升项） | `e2e_runs/<run>/subruns/deep_verify/` | 整体搬入 |
| `kotlin_pipeline/`（整体） | `e2e_runs/<run>/subruns/kotlin_pipeline/` | 整体搬入 |
| 其它零散文件（preview/approximate/对比/dump） | `e2e_runs/<run>/misc/` | 移动 |

**冲突处理实例**：`quick_verify_report.json` 与 `e2e_unified_report.json` 同属 `02` 层 → 后者占 `02_unified.json`，前者落 `02_unified__1.json`，无数据丢失。

**执行记录（2026-09-02）**：
- 迁移前对 `e2e_demo/run_20260901` 做了完整备份 → `.bak_e2e_run_20260901_before_organize/`（仓库根，非 `e2e_demo/`，不会被脚本重复发现）
- 首次 `--apply` 因"先搬子目录再搬提升文件"的顺序 bug 中途失败，已回滚并修正（`organize_runs.py` 改为"先搬第 1 级规范文件，再整体搬子目录"），二次执行成功
- 结果：`e2e_runs/20260901_doubao-seed-2-1-turbo-260628/` 含 code(7) / reports(13) / renders(15) / inputs(2) / subruns(2 目录，共 31 文件) / misc(10)，并写入 `manifest.json`
- 旧源目录 `e2e_demo/run_20260901` 已清空删除

> 待确认无误后，可删除备份 `.bak_e2e_run_20260901_before_organize/`。

---

## 五、.gitignore 补充（待执行）

```gitignore
# E2E 运行产物（含代码+结果+渲染，体积大，不入库）
e2e_runs/
# 历史遗留目录
e2e_demo/run_*/
e2e_demo/screenshots/
outputs/
ocr_logs2/
# 迁移备份（临时，确认后可删）
.bak_e2e_run_*/
```

仅保留 `_templates/` 和 `_fixtures/` 的索引（可在 `e2e_runs/` 下放 `.gitkeep` + 说明）。

---

## 六、优先级

| 优先级 | 动作 | 状态 |
|---|---|---|
| **P1** | 运行 `organize_runs.py --apply` 迁移现有 `run_20260901` | ✅ 已完成（2026-09-02） |
| **P0** | 改造 `e2e_unified_verify.py` 等脚本，RUN_DIR 改为 `make_run_dir()` 自动生成 | ⬜ 待做（根治散落，后续 run 自动规范） |
| **P1** | 在 `make_run_dir()` 中写扩展版 `manifest.json`（model/validation/generation 字段） | ⬜ 待做 |
| **P2** | `e2e_demo/templates/` → `e2e_runs/_templates/`，`e2e_test/settings_*` → `e2e_runs/_fixtures/` | ⬜ 待做（复用资产归位） |
| **P2** | 补充 `.gitignore`（见第五节） | ⬜ 待做 |
| **P3** | 确认迁移无误后删除 `.bak_e2e_run_20260901_before_organize/` 备份 | ⬜ 待做 |
