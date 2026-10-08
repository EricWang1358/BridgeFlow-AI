"""Quotation contract terms checked against the legal requirements (#302, demo cut).

What this locks: each built-in quotation keeps its own contract; every requirement gets a
conclusion that quotes the contract; missing information is undetermined, never compliant;
the frozen model conclusions are re-admitted on load, so a forged citation, an uncited
"compliant", numbers in the prose, or a conclusion made for another version cannot pass.
"""
import copy
import shutil

import pytest
import yaml
from fastapi.testclient import TestClient

from bridgeflow.api.main import app
from bridgeflow.config import REPO_ROOT, settings
from bridgeflow.quote_compliance import (
    Bundle,
    CaseError,
    ContractTerms,
    FieldValue,
    LegalRequirement,
    admit_judgements,
    judge_rule,
    split_clauses,
)

BASE = REPO_ROOT / "data/quote_compliance_demo"
A, B = "BJ-2024-0715", "BJ-2024-0718"


# The English guest dictionary and its Chinese original declare the same quotation arithmetic.
@pytest.fixture(params=["data/demo_en/demo/dictionary.yaml", "data/mock_business/demo/dictionary.yaml"])
def demo(monkeypatch, request):
    monkeypatch.setattr(settings, "field_dictionary_path", str(REPO_ROOT / request.param))
    monkeypatch.setattr(settings, "quotation_cases_path", str(BASE / "quotes.yaml"))
    return TestClient(app)


def _copy(tmp_path):
    """A writable copy of the bundle; its dictionary reference is relative, so it is pinned to the original."""
    shutil.copytree(BASE, tmp_path / "q")
    path = tmp_path / "q/quotes.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace(
        "dictionary: ../demo_en/demo/dictionary.yaml", f"dictionary: {REPO_ROOT / 'data/demo_en/demo/dictionary.yaml'}"), encoding="utf-8")
    return tmp_path / "q"


def _statuses(case: dict) -> dict:
    out = {r["requirement_id"]: r["status"] for r in case["compliance"]["requirements"]}
    out.update({f"consistent:{c['metric']}": c["status"] for c in case["compliance"]["consistency"]})
    return out


def test_both_samples_equal_the_hand_answer(demo):
    a, b = demo.get(f"/quotation/cases/{A}").json(), demo.get(f"/quotation/cases/{B}").json()
    assert _statuses(a) == {"payment_days_max": "undetermined", "penalty_cap_max": "undetermined",
                            "no_unlimited_liability": "undetermined", "ip_clause_required": "non_compliant",
                            "warranty_clause_required": "non_compliant", "consistent:payment_ratio": "undetermined"}
    assert _statuses(b) == {"payment_days_max": "compliant", "penalty_cap_max": "non_compliant",
                            "no_unlimited_liability": "compliant", "ip_clause_required": "compliant",
                            "warranty_clause_required": "compliant", "consistent:payment_ratio": "inconsistent"}
    assert a["compliance"]["overall"] == b["compliance"]["overall"] == "non_compliant"
    fields = {f["metric"]: f["value"] for f in b["draft"]["fields"]}
    assert b["draft"]["status"] == "draft" and fields["target_total"] == "1746880.00" and fields["payment_ratio"] == "0.75"
    answer = (BASE / "expected-compliance.md").read_text(encoding="utf-8")
    assert "1,746,880.00" in answer and "**Inconsistent**" in answer


def test_each_quotation_keeps_its_own_contract(demo):
    a, b = demo.get(f"/quotation/cases/{A}").json(), demo.get(f"/quotation/cases/{B}").json()
    assert a["contract"]["file"] != b["contract"]["file"]
    assert a["contract"]["document_sha256"] != b["contract"]["document_sha256"]
    assert a["contract"]["fields"] == {} and set(b["contract"]["fields"]) >= {"payment_days", "penalty_cap_ratio"}
    assert not {c["text"] for c in a["contract"]["clauses"]} & {c["text"] for c in b["contract"]["clauses"]}


def test_every_conclusion_names_the_legal_version_and_quotes_the_contract(demo):
    case = demo.get(f"/quotation/cases/{B}").json()
    assert case["compliance"]["legal_version"] == 1
    clauses = {c["id"]: c["text"] for c in case["contract"]["clauses"]}
    for result in case["compliance"]["requirements"]:
        assert result["evidence"], result["requirement_id"]
        for citation in result["evidence"]:
            assert citation["excerpt"] in clauses[citation["clause"]]
    penalty = next(r for r in case["compliance"]["requirements"] if r["requirement_id"] == "penalty_cap_max")
    assert penalty["suggestion"] and penalty["observed"] == "0.30" and penalty["decided_by"] == "rule"


def test_the_list_names_both_samples_and_the_requirements(demo):
    listing = demo.get("/quotation/cases").json()
    assert listing["status"] == "available" and [q["id"] for q in listing["quotes"]] == [A, B]
    assert listing["legal"]["version"] == 1 and len(listing["legal"]["requirements"]) == 5
    assert demo.get("/quotation/cases/nope").status_code == 404


