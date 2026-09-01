"""火山引擎 Ark 已开通模型清单与 Token 额度。

数据来源：火山引擎控制台 2026-08-31 实测。
此文件作为持久化记录，记录所有已开通模型的额度、定价、endpoint ID 和 API 可用性。

控制台 "已开通" ≠ API 可用。需要为每个模型创建推理接入点 (endpoint) 才能调用。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class VolcanoModel:
    """火山引擎 Ark 模型信息。"""

    # 模型显示名（控制台名称）
    name: str
    # 提供方
    provider: str
    # 是否已开通（控制台）
    activated: bool
    # 推理接入点 ID（API 调用时使用的 model 参数）
    # None = 未创建 endpoint，API 不可用
    endpoint_id: Optional[str] = None
    # API 是否可用（实测）
    api_available: bool = False
    # 是否支持视觉（图片输入）
    vision_capable: bool = False
    # 总额度（tokens）
    total_quota: int = 0
    # 剩余额度（tokens）
    remaining_quota: int = 0
    # 输入定价（元/千tokens）
    input_price: float = 0.0
    # 输出定价（元/千tokens）
    output_price: float = 0.0
    # 缓存命中定价（元/千tokens）
    cache_price: float = 0.0
    # 限流 RPM
    rpm: int = 0
    # 限流 TPM
    tpm: int = 0
    # 备注
    note: str = ""


# === 所有已开通模型（控制台数据 2026-08-31）===
VOLCANO_MODELS: List[VolcanoModel] = [
    # --- 可用模型（endpoint 已创建 + API 实测通过）---
    VolcanoModel(
        name="doubao-seed-evolving",
        provider="字节跳动",
        activated=True,
        endpoint_id="doubao-seed-evolving",
        api_available=True,
        vision_capable=True,
        total_quota=11543928,
        remaining_quota=250883,
        input_price=0.006,
        output_price=0.030,
        cache_price=0.00120,
        rpm=500,
        tpm=1000000,
        note="08.27 升级最新版本，视觉多模态确认可用",
    ),
    VolcanoModel(
        name="doubao-seed-2.1-turbo",
        provider="字节跳动",
        activated=True,
        endpoint_id="doubao-seed-2-1-turbo-260628",
        api_available=True,
        vision_capable=True,
        total_quota=500000,
        remaining_quota=270311,
        input_price=0.003,
        output_price=0.015,
        cache_price=0.00060,
        rpm=500,
        tpm=1000000,
        note="中端视觉模型，性价比好",
    ),

    # --- 已开通但 endpoint 未创建 / API 不可用 ---
    VolcanoModel(
        name="doubao-seed-1.8",
        provider="字节跳动",
        activated=True,
        endpoint_id=None,  # doubao-seed-1-8-251228 → 404
        api_available=False,
        vision_capable=True,  # 控制台标注视觉
        total_quota=500000,
        remaining_quota=500000,
        input_price=0.0008,
        output_price=0.0020,
        cache_price=0.00016,
        rpm=30000,
        tpm=5000000,
        note="性价比最优，但 endpoint 404 需重新创建",
    ),
    VolcanoModel(
        name="doubao-seed-1.6-vision",
        provider="字节跳动",
        activated=True,
        endpoint_id=None,  # doubao-seed-1-6-vision-250815 → 404
        api_available=False,
        vision_capable=True,
        total_quota=500000,
        remaining_quota=500000,
        input_price=0.0008,
        output_price=0.0080,
        cache_price=0.00016,
        rpm=30000,
        tpm=5000000,
        note="GUI Agent 专用视觉模型，endpoint 404",
    ),
    VolcanoModel(
        name="doubao-seed-1.6-flash",
        provider="字节跳动",
        activated=True,
        endpoint_id=None,  # doubao-seed-1-6-flash-250828 → 404
        api_available=False,
        vision_capable=True,
        total_quota=500000,
        remaining_quota=500000,
        input_price=0.00015,
        output_price=0.0015,
        cache_price=0.00003,
        rpm=30000,
        tpm=5000000,
        note="最便宜模型（¥0.15/M），endpoint 404 需重新创建",
    ),
    VolcanoModel(
        name="doubao-seed-2.0-mini",
        provider="字节跳动",
        activated=True,
        endpoint_id=None,
        api_available=False,
        vision_capable=True,
        total_quota=500000,
        remaining_quota=0,
        input_price=0.0002,
        output_price=0.0020,
        cache_price=0.00004,
        rpm=30000,
        tpm=5000000,
        note="全模态含音频，额度已用完",
    ),
    VolcanoModel(
        name="doubao-seed-2.0-lite",
        provider="字节跳动",
        activated=True,
        endpoint_id=None,
        api_available=False,
        vision_capable=True,
        total_quota=500000,
        remaining_quota=0,
        input_price=0.0006,
        output_price=0.0036,
        cache_price=0.00012,
        rpm=30000,
        tpm=5000000,
        note="全模态含音频，额度已用完",
    ),
    VolcanoModel(
        name="doubao-seed-2.0-code",
        provider="字节跳动",
        activated=True,
        endpoint_id=None,
        api_available=False,
        vision_capable=False,
        total_quota=500000,
        remaining_quota=0,
        input_price=0.0032,
        output_price=0.0160,
        cache_price=0.00064,
        rpm=30000,
        tpm=5000000,
        note="编程增强，额度已用完",
    ),
    VolcanoModel(
        name="doubao-seed-2.0-pro",
        provider="字节跳动",
        activated=True,
        endpoint_id=None,
        api_available=False,
        vision_capable=True,
        total_quota=500000,
        remaining_quota=0,
        input_price=0.0032,
        output_price=0.0160,
        cache_price=0.00064,
        rpm=30000,
        tpm=5000000,
        note="旗舰模型，额度已用完",
    ),
    VolcanoModel(
        name="doubao-seed-character",
        provider="字节跳动",
        activated=True,
        endpoint_id=None,
        api_available=False,
        vision_capable=False,
        total_quota=500000,
        remaining_quota=500000,
        input_price=0.0008,
        output_price=0.0020,
        cache_price=0.00016,
        rpm=30000,
        tpm=5000000,
        note="角色扮演模型",
    ),
    VolcanoModel(
        name="doubao-seed-code",
        provider="字节跳动",
        activated=True,
        endpoint_id=None,
        api_available=False,
        vision_capable=False,
        total_quota=500000,
        remaining_quota=500000,
        input_price=0.0012,
        output_price=0.0080,
        cache_price=0.00024,
        rpm=5000,
        tpm=1200000,
        note="代码模型",
    ),
    VolcanoModel(
        name="doubao-seed-translation",
        provider="字节跳动",
        activated=True,
        endpoint_id=None,
        api_available=False,
        vision_capable=False,
        total_quota=500000,
        remaining_quota=500000,
        input_price=0.0012,
        output_price=0.0036,
        cache_price=0.0,
        rpm=5000,
        tpm=500000,
        note="翻译模型",
    ),
    VolcanoModel(
        name="doubao-1.5-vision-lite",
        provider="字节跳动",
        activated=True,
        endpoint_id=None,
        api_available=False,
        vision_capable=True,
        total_quota=500000,
        remaining_quota=500000,
        input_price=0.0015,
        output_price=0.0045,
        cache_price=0.0,
        rpm=30000,
        tpm=5000000,
        note="轻量视觉模型",
    ),
    VolcanoModel(
        name="doubao-pro-32k",
        provider="字节跳动",
        activated=True,
        endpoint_id=None,
        api_available=False,
        vision_capable=False,
        total_quota=500000,
        remaining_quota=500000,
        input_price=0.0008,
        output_price=0.0020,
        cache_price=0.00016,
        rpm=15000,
        tpm=1200000,
        note="通用模型 32k 上下文",
    ),
    VolcanoModel(
        name="doubao-lite-4k",
        provider="字节跳动",
        activated=True,
        endpoint_id=None,
        api_available=False,
        vision_capable=False,
        total_quota=500000,
        remaining_quota=500000,
        input_price=0.0003,
        output_price=0.0006,
        cache_price=0.0,
        rpm=10000,
        tpm=800000,
        note="轻量模型 4k 上下文",
    ),
    VolcanoModel(
        name="doubao-lite-32k",
        provider="字节跳动",
        activated=True,
        endpoint_id=None,
        api_available=False,
        vision_capable=False,
        total_quota=500000,
        remaining_quota=500000,
        input_price=0.0003,
        output_price=0.0006,
        cache_price=0.00006,
        rpm=15000,
        tpm=1200000,
        note="轻量模型 32k 上下文",
    ),
    # --- 其他提供方 ---
    VolcanoModel(
        name="glm-5.2",
        provider="智谱AI",
        activated=True,
        endpoint_id=None,
        api_available=False,
        vision_capable=True,
        total_quota=500000,
        remaining_quota=500000,
        input_price=0.008,
        output_price=0.028,
        cache_price=0.00200,
        rpm=500,
        tpm=1000000,
        note="智谱 GLM-5.2，endpoint 未创建",
    ),
    VolcanoModel(
        name="deepseek-v4-pro",
        provider="DeepSeek",
        activated=True,
        endpoint_id=None,
        api_available=False,
        vision_capable=False,
        total_quota=500000,
        remaining_quota=223965,
        input_price=0.009,
        output_price=0.027,
        cache_price=0.00030,
        rpm=15000,
        tpm=1500000,
        note="DeepSeek V4 Pro，纯文本",
    ),
]


# === 便捷查询 ===

def get_available_models() -> List[VolcanoModel]:
    """返回 API 可用的模型。"""
    return [m for m in VOLCANO_MODELS if m.api_available]


def get_vision_models() -> List[VolcanoModel]:
    """返回支持视觉的模型（已开通且标注视觉能力）。"""
    return [m for m in VOLCANO_MODELS if m.vision_capable and m.activated]


def get_available_vision_models() -> List[VolcanoModel]:
    """返回 API 可用且支持视觉的模型。"""
    return [m for m in VOLCANO_MODELS if m.api_available and m.vision_capable]


def get_total_remaining_tokens() -> int:
    """所有已开通模型的剩余 token 总量。"""
    return sum(m.remaining_quota for m in VOLCANO_MODELS if m.activated)


def get_available_remaining_tokens() -> int:
    """API 可用模型的剩余 token 总量。"""
    return sum(m.remaining_quota for m in VOLCANO_MODELS if m.api_available)


def get_model_summary() -> Dict[str, dict]:
    """返回所有模型的摘要字典。"""
    return {
        m.name: {
            "provider": m.provider,
            "activated": m.activated,
            "endpoint_id": m.endpoint_id,
            "api_available": m.api_available,
            "vision_capable": m.vision_capable,
            "total_quota": m.total_quota,
            "remaining_quota": m.remaining_quota,
            "input_price": m.input_price,
            "output_price": m.output_price,
            "note": m.note,
        }
        for m in VOLCANO_MODELS
    }
