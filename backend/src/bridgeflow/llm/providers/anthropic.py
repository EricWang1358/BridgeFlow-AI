from __future__ import annotations

from pydantic import BaseModel

from bridgeflow.config import settings
from bridgeflow.llm.base import Message, Response


class AnthropicProvider:
    """Claude via the official `anthropic` SDK.

    Install with the optional extra: `pip install -e ".[anthropic]"`.
    """

    name = "anthropic"

    def __init__(self) -> None:
        from anthropic import AsyncAnthropic  # imported lazily — optional dependency

        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.anthropic_model

    async def complete(
        self,
        *,
        system: str,
        messages: list[Message],
        schema: type[BaseModel] | None = None,
    ) -> Response:
        payload = [{"role": m.role, "content": m.content} for m in messages]

        if schema is not None:
            # `parse` validates the response against the schema for us.
            result = await self._client.messages.parse(
                model=self._model,
                max_tokens=16000,
                system=system,
                messages=payload,
                output_config={"format": schema},
            )
            parsed = result.parsed_output
            return Response(
                text=parsed.model_dump_json() if parsed else "",
                parsed=parsed,
                provider=self.name,
                model=self._model,
            )

        result = await self._client.messages.create(
            model=self._model,
            max_tokens=16000,
            system=system,
            messages=payload,
        )
        text = "".join(b.text for b in result.content if b.type == "text")
        return Response(text=text, provider=self.name, model=self._model)
