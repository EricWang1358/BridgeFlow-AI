import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from test_discovery import material

from bridgeflow.workflow.material_uploads import MaterialUploads, UploadQuotaError


def test_owner_and_shared_quotas_do_not_overwrite_pending_files(tmp_path):
    uploads = MaterialUploads(tmp_path / "staging.db", owner_count=2, owner_bytes=8, total_bytes=10)
    first = uploads.stage(material(), b"12345", "alice")
    with pytest.raises(UploadQuotaError):
        uploads.stage(material(), b"6789", "alice")
    uploads.stage(material(), b"67890", "bob")
    with pytest.raises(UploadQuotaError):
        uploads.stage(material(), b"x", "carol")
    assert uploads.read(first["upload_id"])[2] == b"12345"
    uploads.discard(first["upload_id"])
    assert uploads.stage(material(), b"ok", "alice")["status"] == "awaiting_registration"


def test_concurrent_uploads_cannot_both_claim_last_quota_slot(tmp_path):
    path = tmp_path / "staging.db"
    MaterialUploads(path)
    def stage(_):
        try:
            return MaterialUploads(path, owner_count=1).stage(material(), b"a,b\n", "alice")["upload_id"]
        except UploadQuotaError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(stage, range(2)))
    assert sum(value is not None for value in results) == 1


def test_cleanup_preview_and_apply_only_affect_expired_staging(tmp_path):
    uploads = MaterialUploads(tmp_path / "staging.db", owner_count=1)
    old = uploads.stage(material(), b"old", "alice")
    with sqlite3.connect(uploads.path) as connection:
        connection.execute("UPDATE uploads SET expires = 0 WHERE id = ?", (old["upload_id"],))
    live = uploads.stage(material(), b"live", "bob")  # Opportunistic cleanup also releases expired quota.
    assert uploads.cleanup() == {"expired_count": 0, "payload_bytes": 0, "applied": False}
    expired = uploads.stage(material(), b"expire", "alice")
    with sqlite3.connect(uploads.path) as connection:
        connection.execute("UPDATE uploads SET expires = 0 WHERE id = ?", (expired["upload_id"],))
    assert uploads.cleanup()["expired_count"] == 1
    with sqlite3.connect(uploads.path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM uploads").fetchone()[0] == 2
    assert uploads.cleanup(apply=True) == {"expired_count": 1, "payload_bytes": 6, "applied": True}
    assert uploads.read(live["upload_id"])[2] == b"live"
    assert uploads.cleanup(apply=True)["expired_count"] == 0


def test_cleanup_cli_defaults_to_preview_and_requires_apply(tmp_path):
    import json
    import os
    import subprocess
    import sys

    from bridgeflow.config import REPO_ROOT

    root = tmp_path / "outputs"
    uploads = MaterialUploads(root / "discovery-uploads.sqlite3")
    uploads.stage(material(), b"expired", "alice")
    with sqlite3.connect(uploads.path) as connection:
        connection.execute("UPDATE uploads SET expires = 0")
    args = [sys.executable, str(REPO_ROOT / "scripts/cleanup_discovery_uploads.py")]
    env = {**os.environ, "RESULT_STORE_PATH": str(root)}
    preview = subprocess.run(args, env=env, capture_output=True, text=True, check=True)
    assert json.loads(preview.stdout) == {"expired_count": 1, "payload_bytes": 7, "applied": False}
    assert uploads.cleanup()["expired_count"] == 1
    applied = subprocess.run([*args, "--apply"], env=env, capture_output=True, text=True, check=True)
    assert json.loads(applied.stdout)["applied"]
    assert uploads.cleanup()["expired_count"] == 0
