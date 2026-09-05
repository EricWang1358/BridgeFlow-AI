from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel

_JSON_BLOCK = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)

_SCHEMA_KEYS = {"properties", "type", "title", "required", "$schema", "definitions"}


def schema_instruction(schema: type[BaseModel]) -> str:
    """The prompt fragment that asks for `schema`-shaped JSON.

    Backends that cannot enforce a schema on the wire get it stated here instead.
    """
    return (
        "Reply with JSON matching this schema and nothing else — no prose, no "
        "explanation outside the JSON. Return the described object itself, not a "
        "copy of the schema:\n" + json.dumps(schema.model_json_schema(), ensure_ascii=False)
    )


def parse_structured(text: str, schema: type[BaseModel]) -> BaseModel:
    """Pull the JSON object out of a reply and validate it against `schema`.

    Handles the three ways a model wraps its answer instead of stating it: a code
    fence, a sentence around the object, and — because we hand the schema over in
    the prompt — the schema envelope itself, with the answer sitting under
    `properties`.
    """
    candidate = text.strip()

    fenced = _JSON_BLOCK.search(candidate)
    if fenced:
        candidate = fenced.group(1).strip()
    else:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start != -1 and end > start:
            candidate = candidate[start : end + 1]

    try:
        payload: Any = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"reply did not parse as {schema.__name__}: {exc}\nreply: {text[:500]!r}"
        ) from exc

    payload = _unwrap_schema_envelope(payload)

    try:
        return schema.model_validate(payload)
    except Exception as exc:  # surface the raw reply for debugging
        raise ValueError(
            f"reply did not parse as {schema.__name__}: {exc}\nreply: {text[:500]!r}"
        ) from exc


def _unwrap_schema_envelope(payload: Any) -> Any:
    """Return the answer when the model echoed the schema shape around it.

    A reply like `{"properties": {...}, "title": "_Adjudication", "type": "object"}`
    is the schema we sent with the values filled in, not the object we asked for.
    It is recognisable because every key belongs to JSON Schema itself.
    """
    if (
        isinstance(payload, dict)
        and isinstance(payload.get("properties"), dict)
        and set(payload) <= _SCHEMA_KEYS
    ):
        return payload["properties"]
    return payload
