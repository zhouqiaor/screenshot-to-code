# ScreenCoder / fork / Design2Code / UI2CodeN 技术方案对比

> 目的：横向对比「截图转代码」4 个代表性方案的技术路径，识别 fork 的可借鉴与可补齐点。
> 评价时间：2026-09-02

---

## 一、4 个方案全景对比

| 维度 | **fork** (screenshot-to-code) | **ScreenCoder** (CUHK MMLab) | **Design2Code** (UCLA) | **UI2CodeN** (ZhipuAI/zai-org) |
|---|---|---|---|---|
| **核心架构** | 1 次 vision 描述 + N 次文本生成各栈 | 3 阶段：Grounding → Planning → Generation | 5 种 prompting 策略对比研究 | 交互式范式 + 3 阶段训练（持续预训练 + SFT + RL） |
| **模型形态** | 调商业 VLM（GPT-4o/Claude/Doubao） | 调商业 VLM（默认 Doubao） | 调商业 VLM（GPT-4V） | 自训开源 VLM（UI2CodeN） |
| **输出栈** | **6 栈**：HTML/Compose/QML/XML/WPF/A2UI | 仅 HTML | HTML（CSS） | HTML/CSS + UI 润色 + UI 编辑 |
| **图像还原** | LLM 描述生成（无原图裁剪） | **CIoU+匈牙利匹配+原图裁剪回填**（创新） | LLM 描述生成 | LLM 描述 + 渲染反馈迭代 |
| **基准测试** | 内部对比 | ScreenBench（1000 张真实网页） | Design2Code（首个真实网页基准） | Design2Code + Web2Code + Flame-React-Eval |
| **Web UI** | ✅（React/Vite，7001+5173） | ❌（CLI only，HF 有 Gradio Demo） | ❌（脚本） | ❌（训练框架 + 推理脚本） |
| **可训练** | ❌（仅调用） | ⚠️（含 post-training/LLaMA-Factory） | ❌（仅调用） | ✅（开源 VLM + 完整训练代码） |
| **最新版本** | abi/main, 持续 | 2025-10-22 | 2024 论文 | **2026 最新 SOTA**（超越 Claude-4-Sonnet/GPT-5） |
| **评估指标** | 内部 | Block-Match + CLIP score | Block-Match + CLIP + 人工评估 | CLIP + DOM match + GPT-4 judge |

---

## 二、架构与流水线对比

### 2.1 fork（screenshot-to-code）流水线

```
截图 → [1] 1 次 vision 描述 (生成 layout_description.md)
        ↓
       [2] 按栈并发 N 次纯文本生成
            ├─ HTML 栈: model + layout_description → html_text
            ├─ Compose 栈: model + layout_description → compose_text
            ├─ QML 栈: ...
            └─ ... (6 栈)
        ↓
       [3] 6 栈 validate_code.py 验证
        ↓
       [4] 前端展示 6 栈结果（WebSocket 流式）
```

**优点**：
- 单源描述（layout_description）保证 6 栈一致性
- 纯文本生成快（无 vision 重复调用）
- 6 栈覆盖最广（HTML/Compose/QML/XML/WPF/A2UI）

**缺点**：
- 图像靠 LLM 描述生成，无法像素级还原
- 单次 vision 描述可能漏掉小元素
- 依赖压缩 prompt 影响大图细节

### 2.2 ScreenCoder 流水线

```
截图 → [1] Grounding Agent (block_parsor.py)
            ↓ VLM 检测 4 区域边界框 + 标签
        ↓
       [2] Planning Agent (构建 layout tree)
            ↓ 启发式空间规则 → 树形结构
        ↓
       [3] Generation Agent (html_generator.py)
            ↓ 对每个 leaf node 并发调 LLM 生成
            ↓ 产出含 bg-gray-400 占位符的 HTML
        ↓
       [4] Image Replacement Pipeline (image_*)
            ├─ Playwright 检测占位符盒
            ├─ UIED(CNN+OCR) 检测原图图像组件
            ├─ mapping.py: CIoU + 匈牙利算法 1:1 匹配
            └─ image_replacer.py: crop 原图 → 替换占位符 → 写 <img>
        ↓
       [5] 最终 HTML（含真实裁剪的图像）
```

**优点**：
- 分阶段解耦，每阶段可独立优化/替换
- 图像回填 Pipeline 是 LLM 难生成位图的创新解法
- 三层 VLM 调用（区域+规划+生成）逐步细化

**缺点**：
- 依赖 UIED（TensorFlow + PaddlePaddle），部署重
- 阶段①区域精度直接决定最终质量（本测试 4 个粗框 = 50% 内容）
- 多线程 Ark client 调用非线程安全（已修）
- 仅输出 HTML（其他栈需自己移植）

### 2.3 Design2Code 流水线（学术方法论）

