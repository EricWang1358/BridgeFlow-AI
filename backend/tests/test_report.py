"""The monthly report document (E13-UC04): generated from the brief, and never from stale data."""
import base64
import io
import re
import zipfile

import pytest
from fastapi.testclient import TestClient
from test_conclusions import finalize

from bridgeflow.api.main import app
from bridgeflow.config import REPO_ROOT, settings

DEMO = REPO_ROOT / "data/mock_business/demo"
SECTIONS = ["一、封面与绑定版本", "二、本月结论", "三、关键指标与对比", "四、各部门研判摘要",
            "五、需关注事项与负责人", "六、待确认事项", "七、口径假设与限制", "八、附录：出处索引"]


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "field_dictionary_path", str(DEMO / "dictionary.yaml"))
    monkeypatch.setattr(settings, "result_store_path", str(tmp_path))
    with TestClient(app) as test_client:
        yield test_client


def document(client, batch, report_id=None):
    response = client.get(f"/conclusions/batches/{batch}/report" + (f"?report_id={report_id}" if report_id else ""))
    assert response.status_code == 200, response.text
    body = response.json()
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(body["base64"]))) as archive:
        text = archive.read("word/document.xml").decode()
    return body, text


def test_the_document_has_every_declared_section_and_a_source_for_every_figure(client):
    batch = client.post("/batches/demo").json()["batch_id"]
    finalize(client, batch)
    body, text = document(client, batch)
    assert body["filename"].startswith("月度经营结论-2024-07-") and body["filename"].endswith(".docx")
    for section in SECTIONS:
        assert section in text, section
    cited = set(re.findall(r"\[S(\d+)\]", text))
    indexed = set(re.findall(r">S(\d+)<", text))
    assert cited and cited <= indexed, (cited, indexed)
    # The appendix entry carries the formula and how many cells the figure rests on.
    assert "个来源单元格" in text and "G2" in text


def test_the_conventions_the_figures_rest_on_are_listed_with_their_state(client):
    batch = client.post("/batches/demo").json()["batch_id"]
    finalize(client, batch)
    _body, text = document(client, batch)
    assert "增值税税率" in text and "未确认" in text
    # Confirming it changes what the report says about it, without changing any figure.
    import json

    from conftest import receipt
    payload = {"batch_id": batch, "convention": "增值税税率", "action": "confirm",
               "source": "财务部确认函", "confirmed_by": "captain"}
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    assert client.post("/tools/convention-decide", content=raw,
                       headers={"content-type": "application/json", "x-bridgeflow-approval": receipt(raw)}).status_code == 200
    _body, after = document(client, batch)
    assert "业务方已确认" in after and "财务部确认函" in after


def test_a_stale_brief_is_refused_instead_of_exporting_old_conclusions(client):
    batch = client.post("/batches/demo").json()["batch_id"]
    first = finalize(client, batch)
    finalize(client, batch)  # a newer review supersedes it
    stale = client.get(f"/conclusions/batches/{batch}/report?report_id={first['report_id']}")
    assert stale.status_code == 409 and "superseded" in stale.text
    assert client.get(f"/conclusions/batches/{batch}/report").status_code == 200


def test_a_partial_review_is_marked_on_the_cover(client):
    batch = client.post("/batches/demo").json()["batch_id"]
    finalize(client, batch, fail="finance")
    _body, text = document(client, batch)
    assert "部分完成" in text and "finance" in text


def test_the_file_opens_as_a_word_document(client):
    batch = client.post("/batches/demo").json()["batch_id"]
    finalize(client, batch)
    body, _text = document(client, batch)
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(body["base64"]))) as archive:
        assert set(archive.namelist()) == {"[Content_Types].xml", "_rels/.rels",
                                           "word/_rels/document.xml.rels", "word/styles.xml", "word/document.xml"}
        assert archive.testzip() is None
