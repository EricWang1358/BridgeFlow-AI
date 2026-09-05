from __future__ import annotations

from functools import cache

from bridgeflow.config import settings
from bridgeflow.llm.base import LLMProvider


@cache
def get_provider(agent: str = "") -> LLMProvider:
    """Resolve the provider for an agent ("sanitizer", "resolver", "evaluator", ...).

    Falls back to the global LLM_PROVIDER. Imports are local so that a missing optional
    SDK for one backend never breaks the others.
    """
    name = settings.provider_for(agent) if agent else settings.llm_provider

    if name == "mock":
        from bridgeflow.llm.providers.mock import MockProvider

        return MockProvider()
    if name == "anthropic":
        from bridgeflow.llm.providers.anthropic import AnthropicProvider

        return AnthropicProvider()
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
