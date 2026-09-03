# E2E 验证流程规范（SOP）

> 适用范围：`screenshot-to-code` fork 的「截图 → 多栈代码 → 编译 → 真机运行 → 验证报告」全链路。
> 版本：v1.0 · 生成时间：2026-09-03
> 关联文档：
> - `e2e-artifacts-organization.md` —— `e2e_runs/` 产物目录规范（本文档第五章为其补充）
> - `e2e-verification-projects.md` —— 各栈可用的业界验证工具选型
> - `~/.workbuddy/skills/compose-cli-apk-build/` —— Compose CLI 直编 APK 的可执行 skill

---

## 一、验证分层模型（L0–L4）

参照测试金字塔（Test Pyramid）与 Android CTS 的分层思想，本项目把验证切成 5 层。**层级越低越快、越应该先跑；上层失败不得跳过下层结论**。

| 层 | 名称 | 验证什么 | 手段 | 单栈耗时 | 失败是否阻塞上层 |
|---|---|---|---|---|---|
| **L0** | 生成 | LLM 是否产出结构完整的代码 | vision 调用 + 纯文本调用 | 10–60 s | 是 |
| **L1** | 语法 | 代码能否被解析（AST/Schema 级） | `validate_code.py` | < 1 s | 是 |
| **L2** | 构建 | 能否编译出可安装/可运行产物 | 各栈 CLI 工具链 | 1–15 min | 是（真机层） |
| **L3** | 运行 | 真机/headless 是否渲染出预期 UI | adb / qmlscenegrabber / 浏览器 | 30 s–3 min | 否（可降级 headless） |
| **L4** | 报告 | 结论是否可复核、可归档 | 报告生成器 | < 10 s | — |

### 1.1 判定语义（严格定义，禁止含糊）

| 状态 | 徽章 | 含义 | 举例 |
|---|---|---|---|
| `PASS` | 绿 | 该层预期全部达成，且有产物可复核 | APK 装机 + 进程存活 + 截图已落盘 |
| `FAIL` | 红 | 预期未达成，且根因在**被测代码**里 | Kotlin 编译报语法错 |
| `BLOCKED` | 黄 | 预期未达成，但根因在**环境/工具链**，非被测代码 | Gradle 被杀软拦截死锁 |
| `DEGRADED` | 蓝 | 用降级手段达成了等价结论 | 真机不可用 → headless 渲染通过 |
| `N/A` | 灰 | 该栈不适用此层 | A2UI 无「编译」概念 |

> **铁律**：`BLOCKED` 绝不能写成 `PASS`。历史上曾把「旧版代码真机跑通」当作「新版代码 PASS」，导致报告失真。**真机结论必须绑定到具体产物哈希/时间戳**（见 §4.4）。

---

## 二、各栈流程矩阵

| Stack | L1 语法 | L2 构建 | L3 运行 | 主脚本 |
|---|---|---|---|---|
| `android_compose` | `validate_code.py` | kotlinc → d8 → aapt2 → apksigner | `adb install` + `am start` + `screencap` | `e2e_hosts/android_compose/build_compose_full.py` |
| `android_xml` | `validate_code.py` | aapt2 → d8 → apksigner | 同上 | `e2e_hosts/android_xml/` |
| `qt_qml` | `validate_code.py` | `qmlscenegrabber` 免编译 | `QT_QPA_PLATFORM=offscreen` headless 截图 | `e2e_hosts/qt_qml/` |
| `windows_html` | HTML 解析 | 无（解释执行） | Playwright / 浏览器截图 | `e2e_demo/templates/` |
| `a2ui` | JSONL Schema 校验（含悬空引用） | 无 | `a2ui_runner.html` 浏览器渲染 | `e2e_demo/templates/a2ui/` |
| `windows_wpf` / `winui3` | XAML 解析 | msbuild（可选） | WinAppDriver（P2 待接） | — |

---

## 三、Compose 栈详细流程（最复杂，作为范式）

Gradle 在本机（360 + Defender）**永久死锁**——native agent 被拦截，`--no-daemon` 也无效。因此走 CLI 直编。

### 3.1 工具链版本锁定

