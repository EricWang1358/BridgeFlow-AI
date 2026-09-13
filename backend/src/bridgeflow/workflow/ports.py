"""Where records go and how people are told — behind protocols, chosen by declaration.

The company's data platform and messaging are not decided (#144, #140). The use cases
therefore depend on two small protocols, and adapters are selected from the
catalogue. The local adapters exist so the whole flow is exercisable on one machine;
the unconfigured adapters exist so a missing integration says so instead of pretending.
A Feishu or warehouse adapter is one more class here, not a change to the use cases.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from bridgeflow.workflow.catalogue import NotifierSpec, SinkSpec


class SinkError(Exception):
    """The target system refused or could not be reached. Nothing is marked ready."""


class IdempotencyConflict(SinkError):
    """The same submission key was already used for different content."""


@dataclass(frozen=True)
class Receipt:
    system: str
    record_id: str
    key: str
    #: True when this key had already been accepted with the same content.
    replayed: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {"system": self.system, "record_id": self.record_id, "key": self.key, "replayed": self.replayed}


class RecordSink(Protocol):
    name: str

    def submit(self, key: str, record: dict[str, Any]) -> Receipt:
        """Store one standard record. Must be idempotent on `key`."""
        ...


class Notifier(Protocol):
    name: str

    def deliver(self, recipient_role: str, message: str, dedupe: str) -> None:
        """Deliver or raise. Returning means the channel accepted it — not that it was read."""
        ...


class LocalSqliteSink:
    """A stand-in data platform: a separate SQLite file with an idempotent insert."""

    name = "local_sqlite"

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS records (key TEXT PRIMARY KEY, digest TEXT NOT NULL, "
                               "body TEXT NOT NULL)")

    def submit(self, key: str, record: dict[str, Any]) -> Receipt:
        body = json.dumps(record, ensure_ascii=False, sort_keys=True)
        digest = hashlib.sha256(body.encode()).hexdigest()
        with sqlite3.connect(self.path) as connection:
            existing = connection.execute("SELECT digest, rowid FROM records WHERE key = ?", (key,)).fetchone()
            if existing is not None:
                if existing[0] != digest:
                    raise IdempotencyConflict("This submission key was already used for different content")
                return Receipt(self.name, str(existing[1]), key, replayed=True)
            cursor = connection.execute("INSERT INTO records (key, digest, body) VALUES (?, ?, ?)", (key, digest, body))
            return Receipt(self.name, str(cursor.lastrowid), key)

    def count(self) -> int:
        with sqlite3.connect(self.path) as connection:
            return int(connection.execute("SELECT COUNT(*) FROM records").fetchone()[0])


class UnconfiguredSink:
    name = "unconfigured"

    def submit(self, key: str, record: dict[str, Any]) -> Receipt:
        raise SinkError("No target system is configured for standard records")


class LocalOutboxNotifier:
    """Records what would be sent. No message leaves the machine."""

    name = "local_outbox"

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS deliveries (dedupe TEXT PRIMARY KEY, role TEXT, message TEXT)")

    def deliver(self, recipient_role: str, message: str, dedupe: str) -> None:
        with sqlite3.connect(self.path) as connection:
            connection.execute("INSERT OR IGNORE INTO deliveries VALUES (?, ?, ?)", (dedupe, recipient_role, message))


class UnconfiguredNotifier:
    name = "unconfigured"

    def deliver(self, recipient_role: str, message: str, dedupe: str) -> None:
        raise SinkError("No notification channel is configured")


def sink_for(spec: SinkSpec, root: Path) -> RecordSink:
    return LocalSqliteSink(root / "workflow-platform.sqlite3") if spec.kind == "local_sqlite" else UnconfiguredSink()


def notifier_for(spec: NotifierSpec, root: Path) -> Notifier:
    return LocalOutboxNotifier(root / "workflow-deliveries.sqlite3") if spec.kind == "local_outbox" else UnconfiguredNotifier()
