"""Tests for reading a structured answer out of a free-text model reply.

Every backend we use states the schema in the prompt rather than enforcing it on
the wire, so the ways a model can wrap its answer are shared, and so is the parser.
"""

from __future__ import annotations

import json

import pytest
from pydantic import BaseModel

from bridgeflow.llm.json_reply import parse_structured, schema_instruction


class _Adjudication(BaseModel):
    confidence: float
    justification: str


def test_plain_object():
    parsed = parse_structured('{"confidence": 0.9, "justification": "row 2"}', _Adjudication)

    assert parsed.confidence == 0.9


def test_code_fence_is_stripped():
    reply = 'Sure:\n```json\n{"confidence": 0.5, "justification": "weak"}\n```\n'

    assert parse_structured(reply, _Adjudication).justification == "weak"


def test_prose_around_the_object_is_ignored():
    reply = 'I think: {"confidence": 0.1, "justification": "no"} — hope that helps.'

    assert parse_structured(reply, _Adjudication).confidence == 0.1


def test_schema_envelope_is_unwrapped():
    """The failure that closed issue #33.

    Handed the schema in the prompt, the model sometimes fills the schema in and
    returns that, rather than returning the object the schema describes.
    """
    reply = json.dumps(
        {
            "properties": {"confidence": 0.4, "justification": "a single co-occurrence"},
            "title": "_Adjudication",
            "type": "object",
        }
    )

    parsed = parse_structured(reply, _Adjudication)

    assert parsed.confidence == 0.4
    assert parsed.justification == "a single co-occurrence"


def test_a_real_properties_field_is_not_mistaken_for_an_envelope():
    """Unwrapping keys on the schema vocabulary alone would corrupt this reply."""

    class _Holder(BaseModel):
        properties: dict
        confidence: float

    reply = '{"properties": {"colour": "red"}, "confidence": 0.8}'

    assert parse_structured(reply, _Holder).properties == {"colour": "red"}


def test_unparseable_reply_names_the_schema_and_shows_the_reply():
    with pytest.raises(ValueError, match="_Adjudication"):
        parse_structured("I would rather not.", _Adjudication)


def test_instruction_tells_the_model_not_to_echo_the_schema():
    instruction = schema_instruction(_Adjudication)

    assert "confidence" in instruction, "the schema itself must be in the prompt"
    assert "not a copy of the schema" in instruction
