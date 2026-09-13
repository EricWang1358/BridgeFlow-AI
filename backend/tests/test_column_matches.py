"""An uploaded column matched onto a declared one: proposed, approved, remembered.

The walk these tests take is the one the product promises (#102, #46, #61): an export
arrives with a header the dictionary does not know, the batch refuses to join, the
captain is shown the declared columns it could be, a person approves one, and the
next import works — without anybody editing the dictionary.
"""
import ast
import json
from pathlib import Path

import pytest
from conftest import receipt
from fastapi.testclient import TestClient

from bridgeflow import business, column_matches
from bridgeflow.api.batches import load_batch
from bridgeflow.api.main import app
from bridgeflow.config import REPO_ROOT, settings

CASES = REPO_ROOT / "data/business_demo"
DICTIONARY = CASES / "dictionary.yaml"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "field_dictionary_path", str(DICTIONARY))
    with TestClient(app) as client:
        yield client


def _declared_entity(department: str) -> str:
    """The finance entity column, read from the dictionary rather than written here."""
    import yaml
    columns = yaml.safe_load(DICTIONARY.read_text(encoding="utf-8"))["columns"][department]
    return next(iter(columns))


FINANCE_KEY = _declared_entity("finance")
RENAMED = f"{FINANCE_KEY}_code"


def rename_header(content: bytes, new: str = RENAMED) -> bytes:
    header, rest = content.split(b"\n", 1)
    names = header.decode().split(",")
    return (",".join(new if n == FINANCE_KEY else n for n in names) + "\n").encode() + rest


def numeric_key(content: bytes) -> bytes:
    lines = rename_header(content).decode().splitlines()
    out = [lines[0]] + [",".join([str(1000 + i), *line.split(",")[1:]]) for i, line in enumerate(lines[1:]) if line]
    return ("\n".join(out) + "\n").encode()


def upload(client, finance=rename_header):
    files = []
    for role in business.ROLES:
        content = (CASES / "risk" / f"{role}.csv").read_bytes()
        if role == "finance" and finance:
            content = finance(content)
        files.append(("files", (f"{role}.csv", content, "text/csv")))
    response = client.post("/batches", data={"period": "2025-11", "departments": list(business.ROLES)}, files=files)
    assert response.status_code == 200, response.text
    return response.json()


def decide(client, batch_id, target, accepted=True, column=RENAMED, approve=True):
    payload = {"batch_id": batch_id, "department": "finance", "column": column, "target": target,
               "accepted": accepted, "reason": "", "confirmed_by": "captain", "call_id": "c1"}
    body = json.dumps(payload, separators=(",", ":")).encode()
    headers = {"content-type": "application/json"}
    if approve:
        headers["x-bridgeflow-approval"] = receipt(body)
    return client.post("/tools/confirm-column-match", content=body, headers=headers)


def test_an_unknown_header_blocks_the_join_and_offers_only_declared_columns(client):
    batch = upload(client)
    assert batch["status"] == "needs_configuration"
    assert batch["column_questions"] > 0

    response = client.post("/tools/column-candidates", json={"batch_id": batch["batch_id"]})
    assert response.status_code == 200
    questions = {(q["department"], q["column"]): q for q in response.json()["questions"]}
    question = questions[("finance", RENAMED)]
    declared = column_matches.declared_columns(load_batch(batch["batch_id"]).dictionary_snapshot, "finance")
    targets = {c["target"] for c in question["candidates"]}
    assert FINANCE_KEY in targets
    assert targets <= set(declared), "every candidate must already be declared"

    best = next(c for c in question["candidates"] if c["target"] == FINANCE_KEY)
    assert best["role"].startswith("entity:")
    assert best["type_fits"] is True
    assert best["entity_overlap"] is not None and best["entity_overlap"] >= 0.5


def test_no_cell_value_reaches_the_candidate_payload(client):
    batch = upload(client)
    text = client.post("/tools/column-candidates", json={"batch_id": batch["batch_id"]}).text
    rows = (CASES / "risk" / "finance.csv").read_text(encoding="utf-8").splitlines()[1:]
    for cell in {c for line in rows for c in line.split(",") if len(c) > 3}:
        assert cell not in text, f"cell value {cell!r} leaked into the tool payload"


