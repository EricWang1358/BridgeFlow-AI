"""The decision journal and the generated acceptance report (rubric: observability, evaluation).

The journal is written in one place — middleware — so these tests exercise real requests and
then read back what the system said about itself.
"""
import json

import pytest
from fastapi.testclient import TestClient

from bridgeflow import journal
from bridgeflow.api.main import app
from bridgeflow.config import REPO_ROOT, settings

DEMO = REPO_ROOT / "data/mock_business/demo"


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "field_dictionary_path", str(DEMO / "dictionary.yaml"))
    monkeypatch.setattr(settings, "result_store_path", str(tmp_path))
    with TestClient(app) as test_client:
        yield test_client


def test_every_request_leaves_one_entry_with_its_trace(client):
    response = client.post("/batches/demo")
    trace = response.headers["x-bridgeflow-trace"]
    assert len(trace) == 16
    entries = client.get("/journal").json()["entries"]
    mine = [e for e in entries if e["trace"] == trace]
    assert len(mine) == 1
    assert mine[0]["surface"] == "/batches/demo" and mine[0]["outcome"] == "wrote"
    assert mine[0]["ms"] > 0 and mine[0]["actor"] in {"host", "anonymous"}


def test_a_refusal_is_recorded_in_its_own_words(client):
    batch = client.post("/batches/demo").json()["batch_id"]
    refused = client.get(f"/conclusions/batches/{batch}/report")
    assert refused.status_code == 409
    entry = next(e for e in client.get("/journal?outcome=refused").json()["entries"]
                 if e["trace"] == refused.headers["x-bridgeflow-trace"])
    assert entry["outcome"] == "refused" and entry["status"] == 409
    # The sentence the caller was given is the sentence the journal keeps, not a paraphrase.
    assert entry["reason"] == refused.json()["detail"]


def test_the_journal_groups_by_decision_not_by_instance(client):
    first = client.post("/batches/demo").json()["batch_id"]
    client.get(f"/integration/batches/{first}")
    client.get(f"/conclusions/batches/{first}/comparison")
    surfaces = {e["surface"] for e in client.get("/journal").json()["entries"]}
    assert "/integration/batches/{id}" in surfaces
    assert not any(first in surface for surface in surfaces)


def test_the_journal_carries_no_rows_and_no_cell_values(client):
    batch = client.post("/batches/demo").json()["batch_id"]
    client.get(f"/integration/batches/{batch}")
    master = client.get(f"/integration/batches/{batch}").json()
    text = json.dumps(client.get("/journal").json(), ensure_ascii=False)
    values = [str(v) for row in master["rows"] for v in row["values"].values() if isinstance(v, str) and len(str(v)) > 6]
    assert values, "the demo master has text values to look for"
    assert not any(value in text for value in values)


def test_the_summary_counts_outcomes_and_ranks_refusal_reasons(client):
    batch = client.post("/batches/demo").json()["batch_id"]
    for _ in range(2):
        client.get(f"/conclusions/batches/{batch}/report")
    summary = client.get("/journal").json()
    assert summary["by_outcome"]["refused"] >= 2 and summary["by_outcome"]["wrote"] >= 1
    assert summary["refusal_reasons"][0]["count"] >= 2
    assert summary["median_ms"] >= 0 and summary["slowest_ms"] >= summary["median_ms"]


def test_filters_narrow_the_entries_without_changing_the_counts(client):
    batch = client.post("/batches/demo").json()["batch_id"]
    client.get(f"/conclusions/batches/{batch}/report")
    everything = client.get("/journal").json()
    refused = client.get("/journal?outcome=refused").json()
    assert refused["by_outcome"] == everything["by_outcome"]
    assert all(e["outcome"] == "refused" for e in refused["entries"])
    by_batch = client.get(f"/journal?batch_id={batch}").json()
    assert all((e.get("facts") or {}).get("batch_id") == batch for e in by_batch["entries"])


def test_without_a_generated_report_the_studio_is_told_to_generate_one(client):
    result = client.get("/eval/report").json()
    assert result["checks"] == [] and "bridgeflow.eval" in result["refusal"]


def test_a_generated_report_carries_both_tracks_and_its_age(client, tmp_path):
    from bridgeflow.eval import report_path
    path = report_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "generated_at": "2026-09-20T09:00:00+00:00", "passed": 2, "total": 3,
        "tracks": {"golden": {"passed": 2, "total": 2}, "adversarial": {"passed": 0, "total": 1}},
        "checks": [{"industry": "refusals", "name": "x", "passed": False, "detail": "d",
                    "owner": "#16", "track": "adversarial"}]}, ensure_ascii=False), encoding="utf-8")
    report = client.get("/eval/report").json()
    assert report["tracks"]["adversarial"]["total"] == 1 and report["age_hours"] is not None
    assert report["checks"][0]["owner"] == "#16"


def test_the_journal_keeps_itself_bounded(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "result_store_path", str(tmp_path))
    folder = tmp_path / "journal"
    folder.mkdir(parents=True)
    for day in range(20):
        (folder / f"2026-09-{day + 1:02d}.jsonl").write_text("{}\n", encoding="utf-8")
    assert journal.prune(keep_days=14) == 6
    assert len(list(folder.glob("*.jsonl"))) == 14


def call(client, path, body, *, run, agent, tool, call_id="c1"):
    """A tool call as the plugin makes it: the run id is the model-requested call's id."""
    subject = {"x-bridgeflow-batch": str(body["batch_id"])} if "batch_id" in body else {}
    return client.post(path, json=body, headers={
        "x-bridgeflow-root": run, "x-bridgeflow-call": call_id,
        "x-bridgeflow-agent": agent, "x-bridgeflow-tool": tool} | subject)


def test_a_run_is_one_model_requested_call_and_everything_under_it(client):
    batch = client.post("/batches/demo").json()["batch_id"]
    call(client, "/tools/batch-summary", {"batch_id": batch}, run="r-1", agent="captain", tool="batch_summary")
    call(client, "/tools/integration-summary", {"batch_id": batch}, run="r-1", agent="captain",
         tool="integration_summary", call_id="c2")
    call(client, "/tools/monthly-inbox", {"period": "2024-07"}, run="r-1", agent="child-finance",
         tool="monthly_inbox", call_id="c3")
    call(client, "/tools/risk-dispositions", {"batch_id": batch}, run="r-2", agent="captain",
         tool="risk_dispositions", call_id="c4")

    runs = {r["run"]: r for r in client.get("/journal/runs").json()["runs"]}
    assert set(runs) == {"r-1", "r-2"}
    first = runs["r-1"]
    assert first["steps"] == 3 and first["agents"] == ["captain", "child-finance"]
    assert first["batch_id"] == batch and first["ms"] > 0
    assert [step["tool"] for step in first["timeline"]] == ["batch_summary", "integration_summary", "monthly_inbox"]
    assert first["refused"] == 0


def test_a_refusal_inside_a_run_is_shown_on_its_step(client):
    batch = client.post("/batches/demo").json()["batch_id"]
    call(client, "/tools/risk-dispositions", {"batch_id": batch}, run="r-3", agent="captain", tool="risk_dispositions")
    runs = {r["run"]: r for r in client.get("/journal/runs").json()["runs"]}
    step = runs["r-3"]["timeline"][0]
    assert runs["r-3"]["refused"] == 1 and step["outcome"] == "refused"
    assert "review" in step["reason"].lower() and step["trace"]


def test_browser_reads_are_not_runs(client):
    batch = client.post("/batches/demo").json()["batch_id"]
    client.get(f"/integration/batches/{batch}")
    assert client.get("/journal/runs").json()["runs"] == []