| 组件 | 版本 | 路径 |
|---|---|---|
| JDK | 21.0.11 | `C:/Programs/Java/jdk-21.0.11` |
| Android SDK Platform | android-34 | `C:/Programs/Android/Sdk/platforms/android-34` |
| build-tools | 37.0.0 | `C:/Programs/Android/Sdk/build-tools/37.0.0` |
| Kotlin 编译器 | 2.0.21 (`kotlin-compiler-embeddable`) | Gradle 缓存 |
| Compose 编译器插件 | 2.0.21 (`kotlin-compose-compiler-plugin-embeddable`) | Gradle 缓存 |
| minSdk / targetSdk | 24 / 34 | `AndroidManifest.xml` |

### 3.2 五阶段流水线

```
① fetch_compose_deps_v2.py   拉 aar/jar → deps_repo/（含 res/、AndroidManifest、libs/*.jar）
        ↓
② link_resources.py          aapt2 compile 全库 res → link → base_res.apk + 各库 R.java → javac → r_classes/
        ↓
③ build_compose_apk.py       kotlinc（+Compose 插件）→ classes/ → d8 三步法 → classes*.dex
        ↓
④ repack_full.py             base_res.apk + 全部 dex → zipalign → apksigner → *_signed.apk
        ↓
⑤ adb install / am start / screencap
```

一键：

```bash
cd e2e_hosts/android_compose
python build_compose_full.py
```

### 3.3 每阶段检查点（Gate）

| 阶段 | 检查命令 | 通过判据 |
|---|---|---|
| ① 依赖 | `find deps_repo -name classes.jar \| wc -l` | ≥ 37 |
| ② 资源 | `ls -la compose_cli_build/base_res.apk` + `find r_classes -name '*.class' \| wc -l` | arsc ≥ 400 KB；R 类 ≥ 480 |
| ③ 编译 | `find compose_cli_build/classes -name '*.class' \| wc -l` | > 0 且含 `MainActivity.class` |
| ③ dex | `find_missing_classes.py` | **缺失类清单为空** |
| ④ 打包 | `unzip -l *_signed.apk \| grep classes` | `classes.dex` … `classesN.dex` **全部在列** |
| ⑤ 装机 | `adb shell ps -A \| grep <pkg>` | 进程存活 ≥ 10 s，`logcat` 无 `FATAL EXCEPTION` |

> **③ 的 `find_missing_classes.py` 是最有价值的 Gate**：它一次性算出「被引用但未提供」的全部类，避免装机后逐个撞 `NoClassDefFoundError`（历史上撞了 4 轮）。

### 3.4 已知陷阱清单（8 个，全部已修复）

| # | 症状 | 根因 | 修复 |
|---|---|---|---|
| 1 | `force_rmtree` 静默失败 | WorkBuddy 沙箱拦截 `os.remove`/`shutil.rmtree`（回收站不可用 → FAIL_CLOSED） | 改 `os.rename()` 整目录改名到 `_stale_bak/` |
| 2 | `NoClassDefFoundError: org/jetbrains/annotations/NotNull` | kotlinc codegen 阶段需 `org.jetbrains.annotations`（**不是** `androidx.annotation`） | 注入 kotlinc 的 **java 启动 classpath** |
| 3 | `find_in_cache` 找不到 jar | Gradle 缓存 group 目录**保留点号**（`org.jetbrains.kotlin/`），代码却做了 `group.replace(".", os.sep)` | 去掉 replace |
| 4 | `new target SDK 0 doesn't support runtime permissions` | Manifest 缺 `targetSdkVersion` | 加 `<uses-sdk minSdkVersion="24" targetSdkVersion="34"/>` |
| 5 | `ClassNotFoundException: MainActivity`（APK 里明明有类） | d8 把「我们的 .class」与「依赖 jar」混作 program 输入时，因父类 `ComponentActivity` 不在输入里而**静默 tree-shake 丢弃** | **d8 三步法**：依赖单独 dex → 我们的类单独 dex（依赖走 `--classpath`）→ 全 dex 打包 |
| 6 | 仍 `ClassNotFoundException` | `deps_dex/` 产出了 `classes.dex` + `classes2.dex`，合并步骤只喂了第一个，**4.4 MB 依赖类被丢** | 取消合并，走**原生 multidex**（minSdk 24 平台原生支持），全 dex 按 `classes.dex/classes2.dex/...` 打进 APK |
| 7 | `NoClassDefFoundError: kotlin/jvm/internal/Intrinsics` | `kotlin-stdlib` 只进了 kotlinc classpath，**没进 d8 输入**；`coroutines-android` 仅 9 个类，核心 868 类在 `coroutines-core-jvm` | 两者都补进 `extra_jars` |
| 8 | `NoClassDefFoundError: androidx/…/R$…`（31 个 R 类） | aar 的库 R 类需 aapt2 link 后 `javac` 生成，纯 dex 流程不会有 | `link_resources.py`：38 库 res → 44 个 `R.java` → **484 个 R 类** |

