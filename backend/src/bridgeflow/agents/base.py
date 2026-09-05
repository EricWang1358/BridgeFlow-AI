from __future__ import annotations

import abc
from typing import Generic, TypeVar

from bridgeflow.llm import LLMProvider, get_provider

In_ = TypeVar("In_")
Out = TypeVar("Out")


class Agent(abc.ABC, Generic[In_, Out]):
    """One stage of the pipeline.

    Subclasses declare a `slug` (used to pick a per-agent LLM provider) and implement
    `run`. They must never construct a provider themselves — always `self.llm`.
    """

    slug: str = ""
    system_prompt: str = ""

    def __init__(self, llm: LLMProvider | None = None) -> None:
        self._llm = llm

    @property
    def llm(self) -> LLMProvider:
        if self._llm is None:
            self._llm = get_provider(self.slug)
        return self._llm

    @abc.abstractmethod
    async def run(self, payload: In_) -> Out: ...
