# 脚本直调流程优化方案

> 参考前端 WebSocket → Agent 流程，对 `generate_5stacks.py` 等直调脚本的 6 个优化点

## 当前问题

脚本直调流程是"生成即终态"——LLM 输出代码后直接写文件，无验证、无修复、无预算控制。与前端 Agent 循环（最多 30 轮 + 9 个工具 + 预算检查 + 流式预览）相比缺失关键反馈机制。

## 优化总览

| 优先级 | 优化项 | 参考前端对应物 | 预期收益 |
|--------|--------|---------------|---------|
| P0 | ① 验证-修复循环 | Agent engine.py 30 轮循环 + validate_code | PASS 率 ~60% → ~90% |
| P1 | ② ADB 设计数据注入 | policies.py build_adb_data_policy | 色彩/布局精确度提升 |
| P1 | ③ System Prompt 分离 | system_prompt.py SYSTEM_PROMPT | 代码结构一致性 |
| P2 | ④ Token 预算控制 | budget_checker.py check_budget | 成本可控 |
| P2 | ⑤ 错误重试+退避 | generate_code.py variantError | 稳定性 |
| P3 | ⑥ 流式输出（可选） | WebSocket setCode/chunk | 调试可见性 |

---

## 优化①：Validate → Fix 循环（P0 - 核心）

### 参考来源

前端 Agent 引擎 (`backend/agent/engine.py:237-372`) 的核心循环：
```
for _ in range(max_steps):  # max_steps = 30
    turn = await session.stream_turn(on_event)
    if not turn.tool_calls:
        return await self._finalize_response(turn.assistant_text)
    # 检查预算 → 执行工具 → append_tool_results → 继续循环
```

前端虽然没注册 validate_code 工具，但循环结构本身（生成→反馈→再生成）是脚本缺失的关键能力。

### 实现方案

在 `generate_5stacks.py` 的 Step 2 生成循环中加入验证-修复环节：

```python
from agent.tools.validate_code import validate_code

# 栈名 → validate_code 的 stack 参数映射
STACK_VALIDATE_MAP = {
    "android_compose": "android_compose",
    "android_xml": "android_xml",
    "qt_qml": "qt_qml",
    "html": "html",
    "a2ui": "a2ui",
}

MAX_FIX_ROUNDS = 3  # 每个栈最多修复 3 轮

async def generate_with_validation(
    client: httpx.AsyncClient,
    stack: str,
    ui_desc: str,
    max_tokens: int,
) -> dict:
    """生成代码 → 验证 → 修复循环"""
    code = ""
    errors_log = []

    for round_num in range(MAX_FIX_ROUNDS + 1):  # 0=初始生成, 1-3=修复
        if round_num == 0:
            # 初始生成
            prompt = make_stack_prompt(stack, ui_desc)
        else:
            # 修复 prompt：原代码 + 验证错误
            error_list = "\n".join(
                f"  行 {e['line']}:{e['col']} [{e['severity']}] {e['message']}"
                for e in errors_log[-1]
            )
            prompt = f"""以下 {stack} 代码存在验证错误，请修复后输出完整代码。

原始代码:
{code}

验证错误:
{error_list}

要求:
1. 修复所有上述错误
2. 输出完整修复后的代码
3. 不要 markdown fence"""

        messages = [{"role": "user", "content": prompt}]
        resp = await call_ark(client, messages, model=TEXT_MODEL, max_tokens=max_tokens)
        code = extract_content(resp)
        code = strip_markdown_fence(code)

        # 验证
        validate_stack = STACK_VALIDATE_MAP.get(stack)
        if not validate_stack:
            break  # 无验证器的栈直接返回

        result = validate_code(validate_stack, code)
        if result["ok"]:
            return {
                "code": code,
                "rounds": round_num,
                "errors_history": errors_log,
                "ok": True,
            }

        errors_log.append(result["errors"])
        print(f"  [{stack}] Round {round_num}: {len(result['errors'])} errors")

    # 超过最大修复轮次
    return {
        "code": code,
        "rounds": MAX_FIX_ROUNDS,
        "errors_history": errors_log,
        "ok": False,
        "final_errors": errors_log[-1] if errors_log else [],
    }
```

### 改造 main() 中的生成循环

```python
# 原来直接调 call_ark → 改为调 generate_with_validation
for i, (stack, filename, max_tok) in enumerate(stacks, 1):
    result = await generate_with_validation(client, stack, ui_desc, max_tok)

    out_path = OUTPUT_DIR / filename
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(result["code"])

    results[stack] = {
        "file": filename,
        "chars": len(result["code"]),
        "fix_rounds": result["rounds"],
        "ok": result["ok"],
        "final_errors": result.get("final_errors", []),
    }
```

### 成本影响

