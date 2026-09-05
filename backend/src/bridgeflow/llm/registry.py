from __future__ import annotations

from functools import cache

from bridgeflow.config import settings
from bridgeflow.llm.base import LLMProvider


@cache
def get_provider(agent: str = "", lane: str = "") -> LLMProvider:
    """Resolve the provider for an agent ("sanitizer", "resolver", "evaluator", ...).

    Falls back to the global LLM_PROVIDER. Imports are local so that a missing optional
    SDK for one backend never breaks the others.

    `lane` separates callers that must not queue behind each other. A dsh provider
    serialises its calls behind a lock, because one runtime cannot interleave turns —
    so four role agents sharing one provider ran one at a time no matter how they were
    launched, and `asyncio.gather` in the evaluator bought nothing (#51). Giving each
    role its own lane gives it its own runtime.

    Lanes cost a subprocess each, so use one only where concurrency is the point.
    """
    name = settings.provider_for(agent) if agent else settings.llm_provider

    if name == "mock":
        from bridgeflow.llm.providers.mock import MockProvider

        return MockProvider()
    if name == "anthropic":
        from bridgeflow.llm.providers.anthropic import AnthropicProvider

        return AnthropicProvider()
    if name == "dsh":
        from bridgeflow.llm.providers.dsh import DshProvider

        return DshProvider()
    if name == "deepseek":
        from bridgeflow.llm.providers.deepseek import DeepSeekProvider

        return DeepSeekProvider()
    if name == "hermes":
        from bridgeflow.llm.providers.hermes import HermesProvider

        return HermesProvider()
    if name == "openclaw":
        from bridgeflow.llm.providers.openclaw import OpenClawProvider

        return OpenClawProvider()

    raise ValueError(f"unknown LLM provider {name!r}")
