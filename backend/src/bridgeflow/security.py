"""Host authentication and single-use, payload-bound DSH approval receipts."""

from __future__ import annotations

import hashlib
import hmac
import sqlite3
import time

from fastapi import HTTPException, Request

from bridgeflow.config import settings
from bridgeflow.store import _root


async def require_host(request: Request) -> None:
    secret = settings.bridgeflow_service_token
    if len(secret) < 32:
        raise HTTPException(503, "BridgeFlow host credential is not configured (32+ characters)")
    expected = f"Bearer {secret}"
    if not hmac.compare_digest(request.headers.get("authorization", "").encode(), expected.encode()):
        raise HTTPException(401, "DSH host authentication required")


def consume_approval(receipt: str, body: bytes, operation: str | None = None) -> str:
    """Validate before writing, with a durable unique nonce across workers/restarts.

    Portal mode additionally requires an exact-operation employee permit. The
    returned actor is verified by the backend, never copied from model arguments.
    """
    try:
        parts = receipt.split(".")
        if len(parts) not in (3, 4):
            raise ValueError("malformed")
        stamp, nonce, signature = parts[:3]
        permit = parts[3] if len(parts) == 4 else ""
        if settings.portal_base_url and not permit:
            raise ValueError("employee authorization missing")
        timestamp = int(stamp)
        if not 0 <= time.time() - timestamp <= 60 or len(nonce) != 32:
            raise ValueError("expired or malformed")
        message = f"{stamp}.{nonce}.{hashlib.sha256(body).hexdigest()}"
        if permit:
            message += f".{permit}"
        expected = hmac.new(
            settings.bridgeflow_service_token.encode(), message.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("payload mismatch")
    except (ValueError, TypeError) as exc:
        raise HTTPException(403, "A fresh DSH approval for this exact write is required") from exc
    path = _root() / "approval-receipts.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS receipts (nonce TEXT PRIMARY KEY, stamp INT)")
        actor = "dsh-authenticated-session"
        if permit:
            from bridgeflow.write_authorization import consume

            try:
                actor = consume(connection, permit, operation, body, nonce)
            except sqlite3.IntegrityError as exc:
                raise HTTPException(403, "Approval already consumed; request a new decision") from exc
        connection.execute("DELETE FROM receipts WHERE stamp < ?", (time.time() - 120,))
        try:
            connection.execute("INSERT INTO receipts VALUES (?, ?)", (nonce, timestamp))
        except sqlite3.IntegrityError as exc:
            raise HTTPException(403, "Approval already consumed; request a new decision") from exc
    return actor
