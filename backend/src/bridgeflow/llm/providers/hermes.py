from __future__ import annotations

from bridgeflow.config import settings
from bridgeflow.llm.providers.openai_compatible import OpenAICompatibleProvider


class HermesProvider(OpenAICompatibleProvider):
    """Hermes.

    TODO: confirm whether this backend speaks the OpenAI dialect. If it does, this
    class needs no further work — just fill in HERMES_BASE_URL / HERMES_MODEL. If it
    does not, override `complete()` here; nothing outside this file needs to change.
    """

    name = "hermes"

    def __init__(self) -> None:
        super().__init__(
            api_key=settings.hermes_api_key,
            base_url=settings.hermes_base_url,
            model=settings.hermes_model,
        )
