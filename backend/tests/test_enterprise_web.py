import json

import pytest
from conftest import receipt
from fastapi.testclient import TestClient

from bridgeflow.api.main import app
from bridgeflow.config import settings


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "bridgeflow_allow_sample_data", False)
    monkeypatch.setattr(settings, "bridgeflow_enable_legacy_console", False)
    with TestClient(app) as client:
        yield client


def upload(client, quantity=17):
    return client.post("/batches", data={"period": "2025-11", "departments": "production"},
                       files={"files": ("production.csv", f"sku,output_qty\nSKU-A1,{quantity}\n", "text/csv")})


def test_authentication_cannot_be_replaced_by_cors(client):
    client.headers.clear()
    assert client.post("/tools/list-metrics", json={}).status_code == 401
    assert upload(client).status_code == 401


def test_missing_host_configuration_is_closed(client, monkeypatch):
    monkeypatch.setattr(settings, "bridgeflow_service_token", "")
    assert client.post("/tools/list-metrics", json={}).status_code == 503


def test_legacy_console_and_sample_fallback_are_disabled(client):
    assert client.get("/console").status_code == 403
    assert client.post("/tools/aggregate-metric", json={"period": "2025-11", "metric": "total_output"}).status_code == 409


def test_immutable_batch_changes_the_answer_and_reloads(client):
    a, b = upload(client, 17), upload(client, 29)
    assert a.status_code == b.status_code == 200, (a.text, b.text)
    for result, expected in ((a.json(), 17), (b.json(), 29)):
        response = client.post("/tools/aggregate-metric", json={
            "batch_id": result["batch_id"], "period": "2025-11", "metric": "total_output",
        })
        assert response.status_code == 200, response.text
        assert response.json()["value"] == expected
        assert client.get(f'/batches/{result["batch_id"]}').json()["period"] == "2025-11"
    assert a.json()["batch_id"] != b.json()["batch_id"]


def test_invalid_period_and_duplicate_department_are_refused(client):
    assert client.post("/batches", data={"period": "../secret", "departments": "production"},
                       files={"files": ("a.csv", "sku,output_qty\nA,1")}).status_code == 422
    response = client.post("/batches", data={"period": "2025-11", "departments": ["production", "production"]},
                           files=[("files", ("a.csv", "sku,output_qty\nA,1")), ("files", ("b.csv", "sku,output_qty\nA,2"))])
    assert response.status_code == 422


def test_bounded_summary_never_contains_rows(client):
    result = upload(client).json()
    summary = client.post("/tools/batch-summary", json={"batch_id": result["batch_id"]}).json()
    assert "SKU-A1" not in json.dumps(summary)
    assert summary["departments"][0]["rows"] == 1


def test_unknown_metric_provides_supported_names(client):
    result = upload(client).json()
    response = client.post("/tools/aggregate-metric", json={"batch_id": result["batch_id"],
        "period": "2025-11", "metric": "moonbeam"})
    assert response.status_code == 409
    assert "total_output" in response.json()["detail"]


def test_dictionary_and_refusal_are_frozen_with_the_batch(client, monkeypatch, tmp_path):
    first = upload(client).json()
    missing = tmp_path / "missing.yaml"
    monkeypatch.setattr(settings, "field_dictionary_path", str(missing))
    assert client.post("/tools/aggregate-metric", json={"batch_id": first["batch_id"],
        "period": "2025-11", "metric": "total_output"}).json()["value"] == 17
    assert any(m["name"] == "total_output" for m in client.post("/tools/list-metrics", json={
        "batch_id": first["batch_id"],
    }).json()["metrics"])
    second = upload(client).json()
    assert second["status"] == "needs_configuration"
    assert "not configured" in second["refusal"]
    assert client.get(f'/batches/{second["batch_id"]}').json() == second
    assert client.get(f'/batches/{second["batch_id"]}/view').json()["total"] == 0


def test_ambiguous_date_is_preserved_in_quarantine_and_blocks_partial_total(client):
    result = client.post("/batches", data={"period": "2025-11", "departments": "production"},
        files={"files": ("dates.csv", "sku,date,output_qty\nA,2025-11-03,17\nB,03/11/2025,29\n")}).json()
    assert result["status"] == "needs_review"
    assert result["departments"][0]["quarantined"] == 1
    assert result["master_rows"] == 1
    assert client.get(f'/batches/{result["batch_id"]}/view?section=quarantine').json()["rows"][0]["values"]["date"] == "03/11/2025"
    response = client.post("/tools/aggregate-metric", json={"batch_id": result["batch_id"],
        "period": "2025-11", "metric": "total_output"})
    assert response.status_code == 409
    assert "quarantined" in response.text


def test_write_requires_payload_bound_one_use_approval(client):
    payload = {"source": "sku:a", "target": "customer:b", "relation": "ordered_by", "accepted": True}
    assert client.post("/tools/confirm-mapping", json=payload).status_code == 403
    body = json.dumps(payload).encode()
    headers = {"content-type": "application/json", "x-bridgeflow-approval": receipt(body)}
    changed = body.replace(b'sku:a', b'sku:c')
    assert client.post("/tools/confirm-mapping", content=changed, headers=headers).status_code == 403
    accepted = client.post("/tools/confirm-mapping", content=body, headers=headers)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["authorised_by"] == "dsh-authenticated-session"
    assert client.post("/tools/confirm-mapping", content=body, headers=headers).status_code == 403


