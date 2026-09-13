"""One review ends exactly once, with a reason, whatever order events arrive in (#112, #113, #111)."""
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from test_business_mvp import CASES, judgement, upload

from bridgeflow import review_runs
from bridgeflow.api.main import app
from bridgeflow.config import settings


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "field_dictionary_path", str(CASES / "dictionary.yaml"))
    with TestClient(app) as client:
        yield client


def opened(client, review_id="review-0001", deadline=180):
    batch_id = upload(client)
    response = client.post("/tools/review-open", json={"review_id": review_id, "batch_id": batch_id,
                                                        "parent_session_id": "parent", "deadline_seconds": deadline})
    assert response.status_code == 200, response.text
    context = client.post("/tools/review-context", json={"batch_id": batch_id}).json()
    runs = [{"role": p["role"], "session_id": f"child-{p['role']}", "status": "completed", "judgement": judgement(p)}
            for p in context["roles"]]
    return batch_id, runs


def finalize(client, batch_id, runs, review_id="review-0001", reason="completed"):
    return client.post("/tools/review-finalize", json={"batch_id": batch_id, "parent_session_id": "parent", "runs": runs,
                                                       "review_id": review_id, "terminal_reason": reason})


def reports(batch_id):
    folder = review_runs._root() / "batches" / "reviews" / batch_id
    return sorted(folder.glob("*.json"))


def test_finalizing_twice_returns_the_same_report(client):
    batch_id, runs = opened(client)
    first = finalize(client, batch_id, runs).json()
    again = finalize(client, batch_id, runs).json()
    assert first["status"] == "validated" and first["terminal_reason"] == "completed"
    assert again["report_id"] == first["report_id"] and len(reports(batch_id)) == 1


def test_a_timeout_cannot_be_overwritten_by_a_late_success(client):
    batch_id, runs = opened(client)
    aborted = [{**r, "status": "aborted", "judgement": None} for r in runs]
    timed_out = finalize(client, batch_id, aborted, reason="deadline_exceeded").json()
    late = finalize(client, batch_id, runs).json()
    assert timed_out["status"] == "partial" and late["report_id"] == timed_out["report_id"]
    assert late["terminal_reason"] == "deadline_exceeded"


def test_a_finalize_after_the_deadline_is_not_reported_as_completed(client, monkeypatch):
    batch_id, runs = opened(client, deadline=10)
    later = datetime.now(UTC) + timedelta(seconds=11)
    monkeypatch.setattr(review_runs, "_now", lambda: later)
    report = finalize(client, batch_id, runs).json()
    assert (report["status"], report["terminal_reason"]) == ("partial", "deadline_exceeded")
    assert all(role["status"] == "unvalidated" for role in report["roles"])


def test_a_restarted_host_ends_open_reviews_with_a_readable_report(client):
    batch_id, _ = opened(client)
    ended = client.post("/tools/review-recover").json()["ended"]
    assert [e["review_id"] for e in ended] == ["review-0001"]
    report = client.get(f"/batches/{batch_id}/review").json()
    assert (report["status"], report["terminal_reason"]) == ("partial", "host_restarted")
    assert client.post("/tools/review-recover").json()["ended"] == []


def test_an_unknown_or_foreign_review_cannot_be_finalized(client):
    batch_id, runs = opened(client)
    assert finalize(client, batch_id, runs, review_id="review-9999").status_code == 409
    other = client.post("/tools/review-finalize", json={"batch_id": batch_id, "parent_session_id": "someone-else",
                                                        "runs": runs, "review_id": "review-0001"})
    assert other.status_code == 409


def test_a_human_note_is_recorded_once_beside_the_report_without_changing_it(client):
    batch_id, runs = opened(client)
    report = finalize(client, batch_id, [{**r, "status": "aborted", "judgement": None} for r in runs],
                      reason="captain_ended").json()
    note = {"batch_id": batch_id, "report_id": report["report_id"], "parent_session_id": "parent",
            "note_id": "note-0001", "note": "财务部门需线下确认"}
    assert client.post("/tools/review-note", json=note).json() == {"recorded": True, "notes": 1}
    assert client.post("/tools/review-note", json=note).json() == {"recorded": False, "notes": 1}
    assert client.get(f"/batches/{batch_id}/review?report_id={report['report_id']}").json() == report
    notes = client.get(f"/batches/{batch_id}/review-notes/{report['report_id']}").json()["notes"]
    assert [n["note"] for n in notes] == ["财务部门需线下确认"]
