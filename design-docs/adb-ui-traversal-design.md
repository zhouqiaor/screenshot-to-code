# ADB UI 遍历采集 — 详细设计方案

> 目标设备：`200.47.94.166:5555`
> 分支：`adb-ui-traversal`　工作区：`C:/Code/screenshot-to-code-adb-traversal`
> 基线 commit：`3097ff1`　日期：2026-09-02

---

## 0. TL;DR

在现有「单屏 ADB 采集」能力之上，扩展出**多屏自动遍历**能力：自动在设备上导航，逐屏采集
`(截图, uiautomator UI 树, skeleton.json)` 三元组，并产出状态转移图（UTG），
供 screenshot-to-code 做批量代码生成的数据源。

三个关键判断：

1. **目标设备是机顶盒（TEQU-S2C，3840×2160）**，UI 是 D-Pad 焦点驱动的 TV launcher，
   纯 `input tap` 点击不可靠 → 必须实现**双模导航（touch / dpad）**。
2. **零侵入优先**：机顶盒上装 agent APK（uiautomator2 的 atx-agent）风险高且可能不被允许
   → 主链路只用原生 `adb`（`uiautomator dump` + `screencap`），把 uiautomator2 留在可选加速后端。
3. **遍历用 GUI-model 驱动**（参考 DroidBot），不是 Monkey 随机点：以「UI 结构签名」识别状态，
   以「动作 + BACK 回溯」做深度优先探索，避免状态爆炸与跑飞。

---

## 1. 背景与目标

现有仓库已具备**单屏**采集链路（`backend/scripts/`）：

| 文件 | 职责 |
|---|---|
| `adb_capture.py` | `screencap` + `uiautomator dump` → `screenshot.png` + `ui_tree.xml` |
| `skeleton_parser.py` | `ui_tree.xml` → `skeleton.json`（class / bounds / component_type / fill_ratio） |
| `theme_extractor.py` | 截图 + skeleton → `theme.json` |
| `run_adb_pipeline.py` | 编排上述三步，产出 data URL |
| `capture/pipeline.py` | `CapturePipeline` Protocol + `AdbCapturePipeline` / `WinUiaCapturePipeline` 注册表 |
| `routes/adb.py` | `POST /api/adb/capture`、`GET /api/adb/devices` |

缺口：只能抓「当前这一屏」，没有**跨屏遍历**。本方案补齐这一层。

**目标产出**：一次运行，自动产出设备上的多屏数据集 + 状态转移图，且能被下游
`skeleton_parser` / `theme_extractor` / 代码生成链路直接消费。

---

## 2. 设备实测基线（决定设计的关键事实）

以下均为本次实测所得，非推测：

| 项 | 实测值 | 对设计的影响 |
|---|---|---|
| 连接 | `200.47.94.166:5555` 已 `device` 态（另有 `200.47.91.1:5555` 同型号） | 支持 `-s` 指定设备 |
| 型号 | `TEQU-S2C`（product/model）、`HWTEQU-S2C` | 机顶盒，非手机 |
| 分辨率 | **3840×2160**、density **480** | 4K，单张 PNG **1.05 MB** → 必须降采样 |
| 当前页 | launcher，`package=com.device.launcheridea` | TV 桌面九宫格 |
| UI 树 | 51 节点，树深 14 | 单次 dump 19 KB，规模可控 |
| `clickable=true` | **14**（FrameLayout 瓦片 + ImageView 图标） | 点击候选 |
| `focusable=true` | **9**（ViewPager、RecyclerView、7 个应用图标 ImageView） | **D-Pad 候选** |
| `focused=true` | **0**（当前无任何焦点项） | **必须先按键建立焦点才能导航** |
| `scrollable=true` | 1（RecyclerView） | 长列表需滚动分页 |
| 文本节点 | 应用列表(标题) / 云会议 / 白板 / 投屏 / 文件管理 / 浏览器 / 智能管家 / 玩机攻略 | 7 个应用入口 |

**结论**：这是一个 `ViewPager + RecyclerView` 的 TV 应用网格，7 个图标。
`focusable`(9) 与 `clickable`(14) 并存，且当前 `focused=0` ——
**纯 tap 方案在这台设备上会失效或不稳定，D-Pad 焦点寻路是刚需。**

---

## 3. Worktree 规划方案（强制多分支并行隔离）

按项目强制规则，所有开发一律走 worktree，禁止在主工作区来回切分支。

### 3.1 本次实际执行的命令（已验证）