### 3.5 装机注意事项

```bash
export ADB=/c/Programs/Android/Sdk/platform-tools/adb.exe
D=200.47.91.1:5555          # TEQU-S2C / Android 12 / 3840×2160

# 必须完整重装：install -r 有时不下发新 dex，导致跑旧逻辑误判
$ADB -s $D uninstall com.e2e.settings
$ADB -s $D install -r "C:/绝对/Windows/路径/xxx_signed.apk"   # Git Bash 下须用 Windows 绝对路径
$ADB -s $D logcat -c
$ADB -s $D shell am start -n com.e2e.settings/.MainActivity
sleep 12                                                       # 36 MB dex 首次 dex2oat 需时间
$ADB -s $D shell "ps -A | grep e2e"
$ADB -s $D logcat -d | grep -E "FATAL EXCEPTION|NoClassDef|ClassNotFound|Caused by"
$ADB -s $D shell screencap -p /sdcard/shot.png
$ADB -s $D pull /sdcard/shot.png "C:/.../screenshots/device_<stack>_<runid>.png"
```

坑位：
- `INSTALL_FAILED_VERSION_DOWNGRADE` → 加 `-d`
- Git Bash 传 `/c/...` 路径给 `adb install` 会失败 → 用 `C:/...`
- 多设备并存时**必须带 `-s <serial>`**，否则装错机

### 3.6 增量缓存机制（保留历史编译结果，重复编译只跑变化的阶段）

**诉求**：每次重编都白扔最贵的 `deps_dex`(~150 s) 与 `link_res`(~90 s)。引入阶段缓存后，**历史编译产物全部保留**，只重跑输入真正变化的阶段。

**实现**：共享模块 `e2e_hosts/android_compose/buildcache.py`。
- **指纹（fingerprint）**：每阶段输入（源文件 / 依赖 jar / 资源目录 / 命令行参数）算 sha256。文件签名用 `(basename, size, mtime_ns)`，**不读内容**——`deps_repo` 有 119 MB / 50 个 jar，读内容算哈希比直接重编还慢。
- **stamp**：`compose_cli_build/.cache/<stage>.stamp`（JSON：指纹 + 时间 + 输出清单）。
- **命中条件**（三者同时满足才复用）：stamp 存在且指纹一致 + 声明输出均存在 + 未被 `--no-cache` / `--force <stage>` 禁用。
- **失效即重建**：任一不满足则重跑该阶段并写新 stamp。

**五个缓存阶段**（对应 §3.2 流水线）：

| 阶段 | stamp | 输入指纹 | 典型耗时 |
|---|---|---|---|
| `kotlinc` | `kotlinc.stamp` | `MainActivity.kt` + Compose 编译器 jar + deps 指纹 | ~60 s |
| `deps_dex` | `deps_dex.stamp` | 全部依赖 jar + `min-api=24` | ~150 s（最贵） |
| `our_dex` | `our_dex.stamp` | `classes/` 目录 + deps 指纹 | ~8 s |
| `link_res` | `link_res.stamp` | `AndroidManifest.xml` + 各库 res + `target-sdk=34` | ~90 s |
| `our_r_dex` | `our_r_dex.stamp` | `r_classes/` + 依赖 jar + `min-api=24` | ~40 s |

**CLI 开关**（各构建脚本均支持，由 `build_compose_full.py` 透传）：

```bash
python build_compose_full.py                 # 默认：命中则跳过，未命中则重建
python build_compose_full.py --seed-cache    # 首次启用：为已存在的历史产物补写 stamp（零漂移），纳管此前手工构建的 deps_dex / r_classes
python build_compose_full.py --no-cache      # 强制全量重建（忽略所有 stamp）
python build_compose_full.py --force deps_dex # 单阶段强刷（其余仍命中）
python build_compose_apk.py --dex-only       # 只跑到 dex（apk.py 专用），完整打包交 repack_full.py，避免冗余 APK
```

