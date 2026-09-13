"""Tests for the bodies behind the dsh tools.

The declarations live in `plugins/` and cannot be exercised from Python; what is
testable here is the half that decides figures and refusals, which is the half that
can be wrong quietly.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from bridgeflow.api.main import app
from bridgeflow.config import REPO_ROOT

EXAMPLE_DICTIONARY = REPO_ROOT / "data" / "mappings" / "field-dictionary.example.yaml"


@pytest.fixture
def client(monkeypatch):
    """A client whose field dictionary is the committed example, not the machine's.

    The real dictionary is gitignored, so a test that read it would pass or fail
    depending on whose laptop it ran on.
    """
    monkeypatch.setattr(
        "bridgeflow.config.settings.field_dictionary_path", str(EXAMPLE_DICTIONARY)
    )
    return TestClient(app)


@pytest.fixture
def client_without_dictionary(monkeypatch):
    monkeypatch.setattr(
        "bridgeflow.config.settings.field_dictionary_path", "does/not/exist.yaml"
    )
    return TestClient(app)


def test_a_metric_returns_the_rows_it_came_from(client):
    body = client.post(
        "/tools/aggregate-metric", json={"metric": "total_output", "period": "2025-11"}
    ).json()

    assert body["value"] > 0
    assert body["evidence"], "a figure with no source rows cannot be cited by a finding"
    assert all({"department", "row", "column", "value"} <= set(e) for e in body["evidence"])


def test_scoping_to_an_entity_narrows_both_value_and_evidence(client):
    everything = client.post(
        "/tools/aggregate-metric", json={"metric": "total_output", "period": "2025-11"}
    ).json()
    one_sku = client.post(
        "/tools/aggregate-metric",
        json={"metric": "total_output", "period": "2025-11", "entity": "SKU-A1"},
    ).json()

    assert one_sku["value"] < everything["value"]
    assert len(one_sku["evidence"]) < len(everything["evidence"])


def test_an_unknown_metric_is_refused_rather_than_guessed(client):
    response = client.post(
        "/tools/aggregate-metric", json={"metric": "ebitda_per_moonbeam", "period": "2025-11"}
    )

    assert response.status_code == 409
    assert "list_metrics" in response.json()["detail"]


def test_without_a_dictionary_nothing_is_computed(client_without_dictionary):
    response = client_without_dictionary.post(
        "/tools/aggregate-metric", json={"metric": "total_output", "period": "2025-11"}
    )

    assert response.status_code == 409, "guessing from column spelling is not a fallback"


def test_without_a_dictionary_no_metric_is_offered(client_without_dictionary):
    assert client_without_dictionary.post("/tools/list-metrics", json={}).json() == {"metrics": []}


def test_a_hint_match_is_never_reported_as_a_declaration(client_without_dictionary):
    """The trap this project keeps falling into.

    `FieldDictionary.kind_for` falls back to English column hints so the samples run.
    Reporting that as `declared` would tell the model a guess is a fact — and the
    customer's real export is unlikely to be in English.
    """
    body = client_without_dictionary.post(
        "/tools/lookup-field-dictionary", json={"department": "marketing", "column": "customer"}
    ).json()

    assert body["source"] == "unconfigured"
    assert body["kind"] is None


def test_a_declared_column_is_reported_as_declared(client):
    body = client.post(
        "/tools/lookup-field-dictionary", json={"department": "marketing", "column": "product"}
    ).json()

    assert body == {
        "department": "marketing",
        "column": "product",
        "kind": "sku",
        "source": "declared",
    }


def test_an_undeclared_column_is_not_inferred(client):
    body = client.post(
        "/tools/lookup-field-dictionary",
        json={"department": "marketing", "column": "some_column_oa_never_mentioned"},
    ).json()

    assert body["kind"] is None
    assert body["source"] == "undeclared"


def test_evidence_is_a_bounded_sample_not_the_whole_table(client):
    """The PRD sizes one batch at 200,000 rows.

    Keeping rows out of the prompt and then returning one entry per summed cell
    would move the leak into the tool result, where every agent in the fan-out pays
    for it separately.
    """
    from bridgeflow.api.tools import EVIDENCE_SAMPLE

    body = client.post(
        "/tools/aggregate-metric", json={"metric": "sales", "period": "2025-11"}
    ).json()

    assert len(body["evidence"]) <= EVIDENCE_SAMPLE
    assert body["evidence_total"] >= len(body["evidence"])
    assert body["evidence_truncated"] is (body["evidence_total"] > EVIDENCE_SAMPLE)
