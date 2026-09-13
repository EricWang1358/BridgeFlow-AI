"""The mock quotation samples (#104, #7, #20): every input traced to its original, the draft equals the hand answer.

The samples are fictional, written the way a concrete supplier's documents look. What this locks is the
chain: a fact is only used if its excerpt or cell really says it; the price bands follow the declared
policy; a condition the policy forbids refuses the draft instead of producing one.
"""
import copy
import hashlib

import openpyxl
import pytest
import yaml

from bridgeflow.config import REPO_ROOT
from bridgeflow.documents import evaluate_document
from bridgeflow.schemas import SourceRef

BASE = REPO_ROOT / "data/mock_business/quotation"


def _facts():
    record = yaml.safe_load((BASE / "extraction.yaml").read_text(encoding="utf-8"))
    config = yaml.safe_load((BASE / "dictionary.yaml").read_text(encoding="utf-8"))["quotation"]
    facts = {}
    for key, fact in record["facts"].items():
        path = BASE / fact["file"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if "cell" in fact:
            sheet, cell = fact["cell"].split("!")
            stored = openpyxl.load_workbook(path, data_only=True)[sheet][cell].value
            assert float(stored) == float(fact["value"]), (key, stored)
            source = SourceRef(department=fact["department"], batch=record["document_id"], filename=path.name,
                               sheet=sheet, paragraph=cell, excerpt=f"{sheet}!{cell} = {stored}", document_sha256=digest)
        else:
            text = path.read_text(encoding="utf-8")
            section = text.split(f"## {fact['paragraph']}", 1)
            assert len(section) == 2 and fact["excerpt"] in section[1].split("\n## ", 1)[0], key
            source = SourceRef(department=fact["department"], batch=record["document_id"], filename=path.name,
                               paragraph=fact["paragraph"], excerpt=fact["excerpt"], document_sha256=digest)
        facts[key] = {"status": "extracted", "value": fact["value"], "unit": config["inputs"][key]["unit"],
                      "sources": [source.model_dump()]}
    return config, {"id": record["document_id"], "status": "extracted", "facts": facts}


@pytest.fixture
def case():
    config, document = _facts()
    raw = (BASE / "dictionary.yaml").read_bytes()
    declaration = SourceRef(department="marketing", filename="dictionary.yaml", paragraph="quotation",
                            excerpt="quotation:", document_sha256=hashlib.sha256(raw).hexdigest())
    return config, document, declaration


def test_every_declared_input_is_traced_to_a_real_place_in_an_original(case):
    config, document, _ = case
    assert set(document["facts"]) == set(config["inputs"])


def test_the_draft_equals_the_hand_computed_answer(case):
    result = evaluate_document(*case)
    assert result["status"] == "draft", result["refusals"]
    fields = {f["metric"]: f["value"] for f in result["fields"]}
    assert fields["unit_cost"] == "356.47"
    assert (fields["floor_price"], fields["target_price"], fields["stretch_price"]) == ("419.77", "436.72", "448.02")
    assert fields["target_total"] == "5240640.00"
    checks = {c["id"]: (c["status"], c["decision_owner"]) for c in result["checks"]}
    assert checks["below_floor"] == ("attention", "总经理（模拟）")
    assert checks["below_target"][0] == "attention"
    assert all(checks[i][0] == "ok" for i in ("capacity", "credit_grade_c", "payment_ratio", "lead_time"))
    assert result["execution_status"] == "not_approved_not_sent"
    for name in ("419.77", "436.72", "448.02", "5,240,640.00"):
        assert name in (BASE / "expected-quote.md").read_text(encoding="utf-8")


@pytest.mark.parametrize(("key", "value", "refusal"), [
    ("requested_payment_ratio", "0.60", "payment_ratio"),
    ("peak_monthly_volume", "3500", "capacity"),
    ("payment_days", "81", "credit_grade_c"),
    ("requested_first_pour_days", "5", "lead_time"),
])
def test_a_condition_the_policy_forbids_refuses_the_draft(case, key, value, refusal):
    config, document, declaration = copy.deepcopy(case)
    document["facts"][key]["value"] = value
    result = evaluate_document(config, document, declaration)
    assert result["status"] == "refused" and result["fields"] == []
    assert [r["field"] for r in result["refusals"]] == [refusal]


def test_a_fact_with_no_original_is_refused(case):
    config, document, declaration = copy.deepcopy(case)
    document["facts"]["material_cost"]["sources"] = []
    result = evaluate_document(config, document, declaration)
    assert result["status"] == "refused" and result["refusals"][0]["code"] == "missing_source"
