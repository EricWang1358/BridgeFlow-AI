"""Rehearse the dictionary draft lifecycle against a real OA dictionary spreadsheet.

Not a test — a rehearsal harness. It runs the whole product path in-process
(TestClient, mock LLM, temp stores) with your real 字典.xlsx:

  empty dictionary → 4-department import frozen at needs_configuration
  → dictionary_import transcribes the real spreadsheet
  → every entry decided by an explicit, printed policy (standing in for the person)
  → publish writes a new dictionary version
  → the same files import again and join
  → the first batch keeps its frozen (empty) dictionary

Two scenarios run back to back:

  A. only 项目名称 survives as the join key (other entity entries rejected) —
     mirrors the entity-only dictionary hand-written on production 2026-09-21;
  B. 项目编号 is accepted TOO — the trap the real sheet sets (its OA row claims
     项目编号 is now a four-department key, but the production upload has no such
     column, and in finance it precedes 项目名称). With the declaration-order fix
     the master table must still align on 项目名称 (3 rows), not silently split.

Usage:
    python scripts/rehearse_dictionary_draft.py /path/to/字典.xlsx [--period 2025-07]

Run from backend/ with its venv: `cd backend && .venv/bin/python ../scripts/rehearse_dictionary_draft.py ...`
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import tempfile
import time
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend/src"))

import yaml  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from bridgeflow.config import settings  # noqa: E402

TEMP = Path(tempfile.mkdtemp(prefix="bf-dict-rehearsal-"))
TOKEN = "rehearsal-host-secret-32-characters!"
PERIOD = "2025-07"


def receipt(body: bytes) -> str:
    """The same approval receipt mint the test suite uses (portal off, host auth only)."""
    stamp, nonce = str(int(time.time())), uuid.uuid4().hex
    message = f"{stamp}.{nonce}.{hashlib.sha256(body).hexdigest()}"
    signature = hashlib.sha256 if False else None  # noqa: F841 — keep the shape obvious
    import hmac
    return f"{stamp}.{nonce}.{hmac.new(TOKEN.encode(), message.encode(), hashlib.sha256).hexdigest()}"


def post(client: TestClient, path: str, payload: dict) -> dict:
    body = json.dumps(payload, separators=(",", ":")).encode()
    response = client.post(path, content=body, headers={
        "content-type": "application/json", "x-bridgeflow-approval": receipt(body)})
    assert response.status_code == 200, f"{path} -> {response.status_code}: {response.text[:400]}"
    return response.json()


# --- the four uploads: headers mimicking the real production sheets -----------------
# 项目名称 is the only value space all four share. 项目编号 exists in finance/
# marketing/物资 but NOT in production (the fact that makes it a hijack risk).
# production's period arrives as two columns (年份, 报表月) per the OA row 年份+报表月.

PROJECTS = ["城东搅拌站", "机场高速", "地下管廊"]

def csv_bytes(rows: list[dict]) -> bytes:
    header = list(rows[0])
    lines = [",".join(header)]
    lines += [",".join(str(row[column]) for column in header) for row in rows]
    return ("\n".join(lines) + "\n").encode()


def rows_for(department: str) -> list[dict]:
    period = PERIOD
    if department == "finance":
        return [{"项目编号": f"PRJ-{i:03d}", "项目名称": name, "报表年月": period,
                 "期初金额": 1000 + i, "本期借方金额": 200 + i, "期初方向": "借"}
                for i, name in enumerate(PROJECTS)]
    if department == "marketing":
        return [{"项目编号": f"PRJ-{i:03d}", "项目名称": name, "报表年月": period,
                 "客户名称": f"客户{chr(65 + i)}", "数量": 10 + i}
                for i, name in enumerate(PROJECTS)]
    if department == "procurement":
        return [{"项目名称": name, "报表年月": period, "数量": 5 + i, "单价": 12.5}
                for i, name in enumerate(PROJECTS)]
    return [{"项目名称": name, "年份": period[:4], "报表月": period[5:], "产量": 100 + i}
            for i, name in enumerate(PROJECTS)]


class FakeDrive:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    async def download(self, token: str) -> tuple[str, bytes]:
        return "字典.xlsx", self.payload

    async def close(self) -> None:
        pass


def bootstrap() -> TestClient:
    settings.llm_provider = "mock"
    settings.bridgeflow_service_token = TOKEN
    settings.portal_base_url = ""
    settings.bridgeflow_allow_mapping_write = True
    settings.field_dictionary_path = str(TEMP / "field-dictionary.yaml")
    settings.dictionary_draft_path = str(TEMP / "dictionary-drafts")
    settings.result_store_path = str(TEMP / "outputs")
    settings.column_match_path = str(TEMP / "column-matches.json")
    settings.mapping_memory_path = str(TEMP / "mappings.json")
    from bridgeflow.api.main import app
    return TestClient(app, headers={"authorization": f"Bearer {TOKEN}"})


FILES = ("finance", "marketing", "procurement", "production")


def import_batch(client: TestClient) -> dict:
    files = [("files", (f"{dept}.csv", csv_bytes(rows_for(dept)), "text/csv")) for dept in FILES]
    response = client.post("/batches", data={"period": PERIOD, "departments": list(FILES)}, files=files)
    assert response.status_code == 200, response.text[:400]
    return response.json()


def import_dictionary(client: TestClient, payload: bytes) -> dict:
    from bridgeflow.api import dictionary_tools
    dictionary_tools._client = lambda: FakeDrive(payload)  # noqa: SLF001 — rehearsal seam
    return post(client, "/tools/dictionary-import", {"file_token": "tok-000000"})


def decide(client: TestClient, draft_id: str, entry: dict, decision: str, **fields) -> None:
    post(client, "/tools/dictionary-draft-decide", {
        "draft_id": draft_id, "entry_id": entry["entry_id"], "decision": decision,
        "reason": fields.pop("reason", "彩排脚本代行（真实使用中由人逐条决定）"), **fields})


def policy(entry: dict, join_keys: set[str]) -> tuple[str, dict]:
    """The rehearsal's stand-in for the person. Every choice is printed with its why."""
    role, column = entry["role"], entry["column"]
    kind = role.split(":", 1)[1] if role.startswith("entity:") else ""
    if kind in join_keys and column in {alias for key in join_keys for alias in (key,)}:
        return "accepted", {}
    if role == "entity:报表年月" and column == "报表年月":
        return "modified", {"role": "period"}
    if role.startswith("entity:"):
        return "rejected", {"reason": "非本批唯一连接键（避免连接键漂移），彩排中拒绝"}
    return "rejected", {"reason": "度量汇总口径待业务确认——与现行 prod 实体字典同一立场"}


