"""Phase 0/3 reconnaissance for #204: read each configured wiki space's members from a real tenant.

Prints, per configured space: member count, member_type/member_role distribution,
and the shape of member ids (prefix only) — never raw ids or names. This confirms
the app has a sufficient scope (wiki:member:retrieve), that the app itself is a
member of every space (error 131006 otherwise), and which envelope key the API
answers with, before the backend depends on any of it.

Credentials come only from the launching shell, never from a file:

    export FEISHU_APP_ID=... FEISHU_APP_SECRET=...
    python scripts/feishu_membership_check.py [path-to-access-control.yaml]

Without them it says what is missing and exits 2.
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))
from bridgeflow import access_resolver
from bridgeflow.config import settings
from bridgeflow.feishu import FeishuError
from fastapi import HTTPException


def main() -> int:
    missing = [v for v in ("FEISHU_APP_ID", "FEISHU_APP_SECRET") if not os.environ.get(v)]
    if missing:
        print(json.dumps({"status": "not_configured", "missing": missing}))
        return 2
    if len(sys.argv) > 2:
        print(__doc__)
        return 2
    if len(sys.argv) == 2:
        settings.access_control_path = sys.argv[1]
    try:
        declared = access_resolver.structure()
    except HTTPException as exc:
        print(json.dumps({"status": "invalid_structure", "detail": exc.detail}, ensure_ascii=False))
        return 2
    spaces = {**{f"department:{k}": v["space_id"] for k, v in declared["spaces"]["departments"].items()},
              "master_office": declared["spaces"]["master_office"]["space_id"]}
    report = {"status": "ok", "spaces": {}}
    started = time.monotonic()
    for label, space_id in spaces.items():
        fetch_started = time.monotonic()
        try:
            members = access_resolver.fetch_space_members(space_id)
        except FeishuError as exc:
            report["spaces"][label] = {"status": "failed", "reason": str(exc)}
            report["status"] = "incomplete"
            continue
        report["spaces"][label] = {
            "status": "ok",
            "members": len(members),
            "roles": dict(Counter(members.values())),
            "id_prefixes": sorted({key[:3] for key in members}),
            "elapsed_s": round(time.monotonic() - fetch_started, 2),
        }
    report["elapsed_s"] = round(time.monotonic() - started, 2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
