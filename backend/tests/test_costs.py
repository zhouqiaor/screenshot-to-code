"""Tests for costs module: metrics, model_router, budget_checker integration."""

from __future__ import annotations

from costs.metrics import (
    render_metrics,
    record_usage,
    record_budget,
    record_circuit_breaker,
    reset as reset_metrics,
)
from costs.model_router import route_model, STACK_MODEL_PREFERENCE
from costs.pricing import ModelPricing
from costs.token_usage import TokenUsage
from llm import Llm


# --- model_router tests ---


def test_route_user_model_takes_precedence() -> None:
    """User's explicit model choice always wins."""
    result = route_model("html_tailwind", Llm.GEMINI_3_6_FLASH_MINIMAL)
    assert result == Llm.GEMINI_3_6_FLASH_MINIMAL


def test_route_html_tailwind_gets_high() -> None:
    assert route_model("html_tailwind") == Llm.GEMINI_3_6_FLASH_HIGH


def test_route_react_tailwind_gets_high() -> None:
    assert route_model("react_tailwind") == Llm.GEMINI_3_6_FLASH_HIGH


def test_route_bootstrap_gets_low() -> None:
    assert route_model("bootstrap") == Llm.GEMINI_3_6_FLASH_LOW


def test_route_android_compose_gets_minimal() -> None:
    assert route_model("android_compose") == Llm.GEMINI_3_6_FLASH_MINIMAL


def test_route_unknown_stack_gets_default() -> None:
    assert route_model("unknown_stack") == Llm.GEMINI_3_6_FLASH_HIGH


def test_all_defined_stacks_have_preferences() -> None:
    """Ensure every stack in STACK_MODEL_PREFERENCE maps to a valid Llm."""
    for stack, model in STACK_MODEL_PREFERENCE.items():
        assert isinstance(model, Llm), f"{stack} maps to non-Llm: {model}"


# --- metrics tests ---


def setup_method(self) -> None:
    reset_metrics()


def test_record_usage_increments_counters() -> None:
    """record_usage should increment all relevant counters."""
    reset_metrics()
    usage = TokenUsage(input=100, output=50, cache_read=20, total=170)
    pricing = ModelPricing(input=0.5, output=1.0, cache_read=0.1)
    record_usage(usage, "test-model", "html_tailwind", pricing)

    output = render_metrics()
    assert "ai_tokens_input_total" in output
    assert "model=\"test-model\"" in output
    assert "stack=\"html_tailwind\"" in output
    assert "100" in output  # input tokens
    assert "50" in output  # output tokens
    assert "20" in output  # cache_read tokens


def test_record_usage_without_pricing() -> None:
    """record_usage should work without pricing (skip cost counter)."""
    reset_metrics()
    usage = TokenUsage(input=10, output=5, cache_read=0, total=15)
    record_usage(usage, "no-cost-model", "bootstrap", None)

    output = render_metrics()
    assert "ai_tokens_input_total" in output
    assert "10" in output
    # cost counter should not have this model
    assert "no-cost-model" not in output.split("ai_cost_usd_total")[1].split("\n")[0]


def test_record_budget_sets_gauge() -> None:
    reset_metrics()
    record_budget(variant=0, spent=0.5, limit=1.0)

    output = render_metrics()
    assert "ai_budget_utilization" in output
    assert "variant=\"0\"" in output
    assert "0.5" in output


def test_record_circuit_breaker_sets_gauge() -> None:
    reset_metrics()
    record_circuit_breaker(is_open=True)

    output = render_metrics()
    assert "ai_circuit_breaker_open" in output
    assert "1" in output

    record_circuit_breaker(is_open=False)
    output = render_metrics()
    # Should show 0 (closed)
    lines = [l for l in output.split("\n") if "ai_circuit_breaker_open{" in l]
    assert len(lines) == 1
    assert lines[0].strip().endswith(" 0.0")


def test_render_metrics_format() -> None:
    """Output should be valid Prometheus text format."""
    reset_metrics()
    usage = TokenUsage(input=1, output=1, cache_read=0, total=2)
    record_usage(usage, "fmt-model", "html_tailwind")

    output = render_metrics()
    for metric_name in [
        "ai_tokens_input_total",
        "ai_tokens_output_total",
        "ai_tokens_cache_read_total",
        "ai_cost_usd_total",
        "ai_budget_utilization",
        "ai_prompt_cache_hit_rate",
        "ai_circuit_breaker_open",
    ]:
        assert f"# HELP {metric_name}" in output, f"Missing HELP for {metric_name}"
        assert f"# TYPE {metric_name}" in output, f"Missing TYPE for {metric_name}"


def test_cache_hit_rate_gauge() -> None:
    reset_metrics()
    usage = TokenUsage(input=100, cache_read=50, total=150)
    record_usage(usage, "cache-model", "html_tailwind", None)

    output = render_metrics()
    assert "ai_prompt_cache_hit_rate" in output
    # cache_hit_rate = cache_read / (input + cache_read + cache_write) * 100
    # = 50 / (100 + 50 + 0) * 100 = 33.33...
    assert "33.3" in output