```bash
# 1) 建分支（基于 main 基线）
cd /c/Code/screenshot-to-code
git branch adb-ui-traversal main

# 2) 建 worktree（同级父目录，避免嵌套）
git worktree add C:/Code/screenshot-to-code-adb-traversal adb-ui-traversal

# 3) 查看
git worktree list
# C:/Code/screenshot-to-code                3097ff1 [main]
# C:/Code/screenshot-to-code-adb-traversal  3097ff1 [adb-ui-traversal]
```

### 3.2 日常操作速查

```bash
git worktree list                                   # 查看列表
git worktree add C:/Code/<repo>-<branch> <branch>   # 为已有分支建
git worktree add -b <new> C:/Code/<repo>-<new> main # 新建分支并建
git worktree remove C:/Code/<repo>-<branch>         # 移除（干净时）
git worktree remove --force C:/Code/<repo>-<branch> # 强制移除（有改动）
git worktree prune                                  # 清理已删目录的残留引用
git branch -d <branch>                              # 删除已合并分支
```

### 3.3 本环境的三个坑（实测踩过，务必规避）

| 坑 | 现象 | 规避 |
|---|---|---|
| **斜杠分支名静默失败** | `git branch feat/xxx main` 返回 0，但 ref 根本没建；`.git/refs/heads/feat/` 目录会在命令间**被回滚消失** | 本环境改用**无斜杠**分支名（如 `adb-ui-traversal`）；确实需要 `feat/` 前缀时用 `-` 代替 `/` |
| **`adb pull` 到 `/tmp` 失败** | `adb` 是 Windows 程序，不认 Git Bash 的 `/tmp` 映射，报 `cannot create file/directory` | 输出目录一律用 **Windows 风格路径**（`C:/Code/...`） |
| **删除类 git 操作被拦截** | `git worktree prune` / `remove --force` 会让 shell 静默终止（exit 1，无输出） | 需要清理时提高权限执行，或手动删残留目录；`add` 不受影响 |

> 另注：`C:/Code` 下已存在 `screenshot-to-code-fresh / -ocrfix / -pr / -spr / -tok / -compose / -clone`
> 等多个历史**独立 clone**（不是注册 worktree），勿与本 worktree 混淆。

---

## 4. 业界方案调研与选型

### 4.1 候选对比

| 方案 | 需在设备装 APK/JAR | 采集速度 | 树信息完整度 | 跨平台 | 适配本机顶盒 | 结论 |
|---|---|---|---|---|---|---|
| **原生 adb**（`uiautomator dump` + `screencap`） | **否** | 慢（1–3 s/屏） | 完整 hierarchy | Android | ✅ 最佳 | **主选** |
| **uiautomator2** (openatx) | 是（atx-agent + server jar） | 快（~0.2 s/屏） | 完整 + XPath + 实时 | Android | ⚠️ 需装 agent | **可选加速后端** |
| **DroidBot** (honeynet) | 否 | 中 | UTG + 方法跟踪 | Android | ✅ | **算法参考**（GUI-model） |
| **AppCrawler** (seveniruby) | 是（基于 Appium） | 慢 | 完整 | Android+iOS | ⚠️ 重 | 不采用 |
| **Appium** | 是（driver） | 慢 | 完整 | 多平台 | ⚠️ 很重 | 不采用 |
| **Maxim**（Monkey 增强） | 是（push framework/monkey.jar） | 快 | **少（无 UI 树）** | Android | ❌ | 不适合采集（只要压测） |
| **SoloPi** (alipay) | 是（APK） | — | — | Android | ❌ | 录制回放，不适用 |
| `uiautomatorviewer` | — | — | — | — | ❌ | **已被 Google 从 SDK 移除**，不再分发 |

### 4.2 选型结论

> **主链路 = 原生 adb（零侵入）**，**算法借鉴 DroidBot（GUI-model 遍历 + UTG）**，
> **uiautomator2 作为可选加速后端**，通过 `UiBackend` 抽象隔离，后续可无痛切换。

理由：
- 目标是**采集数据**而非做测试，需要完整 UI 树 → 排除 Maxim（无树）。
- 设备是机顶盒，装 agent APK 风险高/可能不允许 → 排除 uiautomator2 / Appium / AppCrawler 作为主链路。
- `uiautomator dump` 虽慢（1–3 s），但对离线数据集采集完全够用；且**零依赖、零侵入、任何 adb 设备即插即用**。
- DroidBot 的「不需系统修改或应用插桩 + 基于 GUI 模型而非随机 + 生成 UTG」正是我们要的形态，
  直接借鉴其状态建模与事件生成思想，但用原生 adb 重新实现（DroidBot 依赖较重且偏测试）。

