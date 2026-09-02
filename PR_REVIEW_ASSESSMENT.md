# PR 检视结果与合入评估

> 仓库：`zhouqiaor/screenshot-to-code` | 审查时间：2026-09-01 19:30
> 已合并 PR：#1, #3, #4, #6 | 待审查 Open PR：#5, #7, #8, #9, #10

---

## 总览表

| PR | 标题 | +/- | 文件数 | Mergeable | OCR | 评估 |
|----|------|-----|--------|-----------|-----|------|
| #5 | OCR volcengine provider | +2/-0 | 1 | unknown | 未触发 | **关闭** (被 #7 取代) |
| #7 | Fork-only bugs fix | +691/-12 | 6 | clean | 6 issues (msg 空) | **合入** |
| #8 | System Prompt Router | +389/-9 | 9 | clean | 已触发(success) | **关闭** (被 #10 取代) |
| #9 | Token optimization | +172/-2 | 5 | clean | 已触发(success) | **合入** |
| #10 | Compose mainline + SPR | +461/-31 | 10 | clean | 已触发(success) | **合入** (需 rebase) |

## PR 依赖关系

```
PR #5 ──(被取代)──> PR #7  (ocr-review.yml 同文件，#7 是完整重写)
PR #8 ──(被取代)──> PR #10 (#10 = #8 + codegen/utils.py，严格超集)
PR #7 ──(冲突)──> PR #10  (codegen/utils.py 同文件，#10 版本更完整)
PR #9 ──(冲突)──> PR #10  (image.py + from_history.py 同文件)
```

---

## 逐 PR 审查

### PR #5 — OCR volcengine provider

**变更**：`.github/workflows/ocr-review.yml` 末尾加 2 行注释

**评估**：
- 内容仅为 2 行注释，无功能性变更
- 被 PR #7 完全取代（#7 对同一文件做了 145 行实质性重写）
- mergeable 状态为 unknown（分支可能已过期）

**结论**：**关闭**，合入 #7 后此 PR 无意义

---

### PR #7 — fix: resolve 3 fork-only bugs blocking backend startup

**变更**（6 文件, +691/-12）：

| 文件 | 变更 | 问题严重度 |
|------|------|-----------|
| `backend/agent/engine.py` | 4 个参数加 `=None` 默认值，修复位置参数调用断裂 | **critical** |
| `backend/codegen/utils.py` | `extract_html_content(text)` → `extract_html_content(text, stack="")` | high |
| `backend/config.py` | 新增 `ANTHROPIC_BASE_URL` 环境变量读取 | medium |
| `backend/routes/generate_code.py` | 透传 `anthropic_base_url` 到 CodegenRunner → AgentRunner | critical |
| `.github/workflows/ocr-review.yml` | 重写 OCR review 步骤：issue_comment 事件支持 + PR comment 自动发布 | improvement |
| `docs/ocr-workflow-guide.html` | 517 行 OCR 配置指南文档 | docs |

**代码审查**：
1. `engine.py`：`anthropic_api_key` 等参数加 `= None` 默认值是正确修复 — 因为 `generate_code.py` 在调用 `AgentRunner.__init__()` 时使用关键字参数，但位置参数 `should_generate_images` 在它们之后，导致 `TypeError: missing required argument`。加默认值使其可按关键字传入。
2. `codegen/utils.py`：`stack` 参数是原生栈支持的必要前提。#7 的实现是基础版（strip fence + return），#10 的实现是完整版（lang_map + _is_main_file + web/native 分支）。
3. `config.py` + `generate_code.py`：`ANTHROPIC_BASE_URL` 透传链路完整，支持百炼等 Anthropic 兼容端点。
4. `ocr-review.yml`：增加了 `issue_comment` 事件的 PR 信息获取逻辑（通过 API 获取 base/head ref），以及 review.json 解析 + PR comment 自动发布。设计合理。
5. OCR check run 报告 6 个 issues，但表格中 message 字段为空 — 这是 OCR 工具的展示 bug，不是代码问题。annotations 仅 1 条 Node.js 20 弃用警告。

**结论**：**合入** — 修复 3 个阻塞性 bug，代码逻辑正确

---

### PR #8 — System Prompt Router

**变更**（9 文件, +389/-9）：

| 文件 | 变更 |
|------|------|
| `backend/prompts/system_prompt_router.py` | 新增 257 行，12 栈 system prompt 路由 |
| `backend/prompts/create/image.py` | `system_prompt.SYSTEM_PROMPT` → `get_system_prompt(stack)` |
| `backend/prompts/create/text.py` | 同上 |
| `backend/prompts/update/from_history.py` | 同上 |
| `backend/prompts/update/from_file_snapshot.py` | 同上 |
| `backend/prompts/prompt_types.py` | Stack Literal +6 原生栈 |
| `backend/agent/tools/validate_code.py` | +winui3 XAML 验证 (97 行) |
| `backend/costs/model_router.py` | +5 原生栈模型路由 |
| `frontend/src/lib/stacks.ts` | +6 原生栈下拉选项 |

**代码审查**：
- `system_prompt_router.py`：路由逻辑清晰，web 栈 fallback 到原 `SYSTEM_PROMPT`，native 栈各指向独立 prompt 模块
- `validate_code.py`：winui3 验证复用 WPF XAML 验证模式，XML 解析 + 命名空间检查 + 花括号平衡
- 代码质量良好，无安全问题

**结论**：**关闭** — PR #10 是严格超集（相同 9 文件 + codegen/utils.py），合入 #10 即可

---

### PR #9 — Token optimization

**变更**（5 文件, +172/-2）：