**效果（2026-09-03 实测，i5-8250U / 8 GB）**：

| 场景 | 耗时 |
|---|---|
| 首次全量（无缓存） | ~5 min |
| 只改 `MainActivity.kt` | ~70 s |
| `--seed-cache` 纳管后首跑 | ~1.2 s |
| 后续纯命中（无参） | **~1.0 s**（5 阶段全 `[cache HIT]`） |

> **关键区分（易混淆）**：
> - **`compose_cli_build/.cache/`** = 真正的可复用缓存（stamp + 活体 `deps_dex/` `classes/` `base_res.apk` `r_classes/`）。让编译变快的就是它。
> - **`compose_cli_build/_stale_bak/`** = `force_rmtree`/`rename_away` 让位时留下的**旧版 / 调试残骸**（`.bak.<ts>` 目录、`<name>.<ts>` APK 副本、`d8_test_*` 实验品），**不是缓存**、不参与加速，可安全清理（见 §4，由 `organize_host_artifacts.py` 报告体积）。

---

## 四、归档路径要求（强制）

### 4.1 顶层职责划分

| 目录 | 职责 | 是否入库 | 生命周期 |
|---|---|---|---|
| `e2e_runs/<run_id>/` | **一次运行的全部产物**（代码/报告/渲染/输入） | ❌ gitignore | 长期留存，跨 run 对比 |
| `e2e_runs/_templates/` | 可复用模板（含报告模板） | ✅ 入库 | 持久 |
| `e2e_runs/_fixtures/` | 可复用测试输入（人工基准代码） | ✅ 入库 | 持久 |
| `e2e_hosts/<stack>/` | **宿主工程 + 构建工具链**（脚本、依赖仓、构建中间物） | 脚本入库，产物 gitignore | 脚本持久；产物可随时重建 |
| `design-docs/` | 规范与方案文档 | ✅ 入库 | 持久 |
| `outputs/` | 临时对外交付（截图/小报告） | ❌ gitignore | 短期 |

### 4.2 `e2e_runs/<run_id>/` 结构

沿用 `e2e-artifacts-organization.md` §2，不重复。要点：

- `run_id` = `{YYYYMMDD}T{HHMMSS}_{model_slug}`
- 七个固定子目录：`code/` `reports/` `renders/` `inputs/` `subruns/` `misc/` + `manifest.json`
- 报告 JSON 按层编号：`01_validation` `02_unified` `03_deep` `04_compile` `05_generation`
- **冲突绝不静默覆盖**：先用源子目录做命名空间，再退化到 `__N` 后缀

### 4.3 `e2e_hosts/<stack>/` 结构（本次新增规范）

现状问题：`e2e_hosts/android_compose/` 根目录散着 15 个 `_*.log/_*.txt`，`compose_cli_build/` 混着 3 代 APK 与一堆 `.bak/.old`。规范如下：

```
e2e_hosts/<stack>/                       # 当前 android_compose 用 compose_cli_build/ 作为构建根（gitignore）
├── app/                      # 宿主工程源码（入库）
│   └── src/main/{AndroidManifest.xml, res/, java/...}
├── *.py                      # 构建脚本（入库，含 buildcache.py 缓存模块）
├── deps_repo/                # 依赖仓：aar/jar/res/libs（gitignore，可重建）
├── compose_cli_build/        # ← 构建根（gitignore）
│   ├── .cache/               #   阶段缓存 stamp（deps_dex/kotlinc/link_res/our_dex/our_r_dex）
│   ├── classes/              #   ③ kotlinc 输出（业务 .class）
│   ├── deps_dex/             #   ③ d8 打依赖 → classes.dex（最贵 ~150s）
│   ├── our_dex/              #   ③ 业务 dex
│   ├── r_classes/            #   ② aapt2 link + javac 生成的 R.class
│   ├── base_res.apk          #   ② 库资源包
│   ├── e2e_compose_full_signed.apk   # ④ 最终产物（仅保留当前代）
│   └── _stale_bak/           #   force_rmtree/rename_away 让位时旧版（非缓存，可清）
├── logs/                     # ← 所有 _*.log / _*.txt 收敛到此（gitignore）
│   └── <YYYYMMDDTHHMMSS>_<phase>.log
└── screenshots/              # 真机/渲染截图（gitignore，但会被报告引用）
    └── device_<stack>_<runid>.png
```

