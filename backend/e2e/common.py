"""Shared helpers for the one-click generation pipeline (backend/e2e).

These utilities are intentionally dependency-light and reusable by both the
generation core (``generate/``), the injector (``inject.py``) and the CLI
(``cli.py``), so the screenshot-to-code fork no longer needs ad-hoc scripts
that hardcode ``RUN_DIR``.
"""
from __future__ import annotations

import base64
import os
import time
from pathlib import Path

import httpx
from PIL import Image

# ---------------------------------------------------------------------------
# Stack registry — single source of truth for stack -> extension / label / req
# Mirrors design-docs/e2e-artifacts-organization.md §2.2
# ---------------------------------------------------------------------------
STACKS: dict[str, dict] = {
    "android_compose": {
        "ext": "kt", "label": "KOTLIN",
        "req": "Android Jetpack Compose，@Composable 函数，Material3 组件",
    },
    "android_xml": {
        "ext": "xml", "label": "XML",
        "req": "Android XML Layout，LinearLayout 根元素，含 xmlns:android",
    },
    "qt_qml": {
        "ext": "qml", "label": "QML",
        "req": "QtQuick Controls，ApplicationWindow 根元素",
    },
    "windows_html": {
        "ext": "html", "label": "HTML",
        "req": "自包含 HTML（DOCTYPE + 内联 CSS），卡片式设置布局",
    },
    "windows_wpf": {
        "ext": "xaml", "label": "WPF",
        "req": "WPF XAML，Window 根元素，含 xmlns",
    },
    "winui3": {
        "ext": "xaml", "label": "WINUI3",
        "req": "WinUI 3 XAML，Page 根元素，含 xmlns",
    },
    "a2ui": {
        "ext": "jsonl", "label": "A2UI",
        "req": (
            "JSONL 格式，每行一个 JSON 对象（不要数组、不要 markdown 围栏）。\n"
            "节点字段：\n"
            "- id(必填, 唯一字符串)\n"
            "- type(必填, 取值: button/card/column/container/image/input/list/row/stack/text/switch/dropdown/slider/divider)\n"
            "- children(必填, 子节点 id 字符串数组，用于构建树；容器写子节点 id 列表，叶子节点写 children:[])\n"
            "- parent(可选, 父节点 id，作为回退链接)\n"
            "- props(对象, 包裹所有视觉与行为属性: text/label/title/src/options/checked/value/min/max/step/placeholder/primaryColor/className，"
            "以及 CSS 类 width/height/backgroundColor/color/fontSize/fontWeight/borderRadius/padding/margin/flexDirection/justifyContent/alignItems/gap/flex/display)\n"
            "根节点 id 为 \"root\"，整棵树通过 children 引用挂接。示例:\n"
            '{"id":"root","type":"column","children":["title","row1"],"props":{"gap":12}}\n'
            '{"id":"title","type":"text","children":[],"props":{"text":"Settings","fontSize":20}}\n'
            '{"id":"row1","type":"row","children":["t","sw"],"props":{"gap":8}}\n'
            '{"id":"t","type":"text","children":[],"props":{"text":"Enable"}}\n'
            '{"id":"sw","type":"switch","children":[],"props":{"checked":true}}'
        ),
    },
}

ALL_STACKS = list(STACKS.keys())


def stack_ext(stack: str) -> str:
    return STACKS[stack]["ext"]


def code_filename(stack: str) -> str:
    """Canonical code file name inside ``<run>/code/``."""
    return f"{stack}.{STACKS[stack]['ext']}"


# ---------------------------------------------------------------------------
# Run directory layout (replaces every hardcoded RUN_DIR)
# ---------------------------------------------------------------------------
def make_run_dir(model: str, base: Path | None = None) -> Path:
    """Create ``e2e_runs/<YYYYMMDD>T<HHMMSS>_<model_slug>/`` with subdirs.

    Uses a real execution timestamp so the same model can be compared across
    multiple runs (forward-looking variant from the E2E plan §2.1).
    """
    slug = model.replace(".", "-").lower()
    ts = time.strftime("%Y%m%dT%H%M%S")
    run_id = f"{ts}_{slug}"
    root = (base or Path(__file__).resolve().parent.parent.parent) / "e2e_runs"
    run = root / run_id
    for sub in ("code", "code/variants", "reports", "renders", "inputs", "subruns", "misc"):
        (run / sub).mkdir(parents=True, exist_ok=True)
    return run


# ---------------------------------------------------------------------------
# LLM call — Volcano Ark OpenAI-compatible endpoint (reuses fork's proven path)
# ---------------------------------------------------------------------------
def _api_key() -> str:
    # Prefer the explicit Ark key, fall back to the OpenAI-style var used in .env
    return os.environ.get("ARK_API_KEY") or os.environ.get("OPENAI_API_KEY", "")


def _base_url() -> str:
    return os.environ.get("OPENAI_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3").rstrip("/")


def chat(messages: list[dict], model: str, *, max_tokens: int = 8000,
         temperature: float = 0.3, timeout: float = 600.0) -> tuple[str, dict, str]:
    """Call ``/chat/completions``. Returns (content, usage, finish_reason).

    ``finish_reason`` is ``"length"`` when the model hit ``max_tokens`` and the
    output was TRUNCATED (Ark does not raise an error on truncation, so callers
    must check this to avoid writing incomplete code).

    Raises ``RuntimeError`` on non-200 so callers can retry per-stack.
    """
    key = _api_key()
    if not key:
        raise RuntimeError("No API key: set ARK_API_KEY or OPENAI_API_KEY")
    resp = httpx.post(
        f"{_base_url()}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        },
        timeout=timeout,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"LLM HTTP {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    choice = data["choices"][0]
    return choice["message"]["content"], data.get("usage", {}), choice.get("finish_reason", "")


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------
def compress_image(image_path: str | Path, max_width: int = 768) -> str:
    """Resize to ``max_width`` and return a base64 JPEG data URI (keeps payload small)."""
    img = Image.open(image_path).convert("RGB")
    if img.width > max_width:
        h = round(img.height * max_width / img.width)
        img = img.resize((max_width, h))
    import io
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def strip_fence(code: str) -> str:
    """Remove a leading/trailing markdown code fence if present."""
    code = code.strip()
    if code.startswith("```"):
        lines = code.split("\n")[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        code = "\n".join(lines)
    return code.strip()
