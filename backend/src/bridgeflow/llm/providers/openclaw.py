from __future__ import annotations

from bridgeflow.config import settings
from bridgeflow.llm.providers.openai_compatible import OpenAICompatibleProvider


class OpenClawProvider(OpenAICompatibleProvider):
    """OpenClaw.

    TODO: confirm the API shape. Same note as HermesProvider — if it is not
    OpenAI-compatible, override `complete()` in this class only.
    """

    name = "openclaw"

    def __init__(self) -> None:
        super().__init__(
            api_key=settings.openclaw_api_key,
            base_url=settings.openclaw_base_url,
            model=settings.openclaw_model,
        )