---

## 5. 架构设计

### 5.1 分层

```
┌──────────────────────────────────────────────────────────┐
│  AdbTraversalPipeline   (capture/pipeline.py, id=adb_traversal) │
│  ── 实现 CapturePipeline Protocol，注册进 CAPTURE_PIPELINES     │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│  Traverser  (scripts/adb_traversal.py)                    │
│  ── 状态识别 / 动作枚举 / DFS + BACK 回溯 / 去重 / 熔断      │
└──────┬──────────────────────────┬────────────────────────┘
       │                          │
┌──────▼──────────┐      ┌────────▼──────────┐
│  UiBackend      │      │  Recorder         │
│  (抽象)          │      │  ── 落盘 + UTG    │
│  ├ AdbBackend   │      └───────────────────┘
│  │  (零侵入,主)  │
│  └ U2Backend    │      ┌───────────────────┐
│     (可选加速)   │      │  复用现有模块      │
└─────────────────┘      │  adb_capture      │
                         │  skeleton_parser  │
                         │  theme_extractor  │
                         └───────────────────┘
```

### 5.2 核心模块职责

| 模块 | 职责 |
|---|---|
| `AdbBackend` | 封装 `screencap` / `uiautomator dump` / `input tap` / `input keyevent` / `dumpsys activity`，全部走 `-s <device>` |
| `UiBackend`（Protocol） | `dump_tree()` / `screenshot()` / `tap()` / `key()/focus_and_press()` / `current_activity()` —— 隔离 adb 与 uiautomator2 |
| `Traverser` | 状态签名、动作枚举、DFS 探索、去重、熔断、安全过滤 |
| `Recorder` | 落盘 `states/<idx>_<sig8>/` + `manifest.json` + `graph.json` |
| `AdbTraversalPipeline` | 接入 `capture/pipeline.py` 注册表，复用 `CaptureResult` |

---

## 6. 核心算法

### 6.1 状态签名（去重的核心）

不能直接用整棵树的哈希 —— `bounds`、焦点、选中态、计时器文本一变，签名就变，会状态爆炸。

**签名只取「稳定结构」**：按树的前序遍历，拼接每个节点的
`(class, resource-id, text, content-desc)`，忽略 `bounds`、`focused`、`selected`、`index`。

```
sig = sha1( "|".join(f"{cls}|{rid}|{text}|{desc}" for node in preorder(tree)) )[:16]
```

例外处理：
- 含明显易变文本（纯数字、时间、进度百分比）的节点，文本置空后再签名。
- 可选 `--fuzzy`：只取 class 序列，更宽松（同构列表页合并）。

### 6.2 动作枚举

从当前树提取候选动作，优先级：

1. `clickable=true` 或 `focusable=true`
2. bounds 面积 > 屏幕的 0.5%，且完整落在屏内
3. 排除系统导航栏 / 状态栏区域（可按 `--exclude-bottom-px` 配置）
4. 安全检查命中黑名单文本的（删除 / 支付 / 卸载 / 注销 / 重置）默认跳过

每个动作记录：`(index, class, text, resource-id, bounds, center, kind)`。

### 6.3 探索循环（DFS + BACK 回溯）

不重放动作路径（重放会漂移），而是**「动作 → 观察 → 递归探索 → BACK 回到父状态」**：

```
def explore(depth):
    sig = observe()                       # 稳定等待后采集
    if sig not in visited:
        record(sig, depth)                # 落盘 screenshot/ui_tree/skeleton/meta
    st = visited[sig]

    for act in st.actions:
        if act in st.tried: continue
        if budget_exceeded(): return
        st.tried.add(act)

        perform(act)                      # tap 或 dpad 聚焦+确认
        wait_stable()
        new_sig = observe()

        if new_sig != sig:
            record_edge(sig, new_sig, act)
            if depth + 1 <= max_depth:
                explore(depth + 1)
                go_back_to(sig)           # BACK 直到签名回到 sig，失败则重启 app
        # 无变化：动作无效，原地继续下一个
```

要点：
- **`wait_stable()`**：轮询 dump，连续 2 次签名一致（或超时 3 s）才认为页面稳定。
  机顶盒动画慢，这一步不能省，否则会采到中间态。
- **`go_back_to(sig)`**：按 `KEYCODE_BACK`，每次后比对签名；最多 K 次。
  若回不到（例如动作把 app 切走了），则 `am force-stop` + 重启目标 app 回到根状态。