- 乐观：5 栈一次通过，0 额外调用（与当前相同 ~26K tokens）
- 悲观：5 栈各修复 3 轮，最多 +15 次调用 ≈ +78K tokens（~¥1.17）
- 预期平均：2-3 栈需要 1-2 轮修复 ≈ +10-20K tokens（~¥0.15-0.30）

---

## 优化②：ADB 设计数据注入（P1）

### 参考来源

前端 WebSocket 流程中，ADB 捕获的 theme.json + skeleton.json 通过 `policies.py` 的 `build_adb_data_policy()` 注入 prompt：

```python
# backend/prompts/policies.py:21-60
parts.append("USE THESE EXACT values — do not approximate.")
parts.append("If fill_ratio < 0.5 for an element, set that element's container to transparent.")
parts.append("Use the exact hex codes from theme.json. Do not guess colors.")
```

### 当前脚本问题

`generate_5stacks.py` 只用截图 base64 做 Vision 分析，**不使用** skeleton/theme 数据。LLM 只能从像素推测颜色和布局，精度低。

### 实现方案

```python
from prompts.policies import build_adb_data_policy

# 读取 ADB 提取的数据（如果存在）
theme_path = SCREENSHOT_DIR / "theme.json"
skeleton_path = SCREENSHOT_DIR / "skeleton.json"
theme_json = theme_path.read_text() if theme_path.exists() else None
skeleton_json = skeleton_path.read_text() if skeleton_path.exists() else None

# 注入到栈生成 prompt
adb_block = build_adb_data_policy(theme_json, skeleton_json)

def make_stack_prompt(stack: str, ui_desc: str, adb_block: str = "") -> str:
    base = f"""请根据以下 UI 描述，生成一个 {stack} 格式的设置页面代码。

UI 描述:
{ui_desc}
{adb_block}
..."""
```

### 效果

- 颜色精确匹配（从 LLM 猜测 → 使用设备提取的精确 hex）
- 布局结构对齐（skeleton 提供精确 bounds_device 坐标）
- fill_ratio 约束（避免透明区域被填色）

---

## 优化③：System Prompt 分离（P1）

### 参考来源

前端 WebSocket 使用 `system_prompt.py` 的 `SYSTEM_PROMPT`（96 行结构化指令），而脚本只用内联 f-string prompt。

### 实现方案

为脚本创建栈相关的 system prompt，作为 messages 的 system 角色消息：

```python
STACK_SYSTEM_PROMPTS = {
    "android_compose": """You are an expert Android Jetpack Compose developer.
Generate clean, idiomatic Kotlin code using Material 3 components.
Requirements:
- @Composable functions with proper imports
- Column/Row for layout
- Material 3 Switch, Text, Button
- No hardcoded colors — use MaterialTheme.colorScheme
- Balance all braces and parentheses""",

    "html": """You are an expert front-end developer.
Generate self-contained HTML with inline CSS.
Requirements:
- DOCTYPE + html/head/body structure
- No external resources (fonts, CSS frameworks)
- Card-based layout with toggle switches
- Semantic HTML5 elements""",

    # ... 其他栈类似
}

# 调用时分离 system + user
messages = [
    {"role": "system", "content": STACK_SYSTEM_PROMPTS[stack]},
    {"role": "user", "content": user_prompt_with_ui_desc},
]
```

### 效果

- 代码一致性提升（每次生成都遵循同一组约束）
- token 效率：system prompt 不含 UI 描述，可被模型缓存

---

## 优化④：Token 预算控制（P2）

### 参考来源

前端 `budget_checker.py`：
- `check_budget(spent)` → 50%/75%/90% 分级告警，>100% 硬限中止
- `check_circuit_breaker()` → 滑动窗口 5 次 abort → 10 分钟冷却
- `record_abort()` → 记录预算超限

### 实现方案（简化版）

脚本场景不需要跨会话断路器，只需单次运行预算：

```python
MAX_TOKEN_BUDGET = 100_000  # 单次运行总 token 上限
WARN_THRESHOLD = 0.50
ALERT_THRESHOLD = 0.75
CRITICAL_THRESHOLD = 0.90

def check_budget(spent_tokens: int, budget: int = MAX_TOKEN_BUDGET) -> dict:
    ratio = spent_tokens / budget
    if ratio > 1.0:
        return {"allow": False, "level": "exceeded", "reason": f"{spent_tokens} > {budget}"}
    if ratio >= CRITICAL_THRESHOLD:
        return {"allow": True, "level": "critical"}
    if ratio >= ALERT_THRESHOLD:
        return {"allow": True, "level": "alert"}
    if ratio >= WARN_THRESHOLD:
        return {"allow": True, "level": "warn"}
    return {"allow": True, "level": "none"}

# 在生成循环中每轮检查
total_usage = {"input": 0, "output": 0, "total": 0}

def track_usage(resp_usage: dict):
    total_usage["input"] += resp_usage["input"]
    total_usage["output"] += resp_usage["output"]
    total_usage["total"] += resp_usage["total"]
    decision = check_budget(total_usage["total"])
    if not decision["allow"]:
        raise BudgetExceededError(decision["reason"])
    if decision["level"] != "none":
        print(f"[BUDGET {decision['level'].upper()}] {total_usage['total']}/{MAX_TOKEN_BUDGET}")
```

