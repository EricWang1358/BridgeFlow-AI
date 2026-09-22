"""Rehearse the #245 walkthrough: batch_issues → quarantine_row → propose → approve → apply.

Not a test — a rehearsal harness, in-process (TestClient, temp stores, business_demo
fixtures with two planted bad rows and a renamed column). It walks exactly what the
captain will do for a person:

  batch_issues   — enumerate every open item with its settling tool
  quarantine_row — read one held row: values, headers as uploaded, provenance, checks
  propose        — a fix attributed to the captain, recorded only with an approval
  apply          — the derived batch; the frozen original untouched
  inbox + audit  — corrections aggregated as open items; every read logged

Usage (from backend/ with its venv):
    .venv/bin/python ../scripts/rehearse_issue_walkthrough.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import time
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend/src"))

from fastapi.testclient import TestClient  # noqa: E402

from bridgeflow.config import settings  # noqa: E402

TEMP = Path(tempfile.mkdtemp(prefix="bf-issue-rehearsal-"))
TOKEN = "rehearsal-host-secret-32-characters!"
CASES = REPO_ROOT / "data/business_demo"
ROLES = ("production", "procurement", "finance", "marketing")


def receipt(body: bytes) -> str:
    import hmac
    stamp, nonce = str(int(time.time())), uuid.uuid4().hex
    message = f"{stamp}.{nonce}.{hashlib.sha256(body).hexdigest()}"
    return f"{stamp}.{nonce}.{hmac.new(TOKEN.encode(), message.encode(), hashlib.sha256).hexdigest()}"


def post(client: TestClient, path: str, payload: dict, approve: bool = True) -> object:
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    headers = {"content-type": "application/json"}
    if approve:
        headers["x-bridgeflow-approval"] = receipt(body)
    response = client.post(path, content=body, headers=headers)
    assert response.status_code == 200, f"{path} -> {response.status_code}: {response.text[:300]}"
    return response.json()


def with_bad_rows(content: bytes) -> bytes:
    """An ambiguous date (quarantined + correction) and a mostly-blank row."""
    return (content.rstrip(b"\n") + b"\nSKU-B2,LINE-B,03/11/2025,30,20,20\n,,,,,7\n")


def with_renamed_project(content: bytes) -> bytes:
    header, rest = content.split(b"\n", 1)
    names = header.decode().split(",")
    return (",".join("project_code" if name == "project" else name for name in names) + "\n").encode() + rest


def bootstrap() -> TestClient:
    settings.llm_provider = "mock"
    settings.bridgeflow_service_token = TOKEN
    settings.portal_base_url = ""
    settings.field_dictionary_path = str(CASES / "dictionary.yaml")
    settings.dictionary_draft_path = str(TEMP / "dictionary-drafts")
    settings.cell_access_log_path = str(TEMP / "cell-access")
    settings.result_store_path = str(TEMP / "outputs")
    settings.column_match_path = str(TEMP / "column-matches.json")
    settings.mapping_memory_path = str(TEMP / "mappings.json")
    from bridgeflow.api.main import app
    return TestClient(app, headers={"authorization": f"Bearer {TOKEN}"})


def import_batch(client: TestClient) -> str:
    files = []
    replacements = {"production": with_bad_rows, "finance": with_renamed_project}
    for role in ROLES:
        content = replacements.get(role, lambda c: c)((CASES / "risk" / f"{role}.csv").read_bytes())
        files.append(("files", (f"{role}.csv", content, "text/csv")))
    response = client.post("/batches", data={"period": "2025-11", "departments": list(ROLES)}, files=files)
    assert response.status_code == 200, response.text[:300]
    return response.json()["batch_id"]


def main() -> None:
    client = bootstrap()
    with client:
        batch_id = import_batch(client)
        print(f"[0] 导入带问题批次 {batch_id[:8]}…（歧义日期行 + 空行 + finance 改列名）")

        issues = post(client, "/tools/batch-issues", {"batch_id": batch_id})
        print(f"[1] batch_issues → {issues['total']} 条待办 {issues['counts']}")
        for item in issues["items"][:6]:
            change = f"（{item['rule']}: {item['before']!r} → {item['after']!r}）" if item["before"] is not None else ""
            print(f"      · [{item['kind']}] {item['department'] or '—'}.{item['subject']}{change}")

        target = next(item for item in issues["items"] if item["kind"] == "quarantined_row"
                      and any("date" in c for c in item["checks"]))
        row = post(client, "/tools/quarantine-row", {
            "batch_id": batch_id, "department": target["department"], "index": int(target["subject"].split()[1])})
        print(f"[2] quarantine_row → {row['department']} 第 {row['index']} 行（{row['filename']}）")
        for name, value in row["values"].items():
            print(f"      · {row['original_columns'].get(name, name)} = {value!r}")
        print(f"      未过检查: {row['failing_checks']}")

        proposal = [{"column": "date", "value": "2025-11-03", "proposed_by": "captain",
                     "evidence": "同批 production 其余行均为 2025-11 上下文；03/11/2025 为日在前写法"}]
        decided = {"batch_id": batch_id, "department": row["department"], "index": row["index"],
                   "action": "release", "reason": "负责人确认：日期为 2025-11-03", "fixes": proposal,
                   "confirmed_by": "captain", "call_id": "c1"}
        body = json.dumps(decided, ensure_ascii=False).encode()
        refused = client.post("/tools/quarantine-decide", content=body,
                              headers={"content-type": "application/json"})
        assert refused.status_code == 403, "未审批的提议绝不能落账"
        print("[3] 提议未审批 → 403 ✓；人审批后：")
        post(client, "/tools/quarantine-decide", decided)

        applied = post(client, "/tools/quarantine-apply", {"batch_id": batch_id, "confirmed_by": "captain", "call_id": "a1"})
        derived = applied["batch"]
        print(f"[4] apply → 派生批次 {derived['batch_id'][:8]}…（{derived['status']}），旧批次冻结不动")

        from bridgeflow.api.batches import load_batch
        snapshot = load_batch(derived["batch_id"])
        fix = snapshot.dispositions[0]["fixes"][0]
        assert fix["proposed_by"] == "captain" and fix["evidence"]
        print(f"[5] 派生批次留痕：fix.proposed_by={fix['proposed_by']!r}, evidence={fix['evidence'][:30]}…")

        from bridgeflow.monthly import inbox
        items = inbox._intake_corrections(inbox.Context(
            batch_id=batch_id, period=snapshot.period, batch=load_batch(batch_id)))
        print(f"[6] 待办清单 corrections 聚合 → {[(i.subject, i.detail) for i in items]}")

        logs = list((TEMP / "cell-access").glob("*.jsonl"))
        assert logs, "读取没有落审计"
        entry = json.loads(logs[0].read_text(encoding="utf-8").splitlines()[0])
        print(f"[7] 单元格读取审计 → {entry['actor']} 读了 {entry['item']}（列 {entry['columns']}）")
    print("\n全链路成立：清单 → 读行 → 提议（未批拒绝）→ 人批 → 派生 → 留痕 → 清单聚合 → 审计。")


if __name__ == "__main__":
    main()
