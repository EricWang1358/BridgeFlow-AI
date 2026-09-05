from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel

from bridgeflow.llm.base import Message, Response


class MockProvider:
    """Deterministic, offline, no API key. The demo must always run on this.

    It returns a stable value derived from the prompt hash, and when a schema is
    requested it constructs a minimal valid instance so downstream code exercises the
    real code path rather than a special case.
    """

    name = "mock"

    async def complete(
        self,
        *,
        system: str,
        messages: list[Message],
        schema: type[BaseModel] | None = None,
    ) -> Response:
        seed = hashlib.sha256(
            (system + "".join(m.content for m in messages)).encode()
        ).hexdigest()

        if schema is None:
            return Response(text=f"mock:{seed[:12]}", provider=self.name, model="mock")

        instance = _minimal_instance(schema, seed)
        return Response(
            text=instance.model_dump_json(),
            parsed=instance,
            provider=self.name,
            model="mock",
        )


def _minimal_instance(schema: type[BaseModel], seed: str) -> BaseModel:
    """Build the smallest instance of `schema` that passes validation."""
    values: dict[str, object] = {}
    for name, field in schema.model_fields.items():
        if not field.is_required():
            continue
        values[name] = _placeholder(field.annotation, seed, name)
    return schema.model_validate(values)


def _placeholder(annotation: object, seed: str, field_name: str) -> object:
    origin = getattr(annotation, "__origin__", None)
    if origin is list:
        return []
    if annotation is int:
        return int(seed[:4], 16) % 100
    if annotation is float:
        return (int(seed[:4], 16) % 1000) / 1000
    if annotation is bool:
        return True
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return _minimal_instance(annotation, seed)
    return f"mock-{field_name}-{seed[:6]}"


def dumps(obj: object) -> str:
    return json.dumps(obj, default=str, ensure_ascii=False)