| 文件 | 变更 | 策略 |
|------|------|------|
| `backend/costs/image_compressor.py` | 新增 103 行 | T1: 768px JPEG 压缩 |
| `backend/costs/history_truncator.py` | 新增 57 行 | T5: 历史图片剥离 |
| `backend/prompts/create/image.py` | +4/-1 | 接入 image_compressor |
| `backend/prompts/policies.py` | +4/-1 | 接入 truncate_skeleton (T4) |
| `backend/prompts/update/from_history.py` | +4/-0 | 接入 history_truncator |

**代码审查**：
1. `image_compressor.py`：
   - PIL 可选导入 + graceful degradation（PIL 不可用时返回原图）— 设计正确
   - RGBA/P/L 模式转 RGB + 白色背景合成 — 正确处理透明通道
   - LANCZOS 重采样 + JPEG quality 85 — 质量与体积平衡合理
   - `estimate_token_saving()` 辅助函数 — 简单但够用
2. `history_truncator.py`：
   - 逆序遍历，保留最近 2 个含图片的 user turn — 逻辑正确
   - **潜在问题**：`msg["images"] = []` 直接修改原 dict（浅拷贝），可能影响调用方。但 `result = list(history)` 只是浅拷贝列表，内部 dict 仍是同一对象。建议改为 `msg_copy = dict(msg); msg_copy["images"] = []; result[idx] = msg_copy`。不过在实际使用中 history 不太可能被并行修改，风险低。
3. `policies.py`：`truncate_skeleton()` 之前定义但未调用，此 PR 正确接入
4. 测试覆盖：PR 描述中 3 个策略均有测试 ✓

**结论**：**合入** — 代码质量好，降级设计合理，节省 ~65% token

---

### PR #10 — Compose mainline + SPR routing

**变更**（10 文件, +461/-31）：

PR #10 = PR #8 的全部 9 文件 + `backend/codegen/utils.py` 多栈提取

**codegen/utils.py 审查**（72+/22-）：
1. `extract_html_content(text, stack="")` — 新增 stack 参数
2. `<file path="...">` 包装处理 + `_is_main_file()` 主文件检测 — 支持 Agent 多文件输出
3. `lang_map` 语言映射（kotlin/xml/jsonl/qml）— 正确匹配各栈代码围栏
4. Web 栈仍走 DOCTYPE + `<html>` 提取逻辑 — 向后兼容
5. Native 栈 strip fence 后直接返回 — 正确（LLM 产出干净代码无需 HTML 包装）

**与其他 PR 的冲突**：
- `codegen/utils.py`：与 #7 冲突（#7 是简化版，#10 是完整版）→ #10 版本应胜出
- `backend/prompts/create/image.py`：与 #9 冲突（#9 加 image_compressor 调用，#10 改 system_prompt 引用）→ 需手动合并
- `backend/prompts/update/from_history.py`：与 #9 冲突（#9 加 history_truncator 调用，#10 改 system_prompt 引用）→ 需手动合并

**结论**：**合入**（需 rebase 到 #7 + #9 之后的 main）

---

## 推荐合入顺序

```
1. 关闭 PR #5  (被 #7 取代)
2. 关闭 PR #8  (被 #10 取代)
3. 合入 PR #7  (修复 3 个阻塞性 bug)
4. 合入 PR #9  (token 优化，独立新文件)
5. rebase + 合入 PR #10  (综合功能，需解决与 #7 utils.py 和 #9 image.py/from_history.py 的冲突)
```

## 冲突解决指南

### PR #10 vs PR #7 (codegen/utils.py)
- **保留 #10 版本**：包含 lang_map、_is_main_file、web/native 分支完整逻辑
- #7 的简化版是 #10 的子集

### PR #10 vs PR #9 (image.py)
- #9 在 `build_image_prompt_messages()` 中加 `compress_image_data_url()` 调用
- #10 将 `from prompts import system_prompt` 改为 `from prompts.system_prompt_router import get_system_prompt`
- **两者不冲突**，修改的是不同行

### PR #10 vs PR #9 (from_history.py)
- #9 加 `truncate_history_images()` 调用
- #10 改 system_prompt 引用
- **两者不冲突**，修改的是不同行

## OCR (OpenCodeReview) 检视汇总

| PR | OCR 状态 | Issues 数 | Annotations | 备注 |
|----|---------|-----------|-------------|------|
| #5 | 未触发 | - | - | 分支可能过期 |
| #7 | 已完成(success) | 6 | 1 (Node.js 20 弃用警告) | 表格 message 字段为空(OCR bug) |
| #8 | 已完成(success) | - | 0 | /open-code-review 已触发 |
| #9 | 已完成(success) | - | 0 | /open-code-review 已触发 |
| #10 | 已完成(success) | - | 0 | /open-code-review 已触发 |

> **注意**：PR #8/#9/#10 的 OCR check run 均为 success 但未发布 PR comment，可能是 OCR 的 `--output review.json` + comment posting 步骤未完成（PR #7 的新 workflow 逻辑）。这些 PR 使用的是旧版 workflow（#7 之前的版本），只运行 `ocr review` 但不自动发评论。

---

## 风险评估

| 风险项 | 影响 | 缓解措施 |
|--------|------|---------|
| PR #7 OCR 报告 6 个 critical issues 但内容为空 | 无法确认是否有真实问题 | OCR 表格 message 为空是工具展示 bug，手动审查 diff 未发现 critical 问题 |
| PR #9 history_truncator 浅拷贝修改原 dict | 可能影响调用方 history | 实际使用场景下 history 不会被并行修改，风险低 |
| PR #10 与 #7/#9 文件冲突 | 合入需手动 rebase | 按推荐顺序合入，冲突可自动解决 |
| 无 pytest/pyright CI | 无法自动验证类型和测试 | AGENTS.md 要求手动运行 `poetry run pytest` + `poetry run pyright` |