def test_a_target_outside_the_closed_set_is_refused_before_any_approval(client):
    batch = upload(client)
    invented = decide(client, batch["batch_id"], "invented_field")
    assert invented.status_code == 409
    assert "dictionary owner" in invented.json()["detail"]
    # A declared column the upload already carries is not a candidate either.
    present = next(iter(column_matches.declared_columns(
        load_batch(batch["batch_id"]).dictionary_snapshot, "finance").keys() - {FINANCE_KEY}))
    assert decide(client, batch["batch_id"], present).status_code == 409


def test_a_decision_needs_a_fresh_approval(client):
    batch = upload(client)
    assert decide(client, batch["batch_id"], FINANCE_KEY, approve=False).status_code == 403
    assert column_matches.load().matches == []


def test_an_approved_match_makes_the_next_import_join_and_leaves_the_old_batch_alone(client):
    first = upload(client)
    result = decide(client, first["batch_id"], FINANCE_KEY)
    assert result.status_code == 200, result.text
    assert "import the files again" in result.json()["next_step"]

    second = upload(client)
    assert second["status"] != "needs_configuration", second["refusal"]
    assert second["master_rows"] > 0
    assert second["matched_columns"] == [f"finance.{RENAMED} → {FINANCE_KEY}"]

    # The source reference still points at what the department actually wrote.
    finance = next(t for t in load_batch(second["batch_id"]).clean_tables if t.department == "finance")
    assert finance.original_columns[FINANCE_KEY] == RENAMED

    # Frozen means frozen.
    again = client.get(f"/batches/{first['batch_id']}").json()
    assert again["status"] == "needs_configuration" and again["matched_columns"] == []


def test_a_rejection_is_remembered_and_says_what_is_left(client):
    batch = upload(client)
    result = decide(client, batch["batch_id"], FINANCE_KEY, accepted=False)
    assert result.status_code == 200
    body = result.json()
    assert body["accepted"] is False
    assert FINANCE_KEY not in body["remaining_candidates"]
    assert "Rejected and remembered" in body["next_step"]

    assert upload(client)["status"] == "needs_configuration"
    candidates = client.post("/tools/column-candidates", json={"batch_id": batch["batch_id"]}).json()
    question = next(q for q in candidates["questions"] if q["column"] == RENAMED)
    assert next(c for c in question["candidates"] if c["target"] == FINANCE_KEY)["decided"] == "rejected"


def test_a_column_whose_shape_changed_is_asked_again_not_silently_matched(client):
    first = upload(client)
    assert decide(client, first["batch_id"], FINANCE_KEY).status_code == 200

    changed = upload(client, finance=numeric_key)
    assert changed["matched_columns"] == []
    assert changed["stale_matches"] == [f"finance.{RENAMED} → {FINANCE_KEY}"]
    assert changed["status"] == "needs_configuration"


def test_no_field_name_is_written_into_the_module():
    tree = ast.parse(Path(column_matches.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        holder = isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
        if holder and ast.get_docstring(node) is not None:
            node.body = node.body[1:] or [ast.Pass()]
    code = ast.unparse(tree).lower()
    for name in ("sku", "gl_account", "customer", "material", "project"):
        assert name not in code, f"{name} must not appear in the code"


def test_the_browser_wizard_view_lists_candidates_decisions_and_no_cells(client):
    batch = upload(client)
    rows = client.get(f"/batches/{batch['batch_id']}/view?section=columns&limit=100").json()["rows"]
    mine = [r for r in rows if r["department"] == "finance" and r["column"] == RENAMED]
    assert FINANCE_KEY in {r["candidate"] for r in mine} and {r["decision"] for r in mine} == {"open"}
    decide(client, batch["batch_id"], FINANCE_KEY, accepted=False)
    rows = client.get(f"/batches/{batch['batch_id']}/view?section=columns&limit=100").json()["rows"]
    assert next(r for r in rows if r["candidate"] == FINANCE_KEY and r["column"] == RENAMED)["decision"] == "rejected"
    text = str(rows)
    for cell in {c for line in (CASES / "risk" / "finance.csv").read_text(encoding="utf-8").splitlines()[1:] for c in line.split(",") if len(c) > 3}:
        assert cell not in text
