"""The English display glossary: served as data, complete for the integration declaration, optional."""

from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from bridgeflow.api.main import app
from bridgeflow.config import REPO_ROOT, settings

SPEC = yaml.safe_load((REPO_ROOT / "data/company_templates/integration.yaml").read_text(encoding="utf-8"))


def _glossed(names: dict, name: str) -> bool:
    """A master column reads either by its own entry or as department + field."""
    if name in names:
        return True
    head, _, rest = name.partition("_")
    return bool(rest) and head in names and rest in names


def test_every_declared_name_and_assumption_has_an_english_display_name():
    with TestClient(app) as client:
        labels = client.get("/labels").json()
    declared = [*SPEC["fields"], *SPEC.get("derived", {}), *SPEC.get("constants", {}), *SPEC.get("classifications", {})]
    assert [name for name in declared if not _glossed(labels["names"], name)] == []
    assert [key for key, text in SPEC["assumptions"].items() if text not in labels["texts"]] == []
    assert labels["names"]["客户名称"] == "Customer name"


def test_a_missing_glossary_shows_the_declared_names_rather_than_failing(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(settings, "display_labels_path", str(tmp_path / "absent.yaml"))
    with TestClient(app) as client:
        response = client.get("/labels")
    assert response.status_code == 200
    assert response.json() == {"names": {}, "texts": {}}
