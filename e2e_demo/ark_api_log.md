# Ark API 调用日志

> 持久化记录所有 Ark API 调用，含 token 消耗和结果。

---

## 2026-09-01 调用记录

### 会话概览
- **API Key**: `REDACTED`（⚠️ 已暴露，需轮换）
- **Base URL**: `https://ark.cn-beijing.volces.com/api/v3`
- **唯一可用模型**: `doubao-seed-2-1-turbo-260628`（endpoint ID）
- **账户状态**: `AccountOverdueError`（欠费，所有 API 调用被拒）

### 模型可用性测试 (test_models.py, ~17:02)

测试 15 个已开通模型，仅 1 个 API 可用：

| # | 模型名 | model_id (API) | 状态 | HTTP | 耗时 | token_in | token_out | 备注 |
|---|--------|----------------|------|------|------|----------|-----------|------|
| 1 | Doubao-Seed-2.1-turbo | doubao-seed-2-1-turbo-260628 | ✅ OK | 200 | 4.0s | 48 | 96 | 唯一可用模型，视觉多模态 |
| 2 | GLM-5.2 | glm-5.2 | ❌ 404 | 404 | - | 0 | 0 | InvalidEndpointOrModel.NotFound |
| 3 | DeepSeek-V4-pro | deepseek-v4-pro | ❌ 404 | 404 | - | 0 | 0 | endpoint 未创建 |
| 4 | Doubao-Seed-1.8 | doubao-seed-1-8-250915 | ❌ 404 | 404 | - | 0 | 0 | endpoint 未创建 |
| 5 | GLM-4.7 | glm-4-7 | ❌ 404 | 404 | - | 0 | 0 | endpoint 未创建 |
| 6 | DeepSeek-V3.2 | deepseek-v3-2-250628 | ❌ 404 | 404 | - | 0 | 0 | endpoint 未创建 |
| 7 | Doubao-Seed-Code | doubao-seed-code-250915 | ❌ 404 | 404 | - | 0 | 0 | endpoint 未创建 |
| 8 | Doubao-Seed-1.6-vision | doubao-seed-1-6-vision-250815 | ❌ 404 | 404 | - | 0 | 0 | endpoint 未创建 |
| 9 | Doubao-Seed-1.6-flash | doubao-seed-1-6-flash-250828 | ❌ 404 | 404 | - | 0 | 0 | endpoint 未创建 |
| 10 | Doubao-Seed-1.6 | doubao-seed-1-6-250815 | ❌ 404 | 404 | - | 0 | 0 | endpoint 未创建 |
| 11 | Doubao-1.5-vision-lite | doubao-1-5-vision-lite-250328 | ❌ 404 | 404 | - | 0 | 0 | endpoint 未创建 |
| 12 | Doubao-1.5-vision-pro-32k | doubao-1-5-vision-pro-32k-250328 | ❌ 404 | 404 | - | 0 | 0 | endpoint 未创建 |
| 13 | Doubao-1.5-pro-32k | doubao-1-5-pro-32k-250328 | ❌ 404 | 404 | - | 0 | 0 | endpoint 未创建 |
| 14 | Doubao-pro-32k | doubao-pro-32k-250328 | ❌ 404 | 404 | - | 0 | 0 | endpoint 未创建 |
| 15 | Doubao-lite-32k | doubao-lite-32k-250328 | ❌ 404 | 404 | - | 0 | 0 | endpoint 未创建 |

**小计**: 15 次调用，1 成功，14 个 404（不消耗 token）。消耗 48+96=144 tokens。

### 早期测试 (test_ark.py, ~17:02)

| # | 模型 | 认证方式 | 状态 | HTTP | token 消耗 | 错误码 |
|---|------|----------|------|------|-----------|--------|
| 1 | doubao-seed-2-1-turbo-260628 | Bearer | ❌ | 403 | 0 | AccountOverdueError |
| 2 | doubao-seed-evolving | Bearer | ❌ | 403 | 0 | AccountOverdueError |
| 3 | doubao-seed-2-1-turbo-260628 | x-api-key | ❌ | 401 | 0 | AuthenticationError |

**小计**: 3 次调用，0 成功。不消耗 token。