**强制命名规则**：

| 类型 | 规则 | 例 |
|---|---|---|
| APK | `<stack>_signed.apk`，**不加 debug/md/full 等演进后缀** | `android_compose_signed.apk` |
| 旧代 APK | 归档到 `compose_cli_build/_stale_bak/<原名>.<epoch_ms>` | `android_compose_signed.apk.1788411849189` |
| 日志 | `logs/<时间戳>_<阶段>.log` | `logs/20260903T131500_link_res.log` |
| 截图 | `screenshots/device_<stack>_<runid>.png` | `screenshots/device_android_compose_20260903T130500.png` |
| 诊断中间物 | `logs/` 下，前缀 `_diag_` | `logs/_diag_missing_classes.txt` |

> **反面教材（本次实际踩过）**：`e2e_compose_debug_signed.apk` → `e2e_compose_md_signed.apk` → `e2e_compose_full_signed.apk` 三代并存，无法从文件名判断哪个是当前有效产物，只能靠 mtime 猜。**演进信息属于日志，不属于文件名。**

### 4.4 产物可追溯性（报告结论的硬要求）

任何 `PASS` 结论必须能回溯到具体产物。报告中每条真机结论**必须**带：

```
产物：compose_cli_build/e2e_compose_full_signed.apk
大小：38.5 MB
SHA256：<前 12 位>
构建时间：2026-09-03T13:05:00+08:00
设备：200.47.91.1:5555 / TEQU-S2C / Android 12 / 3840×2160
截图：screenshots/device_android_compose_20260903T130500.png
```

取哈希：

```bash
sha256sum compose_cli_build/e2e_compose_full_signed.apk | cut -c1-12
```

> 这条规则直接来自本次事故：报告曾标「Compose 真机 PASS」，实际跑的是**上一代 APK**，新代码根本没装上。加哈希后此类失真不可能再发生。

### 4.5 `.gitignore` 补充

```gitignore
# E2E 运行产物
e2e_runs/
!e2e_runs/_templates/
!e2e_runs/_fixtures/

# 宿主工程构建产物与依赖仓
# e2e_hosts/*/build/  (已统一为 compose_cli_build/，保留注释以防旧残留)
e2e_hosts/*/deps_repo/
e2e_hosts/*/deps_repo.old*/
e2e_hosts/*/logs/
e2e_hosts/*/screenshots/
e2e_hosts/*/compose_cli_build/     # 旧路径，迁移期保留
e2e_hosts/*/_stale_bak/
e2e_hosts/*/__pycache__/

# 历史遗留
e2e_demo/run_*/
e2e_demo/screenshots/
outputs/
ocr_logs2/
.bak_e2e_run_*/
```

### 4.6 清理命令（编译产物，可直接执行）

```bash
# 单栈清理构建产物（保留 deps_repo，避免重新下载 50 个 jar）
cd e2e_hosts/android_compose
python -c "import os,time; [os.rename(p, p+'.stale.%d'%int(time.time()*1000)) for p in ['build'] if os.path.exists(p)]"

# 全量清理（含依赖仓，下次要重新拉依赖）
rm -rf e2e_hosts/*/build e2e_hosts/*/deps_repo e2e_hosts/*/logs e2e_hosts/*/__pycache__
rm -rf e2e_hosts/*/_stale_bak e2e_hosts/*/deps_repo.old*

# 清理 run 产物（保留模板与 fixtures）
find e2e_runs -maxdepth 1 -type d -name '20*' -exec rm -rf {} +
```

> 沙箱环境下 `rm -rf` 可能被安全 shim 拦截，此时改用 `os.rename` 归档法（见 §3.4 陷阱 1）。

---

## 五、报告模板规范

模板位置：`e2e_runs/_templates/report/`

| 文件 | 作用 |
|---|---|
| `report_template.html` | 骨架 + CSS（暗色 GitHub 风），含 `{{...}}` 占位符 |
| `build_report.py` | 数据 → 自包含单文件 HTML（图片 base64 内嵌） |
| `report_data.schema.json` | 数据契约（JSON Schema） |
| `example_data.json` | 可直接跑通的示例数据 |

