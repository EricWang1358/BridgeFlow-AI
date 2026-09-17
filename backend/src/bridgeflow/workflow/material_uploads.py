"""Immutable, expiring uploads awaiting native registration approval."""
import hashlib
import json
import secrets
import sqlite3
import time
from pathlib import Path

from bridgeflow.workflow.discovery import DiscoveryError, MaterialInput

MAX_BYTES = 20 * 1024 * 1024


class UploadQuotaError(DiscoveryError):
    pass


class MaterialUploads:
    def __init__(self, path: Path, *, owner_count: int = 20,
                 owner_bytes: int = 100 * 1024 * 1024, total_bytes: int = 1024 * 1024 * 1024):
        if min(owner_count, owner_bytes, total_bytes) <= 0:
            raise ValueError("Upload quota limits must be positive")
        self.owner_count, self.owner_bytes, self.total_bytes = owner_count, owner_bytes, total_bytes
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS uploads (id TEXT PRIMARY KEY, metadata TEXT NOT NULL, "
                               "digest TEXT NOT NULL, payload BLOB NOT NULL, owner TEXT NOT NULL, expires REAL NOT NULL)")

    def stage(self, item: MaterialInput, payload: bytes, owner: str) -> dict:
        if not payload or len(payload) > MAX_BYTES:
            raise DiscoveryError("Material must contain 1 byte to 20 MiB")
        if Path(item.filename).name != item.filename or "\\" in item.filename:
            raise DiscoveryError("A filename, not a filesystem path, is required")
        identifier, digest = secrets.token_hex(32), hashlib.sha256(payload).hexdigest()
        expires = time.time() + 86400
        with sqlite3.connect(self.path) as connection:
            # Serialize quota checks and insertion across workers, not just threads.
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM uploads WHERE expires < ?", (time.time(),))
            count, used = connection.execute(
                "SELECT COUNT(*), COALESCE(SUM(length(payload)), 0) FROM uploads WHERE owner = ?", (owner,)).fetchone()
            total = connection.execute("SELECT COALESCE(SUM(length(payload)), 0) FROM uploads").fetchone()[0]
            if count >= self.owner_count or used + len(payload) > self.owner_bytes:
                raise UploadQuotaError("Pending material quota reached; register uploads or wait for expiry")
            if total + len(payload) > self.total_bytes:
                raise UploadQuotaError("Shared material staging quota reached; ask the operator to review pending uploads")
            connection.execute("INSERT INTO uploads VALUES (?, ?, ?, ?, ?, ?)",
                               (identifier, item.model_dump_json(), digest, payload, owner, expires))
        return {"upload_id": identifier, "digest": digest, "material": item.model_dump(),
                "expires_at": expires, "status": "awaiting_registration"}

    def read(self, identifier: str) -> tuple[MaterialInput, str, bytes]:
        with sqlite3.connect(self.path) as connection:
            row = connection.execute("SELECT metadata, digest, payload FROM uploads WHERE id = ? AND expires >= ?",
                                     (identifier, time.time())).fetchone()
        if row is None:
            raise DiscoveryError("Upload not found or expired; upload again")
        return MaterialInput.model_validate(json.loads(row[0])), row[1], row[2]

    def checked(self, identifier: str, item: MaterialInput, digest: str) -> bytes:
        saved, expected_digest, payload = self.read(identifier)
        if saved != item or digest != expected_digest or hashlib.sha256(payload).hexdigest() != digest:
            raise DiscoveryError("Uploaded content or registration metadata does not match")
        return payload

    def discard(self, identifier: str) -> None:
        with sqlite3.connect(self.path) as connection:
            connection.execute("DELETE FROM uploads WHERE id = ?", (identifier,))

    def cleanup(self, *, apply: bool = False) -> dict:
        """Delete only expired staging rows, never registered material events/blobs."""
        with sqlite3.connect(self.path) as connection:
            connection.execute("BEGIN IMMEDIATE" if apply else "BEGIN")
            cutoff = time.time()
            count, size = connection.execute(
                "SELECT COUNT(*), COALESCE(SUM(length(payload)), 0) FROM uploads WHERE expires < ?",
                (cutoff,)).fetchone()
            if apply:
                connection.execute("DELETE FROM uploads WHERE expires < ?", (cutoff,))
        return {"expired_count": count, "payload_bytes": size, "applied": apply}
