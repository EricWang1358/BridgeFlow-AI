"""The demo dictionary carries the sample supplier's quotation declaration.

The Quotation workspace reads the active field dictionary. The demo runs on
data/mock_business/demo/dictionary.yaml, which once lacked the `quotation` section, so a
person opening Quotation in the demo met "not configured" — a dead end in the walkthrough.
The declaration itself is maintained beside its source documents in
data/mock_business/quotation/; the two copies must stay the same.
"""
import yaml
from fastapi.testclient import TestClient

from bridgeflow.api.main import app
from bridgeflow.config import REPO_ROOT, settings

DEMO = REPO_ROOT / "data/mock_business/demo/dictionary.yaml"
SOURCE = REPO_ROOT / "data/mock_business/quotation/dictionary.yaml"


def test_the_demo_quotation_section_is_the_supplier_declaration():
    demo = yaml.safe_load(DEMO.read_text(encoding="utf-8"))
    source = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
    assert demo["quotation"] == source["quotation"]


def test_the_quotation_workspace_is_configured_in_the_demo(monkeypatch):
    monkeypatch.setattr(settings, "field_dictionary_path", str(DEMO))
    contract = TestClient(app).get("/quotation/contract").json()
    assert contract["status"] == "awaiting_samples" and contract["contract"]["title"]
