"""The demo cases (data/mock_business/cases/cases.yaml) each show what they promise.

One batch cannot show every state, so each case is pinned to the states it exists for:
the core case shows several kinds of open item at once, the other case shows different
ones and none of the core's, and the clean case is ready with nothing open and every
metric inside its threshold.
"""
import pytest

from bridgeflow.config import REPO_ROOT, settings


@pytest.fixture
def client(monkeypatch):
    from fastapi.testclient import TestClient

    from bridgeflow.api.main import app
    monkeypatch.setattr(settings, "field_dictionary_path", str(REPO_ROOT / "data/mock_business/demo/dictionary.yaml"))
    return TestClient(app)


def load(client, case):
    batch = client.post(f"/batches/demo?case={case}")
    assert batch.status_code == 200, batch.text
    body = batch.json()
    master = client.get(f"/integration/batches/{body['batch_id']}").json()
    context = client.post("/tools/review-context", json={"batch_id": body["batch_id"]})
    return body, {issue["kind"] for issue in master["issues"]}, context


def test_the_case_list_names_every_case(client):
    cases = client.get("/batches/demo/cases").json()["cases"]
    assert [c["id"] for c in cases] == ["tour", "core", "other", "clean"]
    assert all(len(c["title"]) == 2 and len(c["summary"]) == 2 for c in cases)


def test_the_core_case_shows_many_problems_at_once(client):
    batch, kinds, context = load(client, "core")
    assert batch["status"] == "needs_review"
    assert sum(d["quarantined"] for d in batch["departments"]) >= 1  # text in a money field
    assert {"missing_department", "cannot_compute", "invalid_number"} <= kinds
    assert context.status_code == 409  # held back until the rows are settled


def test_the_other_case_shows_different_problems_named_where_they_are(client):
    batch, kinds, context = load(client, "other")
    assert batch["status"] == "needs_review"
    assert sum(d["quarantined"] for d in batch["departments"]) == 0  # none of the core's problems
    blockers = " | ".join(batch["review_blockers"])
    assert "生产量 violates the declared nonnegative convention" in blockers
    assert "outside the requested period" in blockers
    assert "marketing: 累计收款 is missing or unreadable" in blockers
    assert "missing_column" in kinds
    assert batch["column_questions"] == 1  # the renamed column, not every undeclared header
    # The status never promises a review that would then be refused.
    assert context.status_code == 409 and context.json()["detail"] in batch["review_blockers"]


def test_the_clean_case_is_ready_with_nothing_open(client):
    batch, kinds, context = load(client, "clean")
    assert batch["status"] == "ready" and batch["review_blockers"] == [] and kinds == set()
    assert batch["column_questions"] == 0
    checks = [c for role in context.json()["roles"] for c in role["checks"]]
    assert len(checks) == 10 and all(c["expected_status"] == "ok" for c in checks)


def test_an_unknown_case_is_refused_with_the_list(client):
    refused = client.post("/batches/demo?case=nope")
    assert refused.status_code == 404 and "clean" in refused.json()["detail"]
