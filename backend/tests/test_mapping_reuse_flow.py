"""Approve through the host, then import again: the decision is reused, changed evidence re-asks (#82)."""
import pytest
from conftest import approved_post
from fastapi.testclient import TestClient
from test_business_mvp import CASES, upload

from bridgeflow.api.main import app
from bridgeflow.config import settings


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "field_dictionary_path", str(CASES / "dictionary.yaml"))
    with TestClient(app) as client:
        yield client


def open_questions(client, batch_id):
    return client.get(f"/batches/{batch_id}/view?section=mappings&limit=100").json()["rows"]


def test_an_approved_mapping_is_reused_by_the_next_import_until_its_facts_change(client):
    first = upload(client)
    questions = open_questions(client, first)
    if not questions:
        pytest.skip("the demo case produces no uncertain relationship to confirm")
    link = questions[0]
    key = (link["source"], link["target"], link["relation"])
    response = approved_post(client, {"source": link["source"], "target": link["target"], "relation": link["relation"],
                                      "accepted": True, "evidence": link["justification"], "period": "2025-11",
                                      "confirmed_by": "captain", "call_id": "c1"})
    assert response.status_code == 200, response.text

    second = upload(client)
    assert key not in {(q["source"], q["target"], q["relation"]) for q in open_questions(client, second)}

    stale = approved_post(client, {"source": link["source"], "target": link["target"], "relation": link["relation"],
                                   "accepted": True, "evidence": link["justification"] + " 2099-01 row 999",
                                   "period": "2025-11", "confirmed_by": "captain", "call_id": "c2"})
    assert stale.status_code == 200
    third = upload(client)
    reasked = [q for q in open_questions(client, third) if (q["source"], q["target"], q["relation"]) == key]
    assert reasked and "asked again" in reasked[0]["justification"]
