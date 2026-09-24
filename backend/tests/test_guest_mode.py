"""Guest mode (docs/22 §9e): an isolated instance for people without a Feishu account.

What these pin is the isolation, because the guest console is public by design: no Feishu or
portal credential reaches it, no model key reaches it unless the operator allowed guest AI,
and every path it writes lives under its own wiped root — including its own dictionary copy,
since publishing a dictionary rewrites the active file.
"""
import importlib.util
import os

import pytest
from fastapi.testclient import TestClient

from bridgeflow.api.main import app
from bridgeflow.config import REPO_ROOT, settings

spec = importlib.util.spec_from_file_location("start_web", REPO_ROOT / "scripts/start_web.py")
start_web = importlib.util.module_from_spec(spec)
spec.loader.exec_module(start_web)

OPERATOR = {"FEISHU_APP_ID": "cli", "FEISHU_APP_SECRET": "s", "PORTAL_SESSION_SECRET": "p",
            "PORTAL_BASE_URL": "http://portal", "DEEPSEEK_API_KEY": "k", "DEEPSEEK_BASE_URL": "http://llm",
            "HYPER_CHARM_API_KEY": "h", "DSH_PROVIDER": "deepseek-official", "DSH_MODEL": "m",
            "BRIDGEFLOW_SERVICE_TOKEN": "t" * 40, "PATH": "/usr/bin"}


@pytest.fixture
def guest_root(tmp_path, monkeypatch):
    root = tmp_path / "guest"
    monkeypatch.setattr(start_web, "GUEST_ROOT", root)
    monkeypatch.setenv("DSH_HOME", str(tmp_path / "operator-home"))
    (root / "stale").mkdir(parents=True)
    (root / "stale" / "left-over.json").write_text("{}", encoding="utf-8")
    return root


def test_a_guest_gets_no_credential_and_its_own_paths(guest_root):
    env = dict(OPERATOR)
    patch = start_web.guest_environment(env)
    assert not any(key.startswith(("FEISHU_", "PORTAL_", "DEEPSEEK_", "HYPER_", "DSH_PROVIDER", "DSH_MODEL")) for key in env)
    assert env["BRIDGEFLOW_SERVICE_TOKEN"] == OPERATOR["BRIDGEFLOW_SERVICE_TOKEN"] and env["PATH"] == "/usr/bin"
    assert env["BRIDGEFLOW_GUEST_MODE"] == "1" and env["BRIDGEFLOW_GUEST_LLM"] == "0"
    for key in ("RESULT_STORE_PATH", "MAPPING_MEMORY_PATH", "COLUMN_MATCH_PATH", "DICTIONARY_DRAFT_PATH",
                "FIELD_DICTIONARY_PATH", "DSH_HOME"):
        assert env[key].startswith(str(guest_root)), key
    assert not (guest_root / "stale").exists()  # wiped on every start
    text = patch.read_text(encoding="utf-8")
    assert "http://127.0.0.1:8001" in text and "http://127.0.0.1:8000" not in text
    assert "provider: bridgeflow-guest-notice" in text and "guest-model/index.ts" in text
    assert os.environ["DSH_HOME"] == env["DSH_HOME"]


def test_the_operator_can_allow_guest_ai_but_never_feishu(guest_root):
    env = {**OPERATOR, "BRIDGEFLOW_GUEST_LLM": "1"}
    patch = start_web.guest_environment(env)
    assert env["DEEPSEEK_API_KEY"] == "k" and env["BRIDGEFLOW_GUEST_LLM"] == "1"
    assert not any(key.startswith(("FEISHU_", "PORTAL_")) for key in env)
    assert "bridgeflow-guest-notice" not in patch.read_text(encoding="utf-8")


@pytest.mark.parametrize(("path", "data"), [
    ("/batches", {"period": "2024-07", "departments": "production"}),
    ("/batches/self-check", {"period": "2024-07", "department": "production"}),
    ("/batches/" + "0" * 32 + "/departments/production", {"period": "2024-07", "reason": "correction"}),
    ("/discovery/uploads", {"metadata": "{}"}),
    ("/workflow/materials/inspect", {}),
    ("/analyze", {"period": "2024-07", "departments": "production"}),
])
def test_guest_refuses_uploaded_files_before_any_are_saved(monkeypatch, tmp_path, path, data):
    monkeypatch.setattr(settings, "bridgeflow_guest_mode", True)
    monkeypatch.setattr(settings, "bridgeflow_enable_legacy_pipeline", True)
    monkeypatch.setattr(settings, "result_store_path", str(tmp_path / "guest-data"))
    with TestClient(app) as client:
        response = client.post(path, data=data, files={"file" if path not in ("/batches", "/analyze") else "files":
                                                   ("private.csv", b"not sample data", "text/csv")})
        assert response.status_code == 403 and "guest" in response.json()["detail"].lower(), (path, response.text)
    assert not list((tmp_path / "guest-data" / "batches").glob("*.json"))
    assert not (tmp_path / "guest-data" / "discovery-uploads.sqlite3").exists()


def test_guest_can_still_open_the_built_in_sample(monkeypatch):
    monkeypatch.setattr(settings, "bridgeflow_guest_mode", True)
    with TestClient(app) as client:
        response = client.post("/batches/demo?case=clean")
        assert response.status_code == 200, response.text
        assert response.json()["demo_case"] == "demo-clean-2024-07"