> **`_templates/` 两层含义（勿混）**：`_templates/report/` 放**报告生成器代码**（`build_report.py` 及一次性生成脚本 `_gen_*.py`/`_assemble.py`，入库、可复用）；`_templates/<stack>/`（待建）放各栈**基准代码夹具**（如 `settings_android_compose.kt`）。两者都是「可复用资产」，区别于一次性的 `<run_id>/` 产物。合并类报告（如 `merged_report.html`）统一放 `e2e_runs/_consolidated/`，不散落根目录。

### 5.1 报告必备章节（缺一不可）

| # | 章节 | 内容 | 为什么必须 |
|---|---|---|---|
| 1 | 指标仪表盘 | 各层通过数 / 栈数 / Token / 成本 | 3 秒获知全局 |
| 2 | 验证矩阵 | **层 · 项目 · 预期 · 操作 · 结果 · 状态** 六列 | 可复核的核心；「预期/操作」缺失则报告不可验证 |
| 3 | 截图对比 | 原始 vs 各栈产出，并排 | 视觉证据 |
| 4 | 根因分析 | 阻塞项的层级 · 症状 · 状态 · 修复 | 区分 FAIL / BLOCKED |
| 5 | 产物清单 | 路径 + 大小 + 哈希 + 时间戳 | 可追溯性（§4.4） |
| 6 | 业界参考 | 采用的工具/方法及依据 | 方法论可信度 |
| 7 | 下一步 | P0–P3 待办 | 闭环 |

### 5.2 硬性约束

1. **自包含单文件**：所有图片必须 base64 内嵌。WorkBuddy webview 与浏览器 `file://` 都无法可靠加载外部相对路径图片——历史上报告在 webview 里图全裂。
2. **状态徽章语义严格**：只用 §1.1 的 5 种，不自造。
3. **「预期 / 操作 / 结果」三列不可省**：只写「结果 PASS」的报告等于没验证。
4. **时间戳带时区**：`2026-09-03T13:05:00+08:00`。
5. **降级要显式标注**：headless 代替真机时标 `DEGRADED` 并写明代替关系。

### 5.3 生成命令

```bash
cd e2e_runs/_templates/report
python build_report.py --data ../../<run_id>/report_data.json \
                       --out ../../<run_id>/reports/final_report.html
```

---

## 六、执行检查清单

开跑前：

- [ ] 确认 `run_id` 已生成，七个子目录已建
- [ ] 输入截图已落 `inputs/`
- [ ] 模型与 Key 已确认可用（避免半途 401）

每层跑完：

- [ ] L1：`01_validation.json` 已写，各栈 PASS/FAIL 明确
- [ ] L2：`find_missing_classes.py` 缺失清单为空
- [ ] L2：APK 内 `classes*.dex` 全部在列（不止 `classes.dex`）
- [ ] L3：`uninstall` + `install` 完整重装（非增量）
- [ ] L3：进程存活 ≥ 10 s，logcat 无 `FATAL`
- [ ] L3：截图已 `pull` 到 `screenshots/`，命名合规
- [ ] L4：产物哈希已写入报告
- [ ] L4：`BLOCKED` 项未被误标 `PASS`

收尾：

- [ ] `manifest.json` 已更新
- [ ] 构建中间物已归档/清理
- [ ] 日志已收敛到 `logs/`
- [ ] 经验已写入 `.workbuddy/memory/` 或 skill

---

## 七、待办

| 优先级 | 动作 | 状态 |
|---|---|---|
| **P0** | 构建根统一为 `compose_cli_build/`（已落地，`build/` 死目录已删；§4.3 已更正） | ✅ |
| **P0** | 各脚本路径常量改为读统一 `paths.py` | ⬜ |
| **P1** | `build_report.py` 接入 `manifest.json` 自动取产物哈希 | ⬜ |
| **P1** | 补 `.gitignore`（§4.5，已落地） | ✅ |
| **P1** | 合并报告归位 `e2e_runs/_consolidated/`、生成脚本归 `_templates/report/`（已落地 2026-09-03） | ✅ |
| **P2** | 其余 4 栈按本 SOP 补齐 L2/L3 脚本 | ⬜ |
| **P2** | 接 Paparazzi / Compose Driver 做像素回归（见 `reuse-reference-report.md`） | ⬜ |
