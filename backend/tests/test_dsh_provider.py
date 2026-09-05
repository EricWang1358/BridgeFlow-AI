"""Tests for the dsh adapter's local logic.

These do not start a runtime — they cover the parts that run on our side of the
JSON-RPC boundary, which is where the adapter can be wrong without any network.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from bridgeflow.llm.base import Message
from bridgeflow.llm.providers.dsh import _build_prompt, _parse


class _Verdict(BaseModel):
    confidence: float
    justification: str


def test_parses_a_fenced_json_block():
    reply = 'Here you go:\n```json\n{"confidence": 0.9, "justification": "same part"}\n```'
    assert _parse(reply, _Verdict).confidence == 0.9


def test_parses_bare_json():
    assert _parse('{"confidence": 0.4, "justification": "weak"}', _Verdict).confidence == 0.4


def test_parses_json_wrapped_in_prose():
    # The model was told not to do this, but it will anyway.
    reply = 'I think they match. {"confidence": 0.8, "justification": "alias"} Hope that helps.'
    assert _parse(reply, _Verdict).justification == "alias"


def test_unparseable_reply_raises_rather_than_returning_none():
    # A silent None here would reach the evaluator as "no findings", which reads
    # as "nothing is wrong" — the most dangerous possible failure mode.
    with pytest.raises(ValueError, match="did not parse"):
        _parse("I'd rather not answer that.", _Verdict)


def test_schema_violation_raises():
    with pytest.raises(ValueError, match="did not parse"):
        _parse('{"confidence": "very high"}', _Verdict)


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
