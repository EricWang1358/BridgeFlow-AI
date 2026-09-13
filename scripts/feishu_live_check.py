"""One real round trip against a Feishu tenant, for #140 acceptance.

Uploads a small synthetic workbook into a test folder, downloads it back by the returned
token and checks the bytes are identical. Nothing from the repository's data is sent.

Credentials come only from the launching shell, never from a file in the repository:

    export FEISHU_APP_ID=... FEISHU_APP_SECRET=...   # self-built app with drive:drive permission
    export FEISHU_TEST_FOLDER=...                    # token of a folder shared with the app
    python scripts/feishu_live_check.py

Without them it says what is missing and exits 2. Tokens and secrets are never printed.
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import os
import sys
import time
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))
from bridgeflow import feishu


def _workbook() -> bytes:
    book = openpyxl.Workbook()
    book.active.append(["check", "value"])
    book.active.append(["bridgeflow-feishu-live-check", time.strftime("%Y-%m-%dT%H:%M:%S")])
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


async def main() -> int:
    missing = [v for v in ("FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_TEST_FOLDER") if not os.environ.get(v)]
    if missing:
        print(json.dumps({"status": "not_configured", "missing": missing}))
        return 2
    drive = feishu.FeishuDrive(os.environ["FEISHU_APP_ID"], os.environ["FEISHU_APP_SECRET"],
                               os.environ.get("FEISHU_BASE_URL", "https://open.feishu.cn"))
    payload = _workbook()
    started = time.monotonic()
    try:
        token = await drive.upload(os.environ["FEISHU_TEST_FOLDER"], "bridgeflow-live-check.xlsx", payload)
        uploaded = time.monotonic()
        name, content = await drive.download(token)
    except feishu.FeishuError as exc:
        print(json.dumps({"status": "refused", "reason": str(exc)}, ensure_ascii=False))
        return 1
    finally:
        await drive.close()
    same = hashlib.sha256(content).digest() == hashlib.sha256(payload).digest()
    print(json.dumps({"status": "passed" if same else "content_differs", "bytes": len(payload),
                      "downloaded_name": name, "upload_seconds": round(uploaded - started, 2),
                      "round_trip_seconds": round(time.monotonic() - started, 2)}, ensure_ascii=False))
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