### 5 栈生成尝试 (generate_5stacks.py)

| # | 时间 | 步骤 | 图片大小 | 状态 | 错误 | token 消耗 |
|---|------|------|----------|------|------|-----------|
| 1 | ~17:08 | Step 1: vision 分析 | 872KB base64 (PNG 1024×576) | ❌ | ReadTimeout (120s) | 0 |
| 2 | ~17:18 | Step 1: vision 分析 | 65KB base64 (JPEG 768×432) | ❌ | 403 AccountOverdueError | 0 |

**小计**: 2 次调用，0 成功。不消耗 token。

### Vision 测试 (test_vision.py, ~17:18)

| # | 测试内容 | 图片 | 状态 | HTTP | token 消耗 |
|---|---------|------|------|------|-----------|
| 1 | 纯文本 "Say OK" | 无 | ❌ | 403 | 0 |
| 2 | Vision (65KB JPEG) | source_screenshot_768.jpg | ❌ | 403 | 0 |
| 3 | Vision (1×1 pixel PNG) | 内联 tiny base64 | ❌ | 403 | 0 |

**小计**: 3 次调用，0 成功。全部 AccountOverdueError。

### 快速验证 (quick_test.py, ~17:19)

| # | 内容 | 状态 | HTTP | token 消耗 |
|---|------|------|------|-----------|
| 1 | "OK" max_tokens=5 | ❌ | 403 | 0 |

**小计**: 1 次调用，0 成功。

---

## 汇总

| 指标 | 值 |
|------|-----|
| 总调用次数 | 24 |
| 成功调用 | 1 |
| 失败调用 | 23 |
| 总消耗 token | 144（48 input + 96 output） |
| 预估费用 | ¥0.000432（几乎可忽略） |
| 唯一可用模型 | doubao-seed-2-1-turbo-260628 |
| 失败原因分布 | 14×404 endpoint未创建, 8×403欠费, 1×timeout |

### Token 预算规划（待充值后执行）

| 步骤 | 模型 | 预估 input | 预估 output | 预估费用 |
|------|------|-----------|-------------|---------|
| Step 1: vision 分析截图 | doubao-seed-2.1-turbo | ~2,000 | ~3,000 | ¥0.051 |
| Step 2: 生成 Kotlin Compose | doubao-seed-2.1-turbo | ~1,000 | ~5,000 | ¥0.105 |
| Step 3: 生成 Android XML | doubao-seed-2.1-turbo | ~1,000 | ~4,000 | ¥0.090 |
| Step 4: 生成 Qt QML | doubao-seed-2.1-turbo | ~1,000 | ~3,000 | ¥0.075 |
| Step 5: 生成 HTML | doubao-seed-2.1-turbo | ~1,000 | ~4,000 | ¥0.090 |
| Step 6: 生成 A2UI JSONL | doubao-seed-2.1-turbo | ~1,000 | ~2,000 | ¥0.060 |
| **合计** | | **~6,000** | **~21,000** | **~¥0.471** |
| 剩余额度 | | | | **268,378 tokens** |
| 调用后剩余 | | | | **~241,378 tokens** |

### 关键教训
1. **免费额度 ≠ 可用余额**：火山引擎账户有欠费时，即使免费额度未用完，API 调用也会被 403 拒绝
2. **控制台数据有延迟**：控制台显示 268K 剩余，实际 API 已不可用
3. **endpoint ID 命名规则**：模型显示名 ≠ API model 参数。如 `Doubao-Seed-2.1-turbo` → `doubao-seed-2-1-turbo-260628`
4. **14 个已开通模型无 endpoint**：需要在控制台为每个模型手动创建推理接入点
5. **SDK silent crash 已规避**：使用 raw httpx 而非 OpenAI SDK，避免大 payload 导致的进程崩溃
6. **doubao-seed-1-6-vision-250815 已 EOM**：2026-07-10 停止新购，无法新建接入点，API 返回 404。EOS 2026-09-21 正式下线。官方建议迁移到 `doubao-seed-2-0-lite-260428`
7. **/responses vs /chat/completions**：doubao-seed-1-6-vision 文档示例用 `/responses` 端点，但 EOM 后两个端点都返回 404
8. **doubao-seed-2-1-turbo-260628 支持视觉多模态**：通过 `/chat/completions` + `image_url` content type 成功调用，200 OK
9. **max_tokens 8000 不够生成 5 栈**：26206 output tokens 消耗殆尽仍只生成 3 栈完整 + HTML 截断 + A2UI 缺失。需拆分调用

