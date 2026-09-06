"""Tests for the escalation checkpoint (#30).

#39 established that the approval seam is fail-closed: with no answerer composed the
live runtime refused `confirm_mapping` and wrote nothing. What it could not do was let
anybody say yes. These tests are about the half that was missing, and every one of
them is really the same question asked from a different side: *can anything other
than a person produce a grant?*

The answer has to be no on the timeout path, the full-queue path, the withdrawn path
and the answered-twice path — because those are the paths a real demo actually takes.
"""

from __future__ import annotations

import json
import re

import pytest
from fastapi.testclient import TestClient

from bridgeflow import approvals
from bridgeflow.api.main import app
from bridgeflow.config import REPO_ROOT

ANSWERER = REPO_ROOT / "plugins" / "src" / "approval" / "answerer.ts"
CONSOLE = REPO_ROOT / "backend" / "src" / "bridgeflow" / "api" / "console.html"


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A fresh queue and a private decision log per test.

    The queue is process-scoped on purpose (a decision means nothing once its caller
    is gone), so isolating tests means replacing it rather than clearing it.
    """
    monkeypatch.setattr("bridgeflow.config.settings.result_store_path", str(tmp_path))
    monkeypatch.setattr(approvals, "queue", approvals.ApprovalQueue())
    # One portal for the whole test: `ask` and `decide` must land on the same event
    # loop or the waiter would be signalled on a loop that is not waiting.
    with TestClient(app) as client:
        yield client


def _ask(client, **overrides):
    body = {
        "tool_name": "confirm_mapping",
        "call_id": "call-1",
        "reason": "changes stored state",
        "detail": [{"label": "relation", "value": "ordered_by"}],
    }
    body.update(overrides)
    response = client.post("/approvals/ask", json=body)
    assert response.status_code == 200, response.text
    return response.json()


# --- the question reaches a person -------------------------------------------


def test_a_pending_question_shows_up_on_the_console(client):
    question = _ask(client)

    waiting = client.get("/approvals").json()

    assert [q["id"] for q in waiting] == [question["id"]]
    assert waiting[0]["tool_name"] == "confirm_mapping"
    assert waiting[0]["detail"] == [{"label": "relation", "value": "ordered_by"}]


def test_the_question_cannot_carry_rows(client):
    """The scenario is 200,000 rows. An approval prompt that grows with the data is
    the same defect as a tool return value that does."""
    question = _ask(
        client,
        reason="x" * 5_000,
        detail=[{"label": f"c{i}", "value": "y" * 5_000} for i in range(50)],
    )

    assert len(question["reason"]) <= 600
    assert len(question["detail"]) <= approvals.MAX_DETAIL_ITEMS
    assert all(len(item["value"]) <= approvals.MAX_DETAIL_VALUE for item in question["detail"])


# --- only a person can grant --------------------------------------------------


def test_a_decision_is_recorded_with_who_and_when(client):
    question = _ask(client)

    decided = client.post(
        f"/approvals/{question['id']}/decide",
        json={"outcome": "allowed-once", "by": "eric"},
    ).json()

    assert decided["outcome"] == "allowed-once"
    assert decided["decided_by"] == "eric"
    assert decided["decided_at"]
    assert client.get("/approvals").json() == []


def test_the_decision_survives_the_request_that_asked(client):
    question = _ask(client)
    client.post(f"/approvals/{question['id']}/decide", json={"outcome": "rejected", "by": "eric"})

    logged = client.get("/approvals/log").json()

    assert [(e["tool_name"], e["outcome"], e["decided_by"]) for e in logged] == [
        ("confirm_mapping", "rejected", "eric")
    ]
    on_disk = approvals.log_path().read_text(encoding="utf-8").strip().splitlines()
    assert json.loads(on_disk[0])["outcome"] == "rejected"


def test_a_question_cannot_be_answered_twice(client):
    question = _ask(client)
    client.post(f"/approvals/{question['id']}/decide", json={"outcome": "rejected", "by": "eric"})

    again = client.post(f"/approvals/{question['id']}/decide", json={"outcome": "allowed-once", "by": "eric"})

    assert again.status_code == 409


# --- absence is never consent -------------------------------------------------


def test_a_timeout_is_not_an_outcome(client):
    """Waiting and getting nothing leaves the question pending. The answerer decides
    whether to give up; giving up denies, and this endpoint must not decide for it."""
    question = _ask(client)

    polled = client.get(f"/approvals/{question['id']}?wait_ms=50").json()

    assert polled["state"] == "pending"
    assert polled["outcome"] is None


def test_a_released_question_can_no_longer_be_approved(client):
    """The answerer gave up, so the tool call already failed. An approval arriving
    afterwards would authorise something that is not there."""
    question = _ask(client)

    released = client.delete(f"/approvals/{question['id']}").json()
    late = client.post(f"/approvals/{question['id']}/decide", json={"outcome": "allowed-once", "by": "eric"})

    assert released["state"] == "withdrawn"
    assert late.status_code == 409
    assert client.get("/approvals").json() == []


def test_a_full_queue_refuses_rather_than_dropping_the_question(client):
    """Refusing is a denial the answerer can act on. Silently dropping it would leave
    a tool call waiting on a question nobody will ever see."""
    for index in range(approvals.MAX_PENDING):
        _ask(client, call_id=f"call-{index}")

    overflow = client.post("/approvals/ask", json={"tool_name": "confirm_mapping"})

    assert overflow.status_code == 409


def test_an_unknown_question_is_not_answerable(client):
    assert client.post("/approvals/nope/decide", json={"outcome": "allowed-once"}).status_code == 404
    assert client.get("/approvals/nope").status_code == 404


# --- the answerer's side of the same invariant --------------------------------


def test_the_answerer_never_writes_a_grant_of_its_own(client):
    """`'allowed-once'` appears in the answerer only as a type it may receive, never
    as a value it constructs. Every failure path calls `next()`, which delegates to
    the fail-closed `unavailable`."""
    source = ANSWERER.read_text(encoding="utf-8")
    code = "\n".join(
        line for line in source.splitlines() if not line.strip().startswith(("*", "/*", "//"))
    )

    grants = re.findall(r"'allowed-once'", code)

    assert len(grants) == 1, "the grant is named once, in the shape of what the backend returns"
    assert "return state.outcome" in code


def test_every_failure_path_delegates(client):
    """A backend that is down, a full queue, a bad response — all reach `next()`."""
    source = ANSWERER.read_text(encoding="utf-8")

    catches = re.findall(r"} catch \{\n\s*(?://[^\n]*\n\s*)*(?:.*\n\s*)?return ([^\n]+)", source)

    assert catches, "the answerer has catch blocks"
    assert all(branch.startswith("next()") for branch in catches), catches


# --- the console --------------------------------------------------------------


def test_the_console_is_served_where_the_tool_call_can_be_reached(client):
    page = client.get("/console")

    assert page.status_code == 200
    assert "text/html" in page.headers["content-type"]
    assert "待确认" in page.text


def test_the_console_never_interprets_what_it_is_shown(client):
    """Values on that page are model-authored and rooted in spreadsheet cells. They
    are rendered as text or not at all."""
    # Prose about not using innerHTML is not the same as not using it, so the HTML
    # comments come out before the check.
    page = re.sub(r"<!--.*?-->", "", CONSOLE.read_text(encoding="utf-8"), flags=re.DOTALL)

    assert "innerHTML" not in page
    assert "insertAdjacentHTML" not in page
    assert "textContent" in page


# --- the record says who allowed it -------------------------------------------


def test_a_console_log_is_not_a_write_capability(client):
    question = _ask(client, call_id="call-abc")
    client.post(f"/approvals/{question['id']}/decide", json={"outcome": "allowed-once", "by": "eric"})
    response = client.post("/tools/confirm-mapping", json={
        "source": "sku:sku-a1", "target": "customer:acme-pte-ltd", "relation": "ordered_by",
        "accepted": True, "confirmed_by": "agent-7", "call_id": "call-abc",
    })
    assert response.status_code == 403


def test_an_unapproved_write_is_refused_instead_of_recording_an_empty_identity(client):
    response = client.post("/tools/confirm-mapping", json={
        "source": "sku:sku-b7", "target": "customer:bayfront-ltd", "relation": "ordered_by",
        "accepted": True, "confirmed_by": "agent-7", "call_id": "call-never-approved",
    })
    assert response.status_code == 403


def test_a_rejected_approval_cannot_be_joined_as_a_grant(client, monkeypatch, tmp_path):
    """Only `allowed-once` counts. A rejection is on the record too, and reading it as
    authorisation would invert the decision it documents."""
    monkeypatch.setattr(
        "bridgeflow.config.settings.mapping_memory_path", str(tmp_path / "mappings.json")
    )
    question = _ask(client, call_id="call-denied")
    client.post(f"/approvals/{question['id']}/decide", json={"outcome": "rejected", "by": "eric"})

    assert approvals.granted_by("call-denied") is None

# --- a refusal has to carry a reason (#86) -----------------------------------

# The framework's denial message is a constant, so an operator's objection had
# nowhere to go and the agent said `done`. These four tests hold the channel open
# from the console field to the audit line, including the case where nobody
# bothered to explain — which stays a valid refusal.


def test_a_refusal_keeps_the_reason_the_operator_gave(client):
    question = _ask(client)

    body = client.post(
        f"/approvals/{question['id']}/decide",
        json={"outcome": "rejected", "by": "eric", "note": "evidence is stale"},
    ).json()

    assert body["decision_note"] == "evidence is stale"


def test_the_reason_reaches_the_polling_answerer(client):
    """The answerer reads the note off this endpoint and the gate quotes it to the
    model. If the field stops travelling here, the agent is deaf again."""
    question = _ask(client)
    client.post(
        f"/approvals/{question['id']}/decide",
        json={"outcome": "rejected", "by": "eric", "note": "wrong BOM"},
    )

    polled = client.get(f"/approvals/{question['id']}").json()

    assert polled["outcome"] == "rejected"
    assert polled["decision_note"] == "wrong BOM"


def test_refusing_without_explaining_is_still_a_refusal(client):
    """The note is optional. Demanding one would train people to type filler."""
    question = _ask(client)

    body = client.post(
        f"/approvals/{question['id']}/decide",
        json={"outcome": "rejected", "by": "eric"},
    ).json()

    assert body["outcome"] == "rejected"
    assert body["decision_note"] == ""


def test_an_operator_note_is_bounded_like_everything_else_on_this_path(client):
    """It arrives from a browser and ends up inside a model prompt."""
    question = _ask(client)

    body = client.post(
        f"/approvals/{question['id']}/decide",
        json={"outcome": "rejected", "by": "eric", "note": "x" * 4000},
    ).json()

    assert len(body["decision_note"]) <= 240


def test_the_decision_is_logged_with_its_reason(client):
    question = _ask(client)
    client.post(
        f"/approvals/{question['id']}/decide",
        json={"outcome": "rejected", "by": "eric", "note": "evidence is stale"},
    )

    entry = json.loads(approvals.log_path().read_text("utf-8").splitlines()[-1])

    assert entry["decision_note"] == "evidence is stale"
