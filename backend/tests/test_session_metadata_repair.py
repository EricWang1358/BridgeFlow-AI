"""A compatibility repair may mark known metadata, never rewrite native history."""
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location("repair_metadata", Path(__file__).resolve().parents[2] / "scripts/repair_session_metadata.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_check_is_read_only_and_apply_keeps_exact_backup_and_event_payloads(tmp_path):
    root = tmp_path / "sessions"
    path = root / "workspace" / "session" / "session.jsonl"
    path.parent.mkdir(parents=True)
    events = [{"type": "session/header", "id": "id", "version": 0},
              {"type": "bridgeflow/review", "seq": 0, "data": {"status": "partial"}},
              {"type": "bridgeflow/approval-note", "seq": 1, "data": {"note": "Check owner"}},
              {"type": "approval/decided", "seq": 2, "data": {"outcome": "rejected"}},
              {"type": "unknown-required", "seq": 3, "data": {}}]
    original = "".join(json.dumps(event) + "\n" for event in events).encode()
    path.write_bytes(original)
    assert module.repair(root)["events"] == 2
    assert path.read_bytes() == original
    result = module.repair(root, apply=True)
    assert (Path(result["backup"]) / path.relative_to(root)).read_bytes() == original
    repaired = [json.loads(line) for line in path.read_bytes().splitlines()]
    for index, event in enumerate(repaired):
        assert event == events[index] | ({"ignorable": True} if index in (1, 2) else {})
    assert module.repair(root, apply=True)["files"] == 0
