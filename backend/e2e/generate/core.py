"""Generation core for the one-click pipeline.

Two stages:
  1. ``describe_image``  — 1 vision call turns a screenshot into a UI description.
  2. ``generate_stacks`` — N text calls (one per requested stack) reuse that
     description, so the visual model is hit only ONCE (token strategy from the
     project memory: ~26K vs 75K, saves ~65%).
"""
from __future__ import annotations

import json
from pathlib import Path

from ..common import STACKS, chat, compress_image, strip_fence

VISION_PROMPT = """请用中文详细描述这张 UI 截图，用于后续生成多技术栈代码。
输出结构化描述，包含：
- 整体主题（亮/暗）、主色调、圆角与间距风格
- 顶部/中部/底部各区域及其包含的组件（按钮、卡片、列表、输入框、图标、文字等）
- 每个组件的层级、文本内容、关键样式
- 布局结构（纵向滚动？分栏？底部 Tab？）
不要生成代码，只做描述。"""

STACK_PROMPT = """根据下面的 UI 描述，生成【{label}】技术栈的代码。

UI 描述:
{ui_desc}

要求: {req}

直接输出代码，不要 markdown 代码块围栏（不要 ```），不要解释。"""


def describe_image(image_path: str | Path, model: str) -> str:
    """Single vision call -> UI description text."""
    data_uri = compress_image(image_path)
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": data_uri}},
                {"type": "text", "text": VISION_PROMPT},
            ],
        }
    ]
    content, _, _ = chat(messages, model, max_tokens=2000, temperature=0.2)
    return content.strip()


def generate_stacks(ui_desc: str, stacks: list[str], model: str) -> dict:
    """Generate one code string per requested stack.

    Returns {stack: {"code", "chars", "ok", "error"}}. Does NOT write files —
    placement is delegated to ``inject.py`` so generation and injection stay
    separate (per "生成结果通过固定脚本替换到框架").
    A failure on one stack does NOT abort the others (per confirmed strategy:
    per-stack text calls are independently retryable).
    """
    results: dict[str, dict] = {}
    for stack in stacks:
        cfg = STACKS[stack]
        prompt = STACK_PROMPT.format(label=cfg["label"], ui_desc=ui_desc, req=cfg["req"])
        try:
            # Start with a generous token budget so detailed UIs are not cut
            # off. If the model still hits the limit, auto-expand and retry
            # (Ark returns finish_reason="length" on silent truncation).
            max_tokens = 12000
            content, usage, finish = chat(
                [{"role": "user", "content": prompt}],
                model,
                max_tokens=max_tokens,
                temperature=0.3,
            )
            attempts = 1
            while finish == "length" and attempts < 3:
                max_tokens = min(max_tokens * 2, 24000)
                content, usage, finish = chat(
                    [{"role": "user", "content": prompt}],
                    model,
                    max_tokens=max_tokens,
                    temperature=0.3,
                )
                attempts += 1
            truncated = finish == "length"
            code = strip_fence(content)
            results[stack] = {
                "code": code,
                "chars": len(code),
                "ok": True,
                "truncated": truncated,
                "usage": usage,
            }
        except Exception as e:  # noqa: BLE001 — isolate per-stack failure
            results[stack] = {"code": "", "chars": 0, "ok": False, "error": str(e)}
    return results


def estimate_cost(usage: dict) -> float:
    """Rough Volcano Ark cost in CNY (input ¥0.003/K, output ¥0.015/K)."""
    inp = usage.get("prompt_tokens", 0)
    out = usage.get("completion_tokens", 0)
    return round((inp * 0.003 + out * 0.015) / 1000, 4)