def run_scenario(client: TestClient, xlsx: bytes, name: str, join_keys: set[str], expect_master_rows: int) -> None:
    print(f"\n=== 场景 {name}：连接键 = {sorted(join_keys)} ===")
    frozen = import_batch(client)
    assert frozen["status"] == "needs_configuration", frozen
    print(f"[1] 空字典导入 → {frozen['status']} ✓  refusal: {frozen['refusal'][:60]}…")

    draft = import_dictionary(client, xlsx)
    print(f"[2] 转写 → {draft['entries']} 条（待决 {draft['pending']}），覆盖 {draft['departments']}，"
          f"缺失 {draft['missing_departments']}，未映射 {draft['unmapped']}")

    view = post(client, "/tools/dictionary-draft-view", {"draft_id": draft["draft_id"]})
    entries = view["entries"]
    for entry in entries:
        decision, fields = policy(entry, join_keys)
        decide(client, draft["draft_id"], entry, decision, **fields)
    by_decision: dict[str, int] = {}
    for entry in entries:
        decided = next(e for e in post(client, "/tools/dictionary-draft-view",
                                       {"draft_id": draft["draft_id"]})["entries"]
                       if e["entry_id"] == entry["entry_id"])
        by_decision[decided["decision"]] = by_decision.get(decided["decision"], 0) + 1
    print(f"[3] 逐条决定 → {by_decision}")

    published = post(client, "/tools/dictionary-draft-publish", {"draft_id": draft["draft_id"]})
    final = yaml.safe_load(Path(settings.field_dictionary_path).read_text(encoding="utf-8"))
    print(f"[4] 发布 → {published['version']}")
    print(f"    columns: " + json.dumps(final.get("columns", {}), ensure_ascii=False))
    print(f"    period_columns: {json.dumps(final.get('period_columns', {}), ensure_ascii=False)}")

    again = import_batch(client)
    status = again["status"]
    assert status != "needs_configuration", f"重新导入仍被拒: {again['refusal']}"
    print(f"[5] 重新导入 → {status}，主表 {again['master_rows']} 行（预期 {expect_master_rows}）")
    assert again["master_rows"] == expect_master_rows, \
        f"主表 {again['master_rows']} 行 ≠ {expect_master_rows}——四部门没有对齐在同一连接键上"

    still = client.get(f"/batches/{frozen['batch_id']}").json()
    assert still["status"] == "needs_configuration" and still["declared_entities"] == {}
    print(f"[6] 旧批次保持冻结 ✓（{still['status']}，声明 {still['declared_entities']}）")


def main() -> None:
    global PERIOD
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xlsx", type=Path, help="真实的 OA 字典表（.xlsx）")
    parser.add_argument("--period", default=PERIOD)
    args = parser.parse_args()
    PERIOD = args.period

    payload = args.xlsx.read_bytes()
    print(f"字典文件：{args.xlsx}（{len(payload)} 字节）")

    # 静态解析统计：不建批次，只看转写器在这份真实文件上产出什么。
    from bridgeflow import dictionary_draft
    entries, unmapped, notes, covered = dictionary_draft.parse_oa_bytes(payload, args.xlsx.name)
    print(f"\n=== 静态转写统计 ===\n条目 {len(entries)}，未映射 {len(unmapped)}，覆盖部门 {covered}")
    print(f"说明：{notes}")
    by_role: dict[str, int] = {}
    for entry in entries:
        key = entry.role.split(":")[0]
        by_role[key] = by_role.get(key, 0) + 1
    print(f"角色分布：{by_role}")
    print("实体 kind 明细（连接键候选）：")
    for kind in sorted({entry.role.split(":", 1)[1] for entry in entries if entry.role.startswith("entity:")}):
        depts = sorted(entry.department for entry in entries
                       if entry.role == f"entity:{kind}")
        print(f"  entity:{kind} × {len(depts)} 部门（{', '.join(depts)}）")
    print(f"未映射 {len(unmapped)} 条（全部留痕，不静默丢弃），前 5 条：")
    for row in unmapped[:5]:
        print(f"  · {row.label} [{row.department}]：{row.reason}")

    client = bootstrap()
    with client:
        run_scenario(client, payload, "A（仅保留项目名称——复刻 prod 实体字典立场）", {"项目名称"}, 3)
        # 场景 B 前清掉 A 发布的字典，回到空字典起点。
        Path(settings.field_dictionary_path).unlink(missing_ok=True)
        for stale in (TEMP / "dictionary-drafts").glob("*.json"):
            stale.unlink()
        run_scenario(client, payload, "B（项目编号也保留——验证劫持陷阱被字典序防住）", {"项目名称", "项目编号"}, 3)
    print("\n两个场景全部通过。本地彩排结论：转写 → 逐条决定 → 发布 → 重导入对齐，全链路成立。")


if __name__ == "__main__":
    main()