- **深度/状态数/步数三重熔断**：`max_depth`（默认 4）、`max_states`（默认 30）、`max_steps`（默认 200）。
- **连续无新状态熔断**：连续 N 次动作未产生新状态则停止（防死循环）。

### 6.4 滚动分页

`RecyclerView`/`ScrollView` 类节点标 `scrollable=true`，对它们额外生成
「向下滚动一屏」动作，滚动后重新采集，从而覆盖长列表的后续页。

---

## 7. 导航策略（双模，本方案关键）

### 7.1 模式选择

```
nav_mode = auto | touch | dpad
```

`auto` 判定（按优先级）：
1. `adb shell getprop ro.build.characteristics` 含 `tv` / `device` 类型 → `dpad`
2. 树中 `focusable` 节点数 > 0 且 `clickable` 节点多为容器（非叶子） → `dpad`
3. 否则 → `touch`

本机顶盒走 `dpad`。

### 7.2 touch 模式

```
adb shell input tap <cx> <cy>      # cx,cy = bounds 中心
```

### 7.3 dpad 模式（焦点寻路）

**难点**：本机顶盒当前 `focused=true` 节点数为 **0**，直接按 `DPAD_CENTER` 无效。

算法 `focus_and_press(target)`：

```
1. dump 当前树
2. 若 target 已 focused → 按 KEYCODE_DPAD_CENTER / ENTER，返回
3. 若全树 focused 节点数 == 0：
       按一次 KEYCODE_DPAD_DOWN（建立初始焦点），重新 dump
4. 循环至多 N 次（默认 12）：
       cur = 当前 focused 节点
       若 cur 为 None → 按 DPAD_DOWN 建立焦点，continue
       按 target 与 cur 的几何关系决定方向键：
           主要偏移在 X 轴 → LEFT / RIGHT
           主要偏移在 Y 轴 → UP / DOWN
       按该方向键，sleep，重新 dump
       若 target focused → 按 CENTER，返回
5. 超时：降级为 input tap target 中心（兜底）
```

> 兜底 tap 很重要：部分 TV 页面焦点不可达但触控仍有效。

### 7.4 等待参数（机顶盒慢，需放宽）

| 参数 | 默认 | 说明 |
|---|---|---|
| `settle_delay` | 0.8 s | 动作后首次等待 |
| `stable_timeout` | 3.0 s | 稳定轮询上限 |
| `stable_interval` | 0.4 s | 稳定轮询间隔 |
| `dump_timeout` | 20 s | 单次 dump 超时（4K 屏 dump 较慢） |

---

## 8. 数据结构与产出

### 8.1 目录布局

```
runs/adb_traversal/<device>_<timestamp>/
├── manifest.json              # 设备信息、运行参数、统计、耗时
├── graph.json                 # UTG：states[] + edges[]（可接 DroidBot 风格可视化）
└── states/
    ├── 000_ab12cd34/
    │   ├── screenshot.png     # 原始 4K（1.05 MB）
    │   ├── screenshot_768.jpg # 降采样（供 LLM / 预览，~50 KB）
    │   ├── ui_tree.xml        # uiautomator 原始 dump
    │   ├── skeleton.json      # skeleton_parser 产出
    │   └── meta.json          # package/activity/depth/来源动作/节点统计
    ├── 001_ef56gh78/
    └── ...
```

### 8.2 `meta.json`

```json
{
  "index": 0,
  "signature": "ab12cd34...",
  "depth": 0,
  "device": "200.47.94.166:5555",
  "package": "com.device.launcheridea",
  "activity": "...",
  "screen": { "width": 3840, "height": 2160 },
  "stats": { "nodes": 51, "clickable": 14, "focusable": 9, "focused": 0 },
  "reached_by": { "type": "dpad_center", "text": "云会议", "bounds": [892,416,1156,680], "from": null },
  "timestamp": "2026-09-02T18:20:00"
}
```

### 8.3 `graph.json`（状态转移图）

```json
{
  "states": [
    { "id": "ab12cd34", "index": 0, "package": "...", "activity": "...", "texts": ["云会议","白板"] }
  ],
  "edges": [
    { "from": "ab12cd34", "to": "ef56gh78", "action": { "type": "dpad_center", "text": "云会议" } }
  ]
}
```

### 8.4 与 token 治理对齐

按项目既有规范（见 `backend/costs/`）：**截图先降到 768 px 宽 JPEG 再入 LLM**，
4K 原图只落盘不上传。原始 1.05 MB PNG → 768 px JPEG 约 50 KB，base64 约 65 KB。

