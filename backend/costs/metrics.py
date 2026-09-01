"""Lightweight Prometheus-compatible metrics exporter.

Provides Counter and Gauge primitives that expose a `/metrics` endpoint in
Prometheus text format.  No external dependency on prometheus_client —
the format is simple enough to emit directly.

Usage:
    from costs.metrics import record_usage, render_metrics
    record_usage(usage, "gemini-3.6-flash", "html_tailwind", pricing)
    # In a FastAPI route:
    return PlainTextResponse(render_metrics(), media_type="text/plain")

Design ref: design-docs/token-governance-design.md §3.4 R3.1
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional, Tuple, Union

from costs.pricing import ModelPricing
from costs.token_usage import TokenUsage

_lock = threading.Lock()


def _escape_label(value: str) -> str:
    """Escape a label value per Prometheus exposition format."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class _Counter:
    """A labeled counter (monotonic increase only)."""

    def __init__(self, name: str, help_text: str, label_names: List[str]):
        self._name = name
        self._help = help_text
        self._label_names = label_names
        self._values: Dict[Tuple[str, ...], float] = {}

    def inc(self, amount: float = 1.0, **labels: str) -> None:
        key = tuple(labels[ln] for ln in self._label_names)
        with _lock:
            self._values[key] = self._values.get(key, 0.0) + amount

    def render(self) -> str:
        lines = [f"# HELP {self._name} {self._help}",
                 f"# TYPE {self._name} counter"]
        with _lock:
            for key, val in sorted(self._values.items()):
                if self._label_names:
                    label_str = ",".join(
                        f'{ln}="{_escape_label(lv)}"' for ln, lv in zip(self._label_names, key)
                    )
                    lines.append(f"{self._name}{{{label_str}}} {val}")
                else:
                    lines.append(f"{self._name} {val}")
        return "\n".join(lines)


class _Gauge:
    """A labeled gauge (set to arbitrary value)."""

    def __init__(self, name: str, help_text: str, label_names: List[str]):
        self._name = name
        self._help = help_text
        self._label_names = label_names
        self._values: Dict[Tuple[str, ...], float] = {}

    def set(self, value: float, **labels: str) -> None:
        key = tuple(labels[ln] for ln in self._label_names)
        with _lock:
            self._values[key] = value

    def render(self) -> str:
        lines = [f"# HELP {self._name} {self._help}",
                 f"# TYPE {self._name} gauge"]
        with _lock:
            for key, val in sorted(self._values.items()):
                if self._label_names:
                    label_str = ",".join(
                        f'{ln}="{_escape_label(lv)}"' for ln, lv in zip(self._label_names, key)
                    )
                    lines.append(f"{self._name}{{{label_str}}} {val}")
                else:
                    lines.append(f"{self._name} {val}")
        return "\n".join(lines)


# --- Metric instances (R3.1 spec) ---

AI_TOKENS_INPUT = _Counter(
    "ai_tokens_input_total", "Total input tokens", ["model", "stack"]
)
AI_TOKENS_OUTPUT = _Counter(
    "ai_tokens_output_total", "Total output tokens", ["model", "stack"]
)
AI_TOKENS_CACHE_READ = _Counter(
    "ai_tokens_cache_read_total", "Cache read tokens", ["model", "stack"]
)
AI_COST_USD = _Counter(
    "ai_cost_usd_total", "Total LLM cost in USD", ["model", "stack"]
)
AI_BUDGET_UTILIZATION = _Gauge(
    "ai_budget_utilization", "Budget utilization ratio 0-1", ["variant"]
)
AI_CACHE_HIT_RATE = _Gauge(
    "ai_prompt_cache_hit_rate", "Cache hit rate %", ["model"]
)
AI_CIRCUIT_BREAKER = _Gauge(
    "ai_circuit_breaker_open", "Circuit breaker open (1) or closed (0)", []
)

_Metric = Union[_Counter, _Gauge]

_ALL_METRICS: List[_Metric] = [
    AI_TOKENS_INPUT,
    AI_TOKENS_OUTPUT,
    AI_TOKENS_CACHE_READ,
    AI_COST_USD,
    AI_BUDGET_UTILIZATION,
    AI_CACHE_HIT_RATE,
    AI_CIRCUIT_BREAKER,
]


def record_usage(
    usage: TokenUsage,
    model: str,
    stack: str,
    pricing: Optional[ModelPricing] = None,
) -> None:
    """Record a TokenUsage snapshot. Call after TokenUsage.accumulate()."""
    AI_TOKENS_INPUT.inc(usage.input, model=model, stack=stack)
    AI_TOKENS_OUTPUT.inc(usage.output, model=model, stack=stack)
    AI_TOKENS_CACHE_READ.inc(usage.cache_read, model=model, stack=stack)
    if pricing is not None:
        AI_COST_USD.inc(usage.cost(pricing), model=model, stack=stack)
    AI_CACHE_HIT_RATE.set(usage.cache_hit_rate_percent(), model=model)


def record_budget(variant: int, spent: float, limit: float) -> None:
    """Record budget utilization for a variant."""
    ratio = spent / limit if limit > 0 else 0.0
    AI_BUDGET_UTILIZATION.set(ratio, variant=str(variant))


def record_circuit_breaker(is_open: bool) -> None:
    """Record circuit breaker state."""
    AI_CIRCUIT_BREAKER.set(1.0 if is_open else 0.0)


def render_metrics() -> str:
    """Render all metrics in Prometheus text format."""
    return "\n\n".join(m.render() for m in _ALL_METRICS) + "\n"


def reset() -> None:
    """Reset all metric values. For testing only."""
    with _lock:
        for m in _ALL_METRICS:
            m._values.clear()
