"""Offline tests never inherit a developer's paid providers or private data."""
import hashlib
import hmac
import json
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from bridgeflow.config import REPO_ROOT, settings
from bridgeflow.llm import get_provider

TEST_SECRET = "bridgeflow-test-host-secret-32-characters"


def receipt(body: bytes) -> str:
    stamp, nonce = str(int(time.time())), uuid.uuid4().hex
    message = f"{stamp}.{nonce}.{hashlib.sha256(body).hexdigest()}"
    signature = hmac.new(TEST_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()
    return f"{stamp}.{nonce}.{signature}"


def approved_post(client, payload):
    body = json.dumps(payload, separators=(",", ":")).encode()
    return client.post("/tools/confirm-mapping", content=body, headers={
        "content-type": "application/json", "x-bridgeflow-approval": receipt(body),
    })


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch, tmp_path):
    for name in ("llm_provider", "llm_provider_sanitizer", "llm_provider_resolver", "llm_provider_evaluator",
                 "llm_provider_dictionary_drafter"):
        monkeypatch.setattr(settings, name, "mock")
    monkeypatch.setattr(settings, "field_dictionary_path", str(REPO_ROOT / "data/mappings/field-dictionary.example.yaml"))
    monkeypatch.setattr(settings, "integration_spec_path", str(REPO_ROOT / "data/company_templates/integration.yaml"))
    monkeypatch.setattr(settings, "result_store_path", str(tmp_path / "outputs"))
    monkeypatch.setattr(settings, "mapping_memory_path", str(tmp_path / "mappings.json"))
    monkeypatch.setattr(settings, "column_match_path", str(tmp_path / "column-matches.json"))
    monkeypatch.setattr(settings, "dictionary_draft_path", str(tmp_path / "dictionary-drafts"))
    monkeypatch.setattr(settings, "bridgeflow_service_token", TEST_SECRET)
    # Existing sample/console tests opt into their compatibility path here. The new
    # enterprise tests explicitly restore production flags and exercise refusals.
    monkeypatch.setattr(settings, "bridgeflow_allow_sample_data", True)
    monkeypatch.setattr(settings, "bridgeflow_enable_legacy_console", True)
    original = TestClient.__init__
    def init(client, *args, **kwargs):
        kwargs.setdefault("headers", {"authorization": f"Bearer {TEST_SECRET}"})
        original(client, *args, **kwargs)
    monkeypatch.setattr(TestClient, "__init__", init)
    get_provider.cache_clear()
    yield
    get_provider.cache_clear()
