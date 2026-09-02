from dataclasses import dataclass
from typing import Dict


@dataclass
class ModelPricing:
    """Per-million-token pricing in USD."""

    input: float = 0.0
    output: float = 0.0
    cache_read: float = 0.0
    cache_write: float = 0.0


# Pricing keyed by the API model name string sent to the provider.
MODEL_PRICING: Dict[str, ModelPricing] = {
    # --- OpenAI ---
    # Verified against developers.openai.com/api/docs/pricing on 2026-07-24.
    "gpt-5.4-mini": ModelPricing(
        input=0.75, output=4.50, cache_read=0.075
    ),
    "gpt-5.4-2026-03-05": ModelPricing(
        input=2.50, output=15.00, cache_read=0.25
    ),
    "gpt-5.5": ModelPricing(
        input=5.00, output=30.00, cache_read=0.50
    ),
    "gpt-5.6-sol": ModelPricing(
        input=5.00, output=30.00, cache_read=0.50
    ),
    "gpt-5.6-terra": ModelPricing(
        input=2.50, output=15.00, cache_read=0.25
    ),
    # --- Anthropic ---
    # Verified against platform.claude.com/docs/en/about-claude/pricing on
    # 2026-07-24. cache_write is the 5-minute cache-write rate (1.25x input).
    "claude-sonnet-4-6": ModelPricing(
        input=3.00, output=15.00, cache_read=0.30, cache_write=3.75
    ),
    "claude-opus-5": ModelPricing(
        input=5.00, output=25.00, cache_read=0.50, cache_write=6.25
    ),
    "claude-opus-4-8": ModelPricing(
        input=5.00, output=25.00, cache_read=0.50, cache_write=6.25
    ),
    "claude-fable-5": ModelPricing(
        input=10.00, output=50.00, cache_read=1.00, cache_write=12.50
    ),
    # --- Gemini ---
    # Verified against ai.google.dev/gemini-api/docs/pricing on 2026-07-24.
    # Pro models bill higher rates for prompts >200k tokens ($4/$18 for 3.1
    # Pro); this flat table uses the <=200k tier, so long-context costs are
    # underestimated.
    "gemini-3-flash-preview": ModelPricing(
        input=0.50, output=3.00, cache_read=0.05
    ),
    "gemini-3-pro-preview": ModelPricing(
        input=2.00, output=12.00, cache_read=0.20
    ),
    "gemini-3.1-pro-preview": ModelPricing(
        input=2.00, output=12.00, cache_read=0.20
    ),
    "gemini-3.5-flash": ModelPricing(
        input=1.50, output=9.00, cache_read=0.15
    ),
    "gemini-3.6-flash": ModelPricing(
        input=1.50, output=7.50, cache_read=0.15
    ),
    # --- Doubao (Volcano Engine Ark) ---
    # Verified against Volcano Engine console on 2026-08-31.
    # CNY per million tokens → USD/M at 7.2 CNY/USD.
    "doubao-seed-evolving": ModelPricing(
        input=0.833, output=4.167, cache_read=0.167
    ),
    "doubao-seed-1.6-flash": ModelPricing(
        input=0.021, output=0.208, cache_read=0.004
    ),
    "doubao-seed-1.8": ModelPricing(
        input=0.111, output=0.278, cache_read=0.022
    ),
    "doubao-seed-1.6-vision": ModelPricing(
        input=0.111, output=1.111, cache_read=0.022
    ),
    # --- Qwen (via DashScope Anthropic-compatible endpoint) ---
    # Verified against help.aliyun.com/zh/model-studio/qwen3-7-max on
    # 2026-08-31. CNY per million tokens → USD/M at 7.2 CNY/USD.
    "qwen3.7-max": ModelPricing(
        input=1.667, output=5.0, cache_read=0.333, cache_write=2.083
    ),
}