---

## 新 Key 调用记录 (REDACTED)

### 模型可用性测试 (test_vision_model.py, ~18:10)

| # | 模型 | 端点 | 状态 | HTTP | token 消耗 |
|---|------|------|------|------|-----------|
| 1 | doubao-seed-1-6-vision-250815 | /chat/completions | ❌ | 404 | 0 |
| 2 | doubao-seed-1-6-vision-250815 | /responses | ❌ | 404 | 0 |
| 3 | doubao-seed-1-6-vision-250815 + image | /responses | ❌ | 404 | 0 |
| 4 | doubao-seed-2-1-turbo-260628 | /chat/completions | ✅ | 200 | 48+96=144 |
| 5 | doubao-seed-2-1-turbo-260628 | /responses | ✅ | 200 | 48+66=114 |
| 6 | doubao-seed-2-1-turbo-260628 + image | /chat/completions | ✅ | 200 | 1348+652=2000 |

### Seed 系列模型全量测试 (~18:12)

| # | 模型 | 状态 | 错误码 |
|---|------|------|--------|
| 1-9 | doubao-seed-1-6-* 系列 | ❌ 全部 404 | InvalidEndpointOrModel.NotFound |
| 10-16 | doubao-seed-2-0-* 系列 | ❌ 全部 404 | ModelNotOpen（模型未开通） |
| 17 | doubao-seed-2-1-turbo-260628 | ✅ 200 | - |
| 18 | doubao-seed-evolving | ✅ 200 | （用户禁止使用） |
| 19-20 | doubao-seed-character-* | ✅ 200 | - |

### 5 栈生成 (generate_5stacks_combined.py, ~18:25-18:31)

| # | 步骤 | 模型 | 状态 | 耗时 | token_in | token_out | 费用 |
|---|------|------|------|------|----------|-----------|------|
| 25 | 合并 5 栈生成 | seed-2-1-turbo | ✅ | 246s | 900 | 26206 | ¥0.3958 |

**结果**: KOTLIN ✅(16410 chars) · XML ✅(16533) · QML ✅(8414) · HTML ✅(1532, 截断) · A2UI ❌(缺失)

### 补充生成 A2UI + HTML (~18:55-19:10)

| # | 步骤 | 模型 | 状态 | 耗时 | token_in | token_out | 费用 |
|---|------|------|------|------|----------|-----------|------|
| 26 | A2UI JSONL | seed-2-1-turbo | ✅ | ~180s | 792 | 18467 | ¥0.2774 |
| 27 | HTML 完整版 | seed-2-1-turbo | ✅ | ~120s | 814 | 11295 | ¥0.1721 |

**结果**: A2UI ✅(5930 chars) · HTML ✅(12357 chars)

### Validate Code 验证 (~19:15)

| 栈 | 文件 | 验证状态 | Errors | Warnings |
|----|------|---------|--------|----------|
| Kotlin Compose | llm_android_compose.kt | ✅ PASS | 0 | 0 |
| Android XML | llm_android_xml.xml | ✅ PASS | 0 | 0 |
| Qt QML | llm_qt_qml.qml | ✅ PASS | 0 | 0 |
| Windows HTML | llm_windows_html.html | ✅ PASS | 0 | 0 |
| A2UI JSONL | llm_a2ui.jsonl | ✅ PASS | 0 | 0 |

**Overall: 5/5 ALL PASS**

---

## 最终汇总（新 Key）

| 指标 | 值 |
|------|-----|
| 新 Key 总调用次数 | 27 |
| 成功调用 | 8 |
| 失败调用 | 19 |
| 新 Key 总消耗 token | 58,618 (2506 input + 55,968 output + 144 test) |
| 新 Key 预估费用 | ¥0.8466 |
| 5 栈生成状态 | 5/5 完成 |
| 5 栈验证状态 | 5/5 PASS |