```
截图 → [1] Direct prompting（单次 prompt 直接生成）
        ↓
       [2] Self-revision（生成+自己改）
        ↓
       [3] Textual description（先用文本描述布局，再依描述生成代码）
        ↓
       [4] Visual refinement（生成代码→渲染→截图比对→修改）
        ↓
       [5] Bootstrapping（迭代多轮视觉反馈，每轮 prompt 携带前轮结果）
        ↓
       [评估] Block-Match + CLIP score
```

**核心贡献**：系统比较 5 种 prompting 策略，证明「**Visual refinement**（视觉反馈迭代）」效果最好，CLIP 得分比直接生成高 ~10 分。

### 2.4 UI2CodeN 流水线（最新 SOTA）

```
截图 → [1] UI-to-code 生成（单次 prompt）
        ↓
       [2] UI 润色（UI polishing，迭代 4 轮视觉反馈）
            ↓ 目标图 + 当前代码 + 渲染输出 → 修正代码
        ↓
       [3] UI 编辑（UI editing，支持局部修改指令）
        ↓
       [训练]
        ├─ 持续预训练（CPT）：在噪声真实网页 HTML 数据上预训练
        ├─ 监督微调（SFT）：在合成干净数据上微调
        └─ 强化学习（RL）：用验证器 reward，不依赖配对数据
```

**核心创新**：
- **交互式范式**：把单次生成变成迭代过程，支持 test-time scaling（4 轮提升 ~10 分）
- **RL reward 设计**：不用配对数据也能训练，扩展到无限真实网页

---

## 三、关键技术模块对比

### 3.1 区域检测 / 布局分解

| 方案 | 方法 | 输出 | 精度评估 |
|---|---|---|---|
| **fork** | ❌ 无显式区域检测 | layout_description（纯文本） | 依赖 VLM 单次描述 |
| **ScreenCoder** | ✅ VLM 检测 4 区域（sidebar/header/nav/main） | bbox + label | 实测：粗，遗漏状态栏/背景 |
| **Design2Code** | 隐式（直接生成） | HTML | N/A |
| **UI2CodeN** | 隐式（直接生成） | HTML | N/A |

**结论**：ScreenCoder 是唯一显式做区域检测的方案，但实测精度不够。需要更细粒度（如 8-12 区域）或自适应分辨率。

### 3.2 图像还原 / 视觉一致性

| 方案 | 方法 | 优势 | 局限 |
|---|---|---|---|
| **fork** | LLM 描述生成（SVG/emoji） | 跨栈一致 | 无法像素级 |
| **ScreenCoder** | **CIoU+匈牙利+原图裁剪回填** | **像素级一致** | 仅适用于含图片的页面 |
| **Design2Code** | LLM 描述生成 | 学术可控 | 同 fork |
| **UI2CodeN** | LLM 描述 + 渲染迭代修正 | 通过多轮逼近 | 计算成本高 |

**ScreenCoder 的 CIoU + 匈牙利 Pipeline 详解**（`mapping.py`）：
1. **Global transform 粗对齐**：用 UIED/img_shape 和原图尺寸计算 scale_x/y；用最近邻匹配中心点估算 dx/dy（中位数）
2. **Local transform 精对齐**：对每个 region 单独重算 scale/dx/dy
3. **CIoU 评分**：IoU + 中心距离惩罚 + 长宽比惩罚（v3 算法）
4. **匈牙利算法**：`scipy.optimize.linear_sum_assignment` 解最优 1:1
5. **Crop & Replace**：从原图裁剪 → BeautifulSoup 替换占位符

**移植到 fork 的可行性**：
- ✅ `mapping.py` 独立可用（仅依赖 numpy/cv2/sklearn/scipy），不依赖 TensorFlow/Paddle
- ❌ 仍依赖 UIED（CNN+OCR）的图像组件检测（重依赖）
- 💡 **简化路径**：用更轻量目标检测（如 YOLOv8）替代 UIED，或直接用 Playwright 检测占位符 ↔ 原图色块匹配

### 3.3 多栈支持

| 方案 | 栈数 | 多栈策略 | 质量保证 |
|---|---|---|---|
| **fork** | **6 栈** | 单源 layout_description + 每栈独立 prompt | validate_code.py 验证 |
| **ScreenCoder** | 1 栈（HTML） | N/A | N/A |
| **Design2Code** | 1 栈（HTML） | N/A | N/A |
| **UI2CodeN** | 1 栈 + UI 润色/编辑 | 同一 VLM 输出 | N/A |

**结论**：fork 在多栈覆盖上**绝对领先**。如果 fork 借鉴 ScreenCoder 的图像回填 + UI2CodeN 的视觉反馈迭代，可成为最强混合方案。

### 3.4 评估指标

| 方案 | 指标 | 自动化 |
|---|---|---|
| **fork** | 内部人工对比 | ❌ |
| **ScreenCoder** | Block-Match（DOM 结构）+ CLIP score（视觉） | ✅ |
| **Design2Code** | Block-Match + CLIP + 人工评估 | ✅ |
| **UI2CodeN** | CLIP + DOM match + GPT-4 judge | ✅ |

