from __future__ import annotations

import httpx
from pydantic import BaseModel

from bridgeflow.llm.base import Message, Response
from bridgeflow.llm.json_reply import parse_structured, schema_instruction


class OpenAICompatibleProvider:
    """Base for any backend exposing an OpenAI-style `/chat/completions` endpoint.

    Several of the backends we may end up using (DeepSeek and friends) speak this
    dialect, so the shared transport lives here and subclasses only supply credentials.

    Structured output is asked for in the prompt rather than through
    `response_format: json_schema`: DeepSeek rejects that type outright
    (`This response_format type is unavailable now`). `json_object` is accepted and
    guarantees parseable JSON, so the schema is stated in the system message and the
    reply is validated here.
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
        session_id: str | None = None,
    ) -> Response:
        instructions = system.strip()
        body: dict[str, object] = {"model": self._model}

        if schema is not None:
            instructions = f"{instructions}\n\n{schema_instruction(schema)}"
            body["response_format"] = {"type": "json_object"}

        body["messages"] = [{"role": "system", "content": instructions}] + [
            {"role": m.role, "content": m.content} for m in messages
        ]

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=body,
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]

        parsed = parse_structured(text, schema) if schema is not None else None
        return Response(text=text, parsed=parsed, provider=self.name, model=self._model)
