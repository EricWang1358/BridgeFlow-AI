from __future__ import annotations

import json

import httpx
from pydantic import BaseModel

from bridgeflow.llm.base import Message, Response


class OpenAICompatibleProvider:
    """Base for any backend exposing an OpenAI-style `/chat/completions` endpoint.

    Several of the backends we may end up using (DeepSeek and friends) speak this
    dialect, so the shared transport lives here and subclasses only supply credentials.
    """

    name = "openai-compatible"

    def __init__(self, *, api_key: str, base_url: str, model: str) -> None:
        if not base_url:
            raise RuntimeError(f"{self.name}: base URL is not configured")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def complete(
        self,
        *,
        system: str,
        messages: list[Message],
        schema: type[BaseModel] | None = None,
    ) -> Response:
        body: dict[str, object] = {
            "model": self._model,
            "messages": [{"role": "system", "content": system}]
            + [{"role": m.role, "content": m.content} for m in messages],
        }
        if schema is not None:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()},
            }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=body,
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]

        parsed = schema.model_validate(json.loads(text)) if schema is not None else None
        return Response(text=text, parsed=parsed, provider=self.name, model=self._model)
