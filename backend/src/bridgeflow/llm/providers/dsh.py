from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from pydantic import BaseModel

from bridgeflow.config import settings
from bridgeflow.llm.base import Message, Response

_JSON_BLOCK = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


class DshProvider:
    """DeepSeek Harness (`dsh`) as the agent runtime behind our agents.

    The SDK drives a bundled `dsh` CLI as a subprocess over newline-delimited
    JSON-RPC on stdio. Starting that subprocess is expensive, so one harness is
    started lazily and reused for the life of the process.

    Two things the SDK is strict about, both reflected here:

    - `dsh_home` must be explicit. The SDK deliberately never discovers `~/.dsh`,
      so DSH_HOME is a required setting rather than something we guess.
    - `run()` is blocking. Our agents are async, so every call is handed to a
      worker thread; a lock keeps concurrent agents from interleaving turns on a
      single runtime.

    `run()` returns free text, not a typed object — unlike the Messages API there
    is no schema parameter — so structured output is requested in the prompt and
    validated here. A response that does not parse raises rather than being
    silently passed downstream as None.
    """

    name = "dsh"

    def __init__(self) -> None:
        if not settings.dsh_home:
            raise RuntimeError(
                "DSH_HOME is not set. The Harness SDK requires an explicit home "
                "directory and never falls back to ~/.dsh."
            )
        self._harness: Any = None
        self._lock = asyncio.Lock()

    def _ensure_started(self) -> Any:
        if self._harness is None:
            from deepseek_harness import DeepSeekHarness  # optional dependency

            kwargs: dict[str, Any] = {
                "dsh_home": settings.dsh_home,
                "profile": settings.dsh_profile,
                "provider": settings.dsh_provider,
                "model": settings.dsh_model,
            }
            if settings.dsh_cwd:
                kwargs["cwd"] = settings.dsh_cwd
            if settings.dsh_reasoning_effort:
                kwargs["reasoning_effort"] = settings.dsh_reasoning_effort
            if settings.dsh_max_tokens:
                kwargs["max_tokens"] = settings.dsh_max_tokens
            if settings.deepseek_api_key:
                kwargs["api_key"] = settings.deepseek_api_key
            if settings.deepseek_base_url:
                kwargs["base_url"] = settings.deepseek_base_url

            self._harness = DeepSeekHarness(**kwargs)
            self._harness.start()
        return self._harness

    async def complete(
        self,
        *,
        system: str,
        messages: list[Message],
        schema: type[BaseModel] | None = None,
        session_id: str | None = None,
    ) -> Response:
        prompt = _build_prompt(system, messages, schema)

        async with self._lock:
            harness = self._ensure_started()
            result = await asyncio.to_thread(harness.run, prompt, session_id=session_id)

        text = result.final_response or ""
        if result.finish_reason not in (None, "completed"):
            raise RuntimeError(
                f"dsh turn ended with finish_reason={result.finish_reason!r}; "
                f"response so far: {text[:200]!r}"
            )

        parsed = _parse(text, schema) if schema is not None else None
        return Response(
            text=text,
            parsed=parsed,
            provider=self.name,
            model=settings.dsh_model,
        )

    def close(self) -> None:
        if self._harness is not None:
            self._harness.close()
            self._harness = None


def _build_prompt(
    system: str, messages: list[Message], schema: type[BaseModel] | None
) -> str:
    """Fold system + turns into one prompt.

    `run()` takes a single input rather than a role-tagged message list, so the
    system instruction is stated first and the turns follow it.
    """
    parts = [system.strip()]
    for message in messages:
        label = "USER" if message.role == "user" else "ASSISTANT"
        parts.append(f"{label}:\n{message.content}")

    if schema is not None:
        parts.append(
            "Reply with JSON matching this schema and nothing else — no prose, "
            "no explanation outside the JSON:\n"
            + json.dumps(schema.model_json_schema(), ensure_ascii=False)
        )
    return "\n\n".join(parts)


def _parse(text: str, schema: type[BaseModel]) -> BaseModel:
    """Pull the JSON object out of a free-text reply and validate it."""
    candidate = text.strip()

    fenced = _JSON_BLOCK.search(candidate)
    if fenced:
        candidate = fenced.group(1).strip()
    else:
        # Fall back to the outermost braces, in case the model wrapped the JSON
        # in a sentence despite being told not to.
        start, end = candidate.find("{"), candidate.rfind("}")
        if start != -1 and end > start:
            candidate = candidate[start : end + 1]

    try:
        return schema.model_validate_json(candidate)
    except Exception as exc:  # surface the raw reply for debugging
        raise ValueError(
            f"dsh reply did not parse as {schema.__name__}: {exc}\nreply: {text[:500]!r}"
        ) from exc