def test_a_different_quotation_declaration_hides_the_samples(demo, monkeypatch):
    monkeypatch.setattr(settings, "field_dictionary_path", str(REPO_ROOT / "data/quotation_demo/dictionary.yaml"))
    assert demo.get("/quotation/cases").json()["status"] == "not_applicable"
    assert demo.get(f"/quotation/cases/{A}").status_code == 404
    monkeypatch.setattr(settings, "quotation_cases_path", "")
    assert demo.get("/quotation/cases").json()["status"] == "not_applicable"


# --- rules ------------------------------------------------------------------------------

CAP = LegalRequirement(id="cap", title="t", basis="b", kind="field_max", field="payment_days", threshold="60", suggestion="s")


def test_a_missing_term_is_undetermined_never_compliant():
    result = judge_rule(CAP, ContractTerms(file="x", complete=True))
    assert (result["status"], result["reason_code"], result["suggestion"]) == ("undetermined", "missing_field", None)


@pytest.mark.parametrize(("value", "status"), [("60", "compliant"), ("61", "non_compliant"), ("45", "compliant")])
def test_bounds_are_closed(value, status):
    terms = ContractTerms(file="x", complete=True, fields={"payment_days": FieldValue(value=value, clause="1", excerpt="ab")})
    assert judge_rule(CAP, terms)["status"] == status


def test_a_term_that_does_not_quote_its_clause_refuses_the_sample(tmp_path):
    path = _copy(tmp_path) / "quotes.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["quotes"][1]["contract"]["fields"]["penalty_cap_ratio"]["excerpt"] = "capped in aggregate at 10% of the contract total"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    bundle = Bundle(path)
    with pytest.raises(CaseError):
        bundle.contract(bundle.quote(B))


def test_clauses_split_on_articles_and_numbered_lines():
    clauses = split_clauses("# t\n\n> note\n\n## Article 1 Scope\nBody text\n\n## Article 12 Payment\n12.1 First clause\nwrapped line\n12.2 Second\n")
    assert [(c.id, c.text) for c in clauses] == [("1", "Body text"), ("12.1", "First clause wrapped line"), ("12.2", "Second")]


# --- frozen model conclusions -----------------------------------------------------------

IP = LegalRequirement(id="ip", title="t", basis="b", kind="clause_required", topic="intellectual property", guidance="g", suggestion="s")
CLAUSES = split_clauses("## Article 6 Intellectual property\nIntellectual property in technical documents belongs to the supplier.\n")
GOOD = {"requirement_id": "ip", "status": "compliant", "citations": [{"clause": "6", "excerpt": "belongs to the supplier"}],
        "explanation": "Article Six states who owns the intellectual property."}


def _admit(answer, complete=True, **kwargs):
    return admit_judgements([IP], CLAUSES, complete, None if answer is None else [answer], **kwargs)[0]


def test_a_verified_conclusion_stands():
    result = _admit(GOOD)
    assert (result["status"], result["decided_by"], result["explanation_status"]) == ("compliant", "model", "model_advice")


@pytest.mark.parametrize("change", [
    {"citations": [{"clause": "6", "excerpt": "belongs to the buyer"}]},     # not in the contract
    {"citations": [{"clause": "9", "excerpt": "belongs to the supplier"}]},  # no such clause
    {"citations": []},                                                      # compliant without a citation
    {"explanation": "Article 6 states who owns the intellectual property."},  # a number in the prose
    {"explanation": ""},
])
def test_an_unverifiable_conclusion_degrades_to_undetermined(change):
    result = _admit({**copy.deepcopy(GOOD), **change})
    assert (result["status"], result["reason_code"]) == ("undetermined", "model_rejected")


def test_an_absent_clause_needs_the_whole_contract():
    absent = {"requirement_id": "ip", "status": "non_compliant", "citations": [], "explanation": "The contract has no intellectual property clause."}
    assert _admit(absent)["status"] == "non_compliant"
    assert _admit(absent, complete=False)["reason_code"] == "clause_absent_terms_incomplete"


def test_missing_duplicate_or_stale_conclusions_are_undetermined():
    assert _admit(None)["reason_code"] == "judgement_missing"
    assert admit_judgements([IP], CLAUSES, True, [GOOD, GOOD])[0]["reason_code"] == "judgement_missing"
    assert _admit(GOOD, stale=True)["reason_code"] == "judgement_stale"


def test_a_new_legal_version_marks_the_frozen_conclusions_stale(tmp_path, demo, monkeypatch):
    legal = _copy(tmp_path) / "legal-requirements.yaml"
    legal.write_text(legal.read_text(encoding="utf-8").replace("version: 1", "version: 2"), encoding="utf-8")
    monkeypatch.setattr(settings, "quotation_cases_path", str(tmp_path / "q/quotes.yaml"))
    case = demo.get(f"/quotation/cases/{B}").json()
    assert case["compliance"]["legal_version"] == 2 and case["compliance"]["judgement"]["stale"] is True
    model = [r for r in case["compliance"]["requirements"] if r["decided_by"] == "model"]
    assert model and all(r["reason_code"] == "judgement_stale" for r in model)
