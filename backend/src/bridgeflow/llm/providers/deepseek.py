from __future__ import annotations

from bridgeflow.config import settings
from bridgeflow.llm.providers.openai_compatible import OpenAICompatibleProvider

# Verified against the live API on 2026-09-06: GET /models returns
# deepseek-v4-flash, deepseek-v4-pro and deepseek-v4-flash-vision-exp.
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-flash"


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek's own chat-completions endpoint, called directly.

    This is the provider for work that is a single completion — deciding whether two
    identifiers are related, say. Such calls need no tools, no planning and no
    approval, so routing them through the dsh agent runtime buys nothing and costs a
    great deal: see issue #25, where one adjudication ran twelve `bash` steps over
    the repository and fed 7k tokens of file contents back to the model.

    The defaults live here rather than in `settings` because `deepseek_base_url` is
    also handed to dsh, which treats an explicitly set base URL as an override.
    """

    name = "deepseek"

    def __init__(self) -> None:
        super().__init__(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url or DEFAULT_BASE_URL,
            model=settings.deepseek_model or DEFAULT_MODEL,
        )
