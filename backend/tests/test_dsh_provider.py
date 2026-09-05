"""Tests for the dsh adapter's local logic.

These do not start a runtime — they cover the parts that run on our side of the
JSON-RPC boundary, which is where the adapter can be wrong without any network.

Reading a structured answer out of a reply is no longer dsh's own concern: every
backend states the schema in the prompt, so the parser is shared and its tests live
in `test_json_reply.py`.
"""

from __future__ import annotations

from pydantic import BaseModel

from bridgeflow.llm.base import Message
from bridgeflow.llm.providers.dsh import _build_prompt


class _Verdict(BaseModel):
    confidence: float
    justification: str


def test_prompt_includes_system_turns_and_schema():
    prompt = _build_prompt(
        "You adjudicate entity links.",
        [Message(role="user", content="SKU-A1 vs sku a1?")],
        _Verdict,
    )
    assert prompt.startswith("You adjudicate entity links.")
    assert "USER:\nSKU-A1 vs sku a1?" in prompt
    assert "confidence" in prompt, "the schema must reach the model"


def test_prompt_without_schema_asks_for_no_json():
    prompt = _build_prompt("Be brief.", [Message(role="user", content="hi")], None)
    assert "JSON" not in prompt
