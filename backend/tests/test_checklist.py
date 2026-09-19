"""The monthly close checklist (E14-UC01): a read-only projection over batch, master and review."""
import pytest
from fastapi.testclient import TestClient
from test_conclusions import finalize
from test_resupply import LABELS, XLSX, original

from bridgeflow.api.main import app
from bridgeflow.config import REPO_ROOT, settings
from bridgeflow.monthly import checklist as checklist_module

DEMO = REPO_ROOT / "data/mock_business/demo"


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "field_dictionary_path", str(DEMO / "dictionary.yaml"))
    monkeypatch.setattr(settings, "result_store_path", str(tmp_path))
    with TestClient(app) as test_client:
        yield test_client


def steps(client, period="2024-07"):
    return {s["id"]: s for s in client.get(f"/monthly/checklist?period={period}").json()["steps"]}


def import_three(client):
    files = [("files", (f"{name}.xlsx", original(name), XLSX)) for name in LABELS if name != "marketing"]
    departments = [name for name in LABELS if name != "marketing"]
    response = client.post("/batches", data={"period": "2024-07", "departments": departments}, files=files)
    assert response.status_code == 200, response.text
    return response.json()["batch_id"]


def test_a_missing_department_blocks_the_review_step_and_says_who_owes_it(client):
    import_three(client)
    found = steps(client)
    assert found["files_submitted"]["state"] == "blocked"
    assert found["files_submitted"]["outstanding"] == ["marketing"]
    assert found["files_submitted"]["owner_role"] == "部门填报员"
    assert found["review_validated"]["state"] == "open"
    assert client.get("/monthly/checklist?period=2024-07").json()["ready_to_close"] is False


def test_an_open_master_question_keeps_its_step_open_with_a_count_and_a_place_to_go(client):
    batch = client.post("/batches/demo").json()["batch_id"]
    found = steps(client)
    master = client.get(f"/integration/batches/{batch}").json()
    assert found["open_items_cleared"]["count"] == len(master["issues"]) > 0
    assert found["open_items_cleared"]["state"] == "open"
    assert found["open_items_cleared"]["next_view"] == "integration"
    assert found["files_submitted"]["state"] == "done" and found["intake_accepted"]["state"] == "done"


def test_a_step_whose_state_cannot_be_read_is_unknown_and_withholds_ready_to_close(client, monkeypatch):
    client.post("/batches/demo")

    def explode(spec, ctx):
        raise TimeoutError("the review service did not answer")

    monkeypatch.setitem(checklist_module.EVALUATORS, "review_validated", explode)
    result = client.get("/monthly/checklist?period=2024-07").json()
    review = next(s for s in result["steps"] if s["id"] == "review_validated")
    assert review["state"] == "unknown" and "TimeoutError" in review["reason"]
    assert result["ready_to_close"] is False
    # The other steps are still reported: one unreadable step does not blank the page.
    assert {s["state"] for s in result["steps"]} - {"unknown"}


def test_a_period_with_no_batch_reports_every_step_as_outstanding(client):
    result = client.get("/monthly/checklist?period=2024-05").json()
    assert result["batch_id"] == "" and result["ready_to_close"] is False
    assert {s["state"] for s in result["steps"]} <= {"blocked", "open", "unknown"}


def test_a_dictionary_that_declares_no_steps_refuses_instead_of_inventing_them():
    result = checklist_module.build({}, checklist_module.Context(period="2024-07"))
    assert result.steps == [] and result.ready_to_close is False and "monthly_close.steps" in result.refusal


def test_the_captain_gets_counts_and_owners_but_no_rows(client):
    batch = client.post("/batches/demo").json()["batch_id"]
    finalize(client, batch)
    result = client.post("/tools/monthly-checklist", json={"period": "2024-07"}).json()
    assert result["batch_id"] == batch and result["outstanding"] >= 1
    assert all("rows" not in step for step in result["steps"])
    assert "unknown" in result["next_step"] or result["ready_to_close"]
    review = next(s for s in result["steps"] if s["id"] == "review_validated")
    assert review["state"] == "done" and review["owner_role"] == "各部门负责人"
