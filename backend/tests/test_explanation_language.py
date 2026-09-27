"""Department explanations are written in the language the batch declares, and held to it (docs/38).

The English sample set once translated the finance role's forbidden topics while the agents still
wrote Chinese, so the topic check could never fire there. The language is now part of the frozen
review contract, and an explanation in another language is refused, not shown.
"""
import pytest
import yaml
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from bridgeflow import business
from bridgeflow.api.main import app
from bridgeflow.config import REPO_ROOT, settings

SETS = {"zh": "data/mock_business/sample-set.yaml", "en": "data/demo_en/sample-set.yaml"}


def use(monkeypatch, name: str, cases=None) -> None:
    declared = yaml.safe_load((REPO_ROOT / SETS[name]).read_text(encoding="utf-8"))
    monkeypatch.setattr(settings, "field_dictionary_path", str(REPO_ROOT / declared["dictionary"]))
    monkeypatch.setattr(settings, "integration_spec_path", str(REPO_ROOT / declared["integration_spec"]))
    monkeypatch.setattr(settings, "demo_cases_path", str(cases or REPO_ROOT / declared["demo_cases"]))


def packets(monkeypatch, name: str, cases=None):
    use(monkeypatch, name, cases)
    with TestClient(app) as client:
        batch = client.post("/batches/demo?case=clean")
        assert batch.status_code == 200, batch.text
        return client.post("/tools/review-context", json={"batch_id": batch.json()["batch_id"]})


def roles(monkeypatch, name: str) -> dict[str, dict]:
    response = packets(monkeypatch, name)
    assert response.status_code == 200, response.text
    return {p["role"]: p for p in response.json()["roles"]}


def answer(packet: dict, explanation: str) -> dict:
    return {"checks": [{"check_id": c["check_id"], "metric": c["metric"], "value": c["value"], "unit": c["unit"],
        "status": c["expected_status"], "action": c["actions"][c["expected_status"]][0], "explanation": explanation}
        for c in packet["checks"]]}


def test_each_set_declares_its_language_and_its_built_in_topics(monkeypatch):
    zh, en = roles(monkeypatch, "zh")["finance"], roles(monkeypatch, "en")["finance"]
    assert (zh["explanation"]["code"], zh["explanation"]["max_characters"]) == ("zh", 120)
    assert zh["explanation"]["threshold_term"] == "关注阈值" and "已批准上限" in zh["unsupported_topics"]
    assert (en["explanation"]["code"], en["explanation"]["language"], en["explanation"]["max_characters"]) == ("en", "English", 240)
    assert en["explanation"]["threshold_term"] == "attention threshold" and "approved limit" in en["unsupported_topics"]
    # The declared finance topics are the dictionary's own, translated with the set.
    assert "Impairment" in en["unsupported_topics"] and "减值" in zh["unsupported_topics"]


def test_an_undeclared_language_is_refused_not_defaulted(monkeypatch, tmp_path):
    declared = yaml.safe_load((REPO_ROOT / SETS["en"]).read_text(encoding="utf-8"))
    dictionary = yaml.safe_load((REPO_ROOT / declared["dictionary"]).read_text(encoding="utf-8"))
    dictionary["business_review"]["explanation_language"] = "fr"
    (tmp_path / "dictionary.yaml").write_text(yaml.safe_dump(dictionary, allow_unicode=True), encoding="utf-8")
    # The sample cases name their own dictionary; point a copy of the registry at the altered one.
    registry = yaml.safe_load((REPO_ROOT / declared["demo_cases"]).read_text(encoding="utf-8"))
    registry["dictionary"] = str(tmp_path / "dictionary.yaml")
    (tmp_path / "cases.yaml").write_text(yaml.safe_dump(registry, allow_unicode=True), encoding="utf-8")
    response = packets(monkeypatch, "en", tmp_path / "cases.yaml")
    assert response.status_code == 409 and "Unknown explanation language" in response.text


def test_english_set_accepts_english_and_refuses_everything_else(monkeypatch):
    finance = roles(monkeypatch, "en")["finance"]
    business.validate_role(finance, answer(finance, "Above the attention threshold; the finance director reviews "
                                                    "profit and collections within the department's scope."))
    refused = {
        "not written in English": "该值低于关注阈值，需由财务牵头复核。",
        "evidence scope": "Within the Approved Limit, so no action is needed.",
    }
    for reason, text in refused.items():
        with pytest.raises(HTTPException, match=reason):
            business.validate_role(finance, answer(finance, text))
    with pytest.raises(HTTPException, match="evidence scope"):
        business.validate_role(finance, answer(finance, "Margin is positive, so no impairment is needed."))
    business.validate_role(finance, answer(finance, "a" * 240))
    with pytest.raises(ValidationError, match="at most 240 characters"):
        business.validate_role(finance, answer(finance, "a" * 241))


def test_chinese_set_keeps_its_rules_and_cannot_be_sidestepped_in_english(monkeypatch):
    finance = roles(monkeypatch, "zh")["finance"]
    business.validate_role(finance, answer(finance, "应按本部门权限核实并提交责任人复核。"))
    refused = {
        "exceeds 120 characters": "应" * 121,
        "not written in Simplified Chinese": "Checked against the threshold; the owner reviews it.",
        # Another language's built-in topic inside a Chinese sentence is still a forbidden topic.
        "evidence scope": "客户账期在 approved limit 之内，无需处理。",
    }
    for reason, text in refused.items():
        with pytest.raises(HTTPException, match=reason):
            business.validate_role(finance, answer(finance, text))