---

## 优化⑤：错误重试 + 速率限制退避（P2）

### 参考来源

前端 `generate_code.py:613-713` 的 `_run_variant()` 捕获 `openai.AuthenticationError`/`NotFoundError`/`RateLimitError`，发送 `variantError`。

### 实现方案

```python
import asyncio

MAX_RETRIES = 3
RETRY_DELAYS = [1, 5, 15]  # 指数退避秒数

async def call_ark_with_retry(
    client: httpx.AsyncClient,
    messages: list[dict],
    model: str = TEXT_MODEL,
    max_tokens: int = 4096,
) -> dict:
    """带重试的 Ark API 调用"""
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = await client.post(...)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            last_error = e
            if e.response.status_code == 429:
                # 速率限制，指数退避
                delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                print(f"  Rate limited, retrying in {delay}s (attempt {attempt+1}/{MAX_RETRIES})")
                await asyncio.sleep(delay)
            elif e.response.status_code >= 500:
                # 服务端错误，短暂等待后重试
                await asyncio.sleep(2)
            else:
                # 4xx 非 429，不重试
                raise
        except httpx.RequestError as e:
            last_error = e
            await asyncio.sleep(2)

    raise last_error  # 重试耗尽
```

---

## 优化⑥：流式输出（P3 - 可选）

### 参考来源

前端 WebSocket 通过 `stream=True` 逐 token 推送 `setCode`/`chunk` 到前端实时渲染。脚本场景无前端，但流式有以下好处：
- 长时间生成时能看到进度（而非等 30s 后一次性返回）
- 可提前检测截断（`finish_reason: length`）

### 实现方案

```python
async def call_ark_streaming(
    client: httpx.AsyncClient,
    messages: list[dict],
    model: str = TEXT_MODEL,
    max_tokens: int = 4096,
) -> tuple[str, dict]:
    """流式调用 Ark API，实时打印进度"""
    body = {"model": model, "messages": messages, "max_tokens": max_tokens,
            "temperature": 0.3, "stream": True}
    async with client.stream("POST", f"{ARK_BASE_URL}/chat/completions",
                              headers=headers, json=body, timeout=300.0) as resp:
        resp.raise_for_status()
        full_content = ""
        usage = {"input": 0, "output": 0, "total": 0}
        chars_since_dot = 0

        async for line in resp.aiter_lines():
            if not line.startswith("data: "):
                continue
            data = json.loads(line[6:])
            if data.get("choices"):
                delta = data["choices"][0].get("delta", {})
                chunk = delta.get("content", "")
                if chunk:
                    full_content += chunk
                    chars_since_dot += 1
                    if chars_since_dot >= 200:
                        print(f"  ...{len(full_content)} chars", end="\r")
                        chars_since_dot = 0
            if data.get("usage"):
                usage = extract_usage(data)

        return full_content, usage
```

### 注意

流式不影响功能，仅改善调试体验。如果不需要实时进度可跳过此优化。

---

## 实施建议

### 第一阶段（P0 + P1）— 最高 ROI

1. **实现优化①**：在 `generate_5stacks.py` 加入 `generate_with_validation()` 函数
   - 需要将 `backend/agent/tools/validate_code.py` 加入 sys.path
   - 改造 Step 2 循环为 `generate_with_validation` 调用
   - 预计改动 ~80 行

2. **实现优化②**：读取 theme.json/skeleton.json 注入 prompt
   - 调用 `build_adb_data_policy()`
   - 改造 `make_stack_prompt()` 签名
   - 预计改动 ~20 行

3. **实现优化③**：添加 `STACK_SYSTEM_PROMPTS` 字典
   - 消息结构从 `[user]` → `[system, user]`
   - 预计改动 ~40 行

### 第二阶段（P2）— 稳定性加固

4. **实现优化④**：`check_budget()` + `track_usage()`
5. **实现优化⑤**：`call_ark_with_retry()` 替换 `call_ark()`

### 第三阶段（P3）— 体验优化

6. **实现优化⑥**：`call_ark_streaming()`（可选）

### 安全性修复（必须）

`generate_5stacks_combined.py` 第 13 行硬编码了 API Key：
```python
API_KEY = os.environ.get("ARK_API_KEY", "REDACTED")
```
应改为 `os.environ.get("ARK_API_KEY", "")`，并轮换已暴露的 Key。