def test_deployment_can_disable_writes_even_with_approval(client, monkeypatch):
    monkeypatch.setattr(settings, "bridgeflow_allow_mapping_write", False)
    body = json.dumps({"source": "a", "target": "b", "relation": "r", "accepted": True}).encode()
    assert client.post("/tools/confirm-mapping", content=body, headers={
        "content-type": "application/json", "x-bridgeflow-approval": receipt(body),
    }).status_code == 403


@pytest.mark.parametrize("contents", ["columns: [unclosed", "- field", "columns: text", "relations: [{}]"])
def test_malformed_dictionary_is_an_actionable_configuration_failure(client, monkeypatch, tmp_path, contents):
    dictionary = tmp_path / "invalid.yaml"
    dictionary.write_text(contents)
    monkeypatch.setattr(settings, "field_dictionary_path", str(dictionary))
    response = upload(client)
    assert response.status_code == 503
    assert "dictionary configuration is invalid" in response.json()["detail"]


def test_original_sources_are_immutable_paginated_and_not_tool_payloads(client):
    from hashlib import sha256

    from bridgeflow.api.batches import batch_path

    raw = 'sku,date,output_qty\n' + ''.join(f'RAW-{i},03/11/2025,{i}\n' for i in range(65))
    first = client.post('/batches', data={'period': '2025-11', 'departments': 'production'},
                        files={'files': ('../original.csv', raw, 'text/csv')}).json()['batch_id']
    second = upload(client, 29).json()['batch_id']
    listing = client.get(f'/batches/{first}/sources').json()
    assert listing['sources'][0]['filename'] == 'original.csv'
    assert listing['sources'][0]['sha256'] == sha256(raw.encode()).hexdigest()
    assert 'RAW-0' not in json.dumps(listing)
    assert listing['sources'][0]['total'] == 65
    page = client.get(f'/batches/{first}/sources/production?offset=50&limit=10').json()
    assert len(page['rows']) == 10
    assert page['rows'][0] == ['RAW-50', '03/11/2025', 50]
    assert page['total'] == 65
    assert client.get(f'/batches/{first}/sources/production?limit=101').status_code == 422
    assert client.get(f'/batches/{first}/sources/finance').status_code == 404
    assert client.get(f'/batches/{first}/sources/not-a-department').status_code == 422
    assert client.get(f'/batches/{second}/sources/production').json()['rows'] == [['SKU-A1', 29]]
    tool = client.post('/tools/batch-summary', json={'batch_id': first}).json()
    assert 'RAW-50' not in json.dumps(tool)
    assert 'sources' not in json.loads(batch_path(first).read_text())
    client.headers.clear()
    assert client.get(f'/batches/{first}/sources').status_code == 401
    assert client.get(f'/batches/{first}/sources/production').status_code == 401
    assert client.get(f'/batches/{first}/artifacts').status_code == 401


def test_older_batch_does_not_masquerade_cleaned_data_as_original(client):
    from bridgeflow.api.batches import batch_path

    batch = upload(client).json()['batch_id']
    (batch_path(batch).parent / 'sources' / batch / 'production.json').unlink()
    source = client.get(f'/batches/{batch}/sources').json()['sources'][0]
    assert source['preview_available'] is False
    assert client.get(f'/batches/{batch}/sources/production').status_code == 404


def test_original_xlsx_preview_preserves_sheet_and_precleaning_values(client):
    import io

    import pandas as pd

    buffer = io.BytesIO()
    pd.DataFrame({'sku': [' sku-a1 '], 'output_qty': [17]}).to_excel(buffer, sheet_name='Original', index=False)
    response = client.post('/batches', data={'period': '2025-11', 'departments': 'production'},
                           files={'files': ('source.xlsx', buffer.getvalue())})
    assert response.status_code == 200
    source = client.get(f'/batches/{response.json()["batch_id"]}/sources/production').json()
    assert source['sheet'] == 'Original'
    assert source['rows'] == [[' sku-a1 ', 17]]


def test_explicit_demo_freezes_its_own_dictionary_without_changing_deployment(client, monkeypatch, tmp_path):
    """A sample must work even when the real deployment is unconfigured."""
    from bridgeflow.api.batches import load_batch
    from bridgeflow.config import settings

    path = str(tmp_path / "real-dictionary-not-configured.yaml")
    monkeypatch.setattr(settings, "field_dictionary_path", path)
    response = client.post("/batches/demo")
    assert response.status_code == 200
    value = response.json()
    assert value["master_rows"] > 0
    assert value["dictionary"] == "data/mock_business/demo/dictionary.yaml"
    assert settings.field_dictionary_path == path
    batch = load_batch(value["batch_id"])
    assert batch.demo_case == "mock-company-2024-07"
    assert "business_review" in batch.dictionary_snapshot
    sources = client.get(f"/batches/{value['batch_id']}/sources").json()["sources"]
    assert len(sources) == 4
    assert all(source["filename"].startswith("模拟-") and source["preview_available"] for source in sources)
    assert client.post("/batches/demo", headers={"authorization":"Bearer invalid"}).status_code == 401
