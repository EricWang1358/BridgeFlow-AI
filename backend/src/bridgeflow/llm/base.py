from __future__ import annotations

from typing import Any, Literal, Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class Response(BaseModel):
    text: str
    parsed: Any = None
    provider: str = ""
    model: str = ""


class LLMProvider(Protocol):
    """The only surface agents are allowed to touch.

    Adding a backend means writing one of these — no agent code changes.
    """

    name: str

    async def complete(
        self,
        *,
        system: str,
        messages: list[Message],
        schema: type[BaseModel] | None = None,
    ) -> Response:
        """Run a completion. If `schema` is given, `Response.parsed` is an instance of it."""
        ...
