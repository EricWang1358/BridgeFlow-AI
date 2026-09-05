from __future__ import annotations

from bridgeflow.config import settings
from bridgeflow.llm.providers.openai_compatible import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek — OpenAI-compatible chat completions.

    TODO: confirm the exact endpoint and model id for the "deepseek harness" setup
    suggested by the course. Set DEEPSEEK_BASE_URL / DEEPSEEK_MODEL in .env.
    """

    name = "deepseek"

    def __init__(self) -> None:
        super().__init__(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
        )
