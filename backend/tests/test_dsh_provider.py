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


def test_sdk_explicitly_uses_the_same_native_installation_as_web(monkeypatch, tmp_path):
    """Omitting dsh_bin silently boots pkg and corrupts the live Web fallback."""
    from unittest.mock import Mock

    import deepseek_harness

    from bridgeflow.llm.providers import dsh

    factory = Mock()
    monkeypatch.setattr(deepseek_harness, "DeepSeekHarness", factory)
    monkeypatch.setattr(dsh.settings, "dsh_home", str(tmp_path))
    monkeypatch.setattr(dsh, "native_command", lambda: "/installed/npm/dsh/lib/bin.js")
    provider = dsh.DshProvider()
    provider._ensure_started()
    assert factory.call_args.kwargs["dsh_bin"] == "/installed/npm/dsh/lib/bin.js"
    assert factory.call_args.kwargs["dsh_home"] == str(tmp_path)
    factory.return_value.start.assert_called_once()
    provider.close()