**fork 缺失**：无自动化评估指标，每次靠肉眼对比。

---

## 四、可借鉴与可补齐

### 4.1 fork 可立即借鉴（低成本高收益）

1. **借鉴 ScreenCoder 的 Block-Match 评估指标**
   - 用 BeautifulSoup 解析 fork 生成的 HTML，提取 div 树结构
   - 跟原图 DOM（用 VLM 描述）做树形匹配，量化相似度
   - **工作量**：1 人天

2. **借鉴 UI2CodeN 的视觉反馈迭代**
   - 当前 fork 一次生成就结束；可加「渲染 → 截图 → VLM 评分 → 二次生成」闭环
   - 不重训模型，纯推理侧多 1 次调用即可
   - **工作量**：3 人天（需引入 Playwright）

3. **借鉴 Design2Code 的多策略对比框架**
   - 在 fork 内部实现 4 种策略（direct / self-revision / textual-description / visual-refinement）的对比报告
   - 帮助用户选择最适合的策略
   - **工作量**：5 人天

### 4.2 fork 可中长期补齐（高成本但高价值）

1. **移植 ScreenCoder 图像回填 Pipeline**
   - 步骤：① 解析 fork 生成的 HTML 找图像占位符 ② 用 YOLOv8/UIED 检测原图图像组件 ③ CIoU+匈牙利匹配 ④ 裁剪回填
   - 价值：让 fork 在含真实位图的页面（电商/新闻/相册）像素级还原
   - **工作量**：2 人周（核心 1 周，集成 1 周）

2. **引入区域检测（参考 ScreenCoder）**
   - 在 fork 的 stage 1（vision 描述）前加一个 Grounding Agent
   - VLM 检测 8-12 区域，每区域独立生成，最后拼装
   - 价值：解决 fork 单次 vision 漏掉小元素的问题
   - **工作量**：2 人周（需调 prompt + 测试）

3. **自训 UI2CodeN 风格的 VLM**
   - 在 fork 的训练数据上 CPT + SFT + RL
   - 价值：摆脱对商业 VLM 的依赖（成本/可控性）
   - **工作量**：1 人季度（需 GPU 资源）

### 4.3 fork 的核心优势（保持）

1. **6 栈覆盖最广**：HTML/Compose/QML/XML/WPF/A2UI → 跨平台设计稿落地
2. **Web UI + 实时流式**：用户可交互地看到生成过程
3. **国产模型深度集成**：doubao/qwen/deepseek 都支持
4. **ADB 截屏 pipeline**：从 Android 设备直接截图生成
5. **预算治理**：token 预算 + 模型路由 + 压缩 + metrics

---

## 五、移植路线图（建议）

### 优先级 P0（立即 1 周内）
1. **Block-Match 评估指标**：量化 fork 6 栈生成质量
2. **CIoU+匈牙利匹配工具**（独立脚本）：为图像回填做准备
3. **HTML 栈视觉反馈迭代**：单栈先验证效果

### 优先级 P1（1 月内）
4. **图像回填 Pipeline 移植**：YOLOv8 替代 UIED，降低依赖
5. **区域检测增强**：在 fork stage 1 前加 Grounding Agent
6. **多策略对比报告**：把 Design2Code 5 策略整合进 fork Web UI

### 优先级 P2（3 月内）
7. **自训 VLM**：在 fork 训练数据上做 CPT + SFT + RL
8. **测试基线化**：用 Design2Code benchmark 评估 fork 质量
9. **多模态扩展**：支持 Figma/Sketch 输入

---

## 六、风险与权衡

| 风险 | 描述 | 缓解 |
|---|---|---|
| 图像回填仅适用于含位图页面 | 矢量图标页面无意义 | 双模式：自动判断是否启用 |
| 区域检测依赖 VLM 精度 | ScreenCoder 实测 4 粗框 | 多区域 + 自适应 |
| 视觉反馈迭代增加 token 成本 | 4 轮 = 4 倍费用 | 限轮数 + 早停条件 |
| 自训 VLM 需大量 GPU | 训练资源重 | 先用商业 VLM 验证方案，再决定是否自训 |

---

## 七、总结：fork 在 4 个方案中的定位

```
                 多栈覆盖
                  ↑
                  |  | fork ★
                  |  |
                  |  |
                  |  |____ UI2CodeN
                  |  |
                  |  |________ ScreenCoder
                  |  |____________ Design2Code
                  |________________→ 视觉还原能力
```

**fork 的护城河**：多栈覆盖 + Web UI + 国产模型 + ADB 集成
**fork 的短板**：图像还原能力弱（无 CIoU+原图裁剪）+ 单次生成无反馈迭代

**最佳演进路径**：**fork + ScreenCoder 图像回填 + UI2CodeN 视觉反馈迭代** = 三方优势合一的最强混合方案。