---

## 9. 稳定性与安全

| 风险 | 对策 |
|---|---|
| 遍历点到破坏性操作（删除/支付/卸载） | 动作文本黑名单；`--package` 白名单，越界即停 |
| 页面未稳定就 dump，采到中间态 | `wait_stable()` 双次签名一致 |
| BACK 退不回父状态（跑飞） | `go_back_to()` 重试 K 次；失败则 force-stop + 重启 app 回根 |
| 4K 截图体积大、dump 慢 | 降采样 768 px；dump 超时放宽到 20 s |
| 并发采集竞争 | 沿用 `adb_capture.py` 的 uuid 临时文件命名 |
| 状态爆炸 | 三重熔断 + 签名去重 + 连续无新状态熔断 |
| 设备断连 | 每次 adb 调用超时 + 重试；连续失败熔断并保存已有产出 |

---

## 10. 与现有代码集成

1. **复用**：`scripts/adb_capture.capture_device_ui`（截图 + dump）、
   `scripts/skeleton_parser.parse_ui_tree`（树 → skeleton）、`scripts/theme_extractor`（可选）。
2. **新增**：`scripts/adb_traversal.py`（`AdbBackend` / `Traverser` / `Recorder`）。
3. **接入注册表**：在 `capture/pipeline.py` 增加
   `AdbTraversalPipeline`（`pipeline_id = "adb_traversal"`），加入 `CAPTURE_PIPELINES`。
4. **API 扩展**（后续 PR）：`POST /api/adb/traverse` 启动遍历任务，
   `GET /api/adb/traverse/<run_id>` 查询进度与产出。
5. **stack_registry**：需要遍历能力的栈（Android XML / Compose）把
   `capture_pipeline_id` 指向 `adb_traversal`。

---

## 11. 实施计划与验收

### 里程碑

| 阶段 | 内容 | 状态 |
|---|---|---|
| M0 | 设备连通性 + UI 树基线实测 | ✅ 完成 |
| M1 | worktree 隔离 + 详细设计 | ✅ 完成 |
| M2 | `adb_traversal.py`：单屏采集 + 签名 + 落盘 | ✅ 完成 |
| M3 | dpad 焦点寻路 + touch 双模导航 | ✅ 完成（v2 修复靶向：包含性焦点判定 + 紧祖先约束 + 动作去重） |
| M4 | DFS 遍历 + BACK 回溯 + 熔断 + UTG | ✅ 完成（v2 修复：回溯先查再按 BACK + HOME 兜底 + 悬空边占位） |
| M5 | `AdbTraversalPipeline` 接入 registry | ✅ 完成 |
| M6 | API 端点 + 前端进度展示 | 后续 PR |

> v2 优化轮（2026-09-02）细节见 `adb-traversal-progress-and-reuse.md` 第六节：步均 30.7s → 20.7s，
> 0 悬空边，launcher 不同图标稳定去到不同应用状态，测试 27 passed。

### 验收标准

1. 对 `200.47.94.166:5555` 跑通 **≥ 5 个状态**的采集，无人工干预。
2. 每个状态目录齐备 `screenshot.png` / `screenshot_768.jpg` / `ui_tree.xml` / `skeleton.json` / `meta.json`。
3. `skeleton.json` 能被现有 `skeleton_parser` 正常解析（结构一致）。
4. `graph.json` 中 `edges` 数量 ≥ `states` 数量 - 1（图连通）。
5. 全程无破坏性副作用（无卸载/无支付/无数据清除），设备可回到 launcher。
6. `pyright` 无新增告警，`pytest` 全绿。

---

## 附录 A：常用调试命令

```bash
# 设备状态
adb devices -l
adb -s 200.47.94.166:5555 shell wm size          # 3840x2160
adb -s 200.47.94.166:5555 shell wm density       # 480
adb -s 200.47.94.166:5555 shell dumpsys activity activities | grep mResumedActivity

# 单次采集（注意：输出目录用 Windows 风格路径）
adb -s 200.47.94.166:5555 shell uiautomator dump /sdcard/t.xml
adb -s 200.47.94.166:5555 pull /sdcard/t.xml C:/Code/screenshot-to-code-adb-traversal/e2e_test/t.xml

# D-Pad 导航
adb -s 200.47.94.166:5555 shell input keyevent KEYCODE_DPAD_DOWN
adb -s 200.47.94.166:5555 shell input keyevent KEYCODE_DPAD_CENTER
adb -s 200.47.94.166:5555 shell input keyevent KEYCODE_BACK
```
