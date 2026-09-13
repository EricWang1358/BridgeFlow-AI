"""Append-only events and a transactional outbox, in one SQLite file.

Events are the record of what happened; every status is replayed from them
(`lifecycle`). Appends use optimistic concurrency — the caller states the sequence it
read, and a concurrent writer makes the append fail rather than interleave.

The outbox is how "data ready" and "tell the next department" stay consistent: the
event that makes data ready and the notification it requires are written in the same
transaction, and a separate dispatcher delivers notifications with retries. A crash
between the two can therefore lose neither, and a retry can never send twice for the
same business event because each notification carries a unique dedupe key.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from bridgeflow.workflow.lifecycle import Event, NotificationState

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    stream TEXT NOT NULL, seq INTEGER NOT NULL, type TEXT NOT NULL,
    data TEXT NOT NULL, at TEXT NOT NULL, PRIMARY KEY (stream, seq));
CREATE TABLE IF NOT EXISTS outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT, dedupe TEXT NOT NULL UNIQUE,
    stream TEXT NOT NULL, recipient_role TEXT NOT NULL, message TEXT NOT NULL,
    state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL);
"""


class ConcurrencyError(Exception):
    """Somebody else appended to this stream since it was read."""


@dataclass(frozen=True)
class Notification:
    id: int
    dedupe: str
    stream: str
    recipient_role: str
    message: str
    state: NotificationState
    attempts: int
    last_error: str
    updated_at: str


@dataclass(frozen=True)
class Pending:
    """Events to append to one stream, guarded by the sequence the writer last saw."""

    stream: str
    expected: int
    events: Sequence[Event]


class WorkflowStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.execute("COMMIT")
        except BaseException:
            connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    # --- events ------------------------------------------------------------------

    def read(self, stream: str) -> list[Event]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT seq, type, data, at FROM events WHERE stream = ? ORDER BY seq", (stream,)).fetchall()
        return [Event(type=r["type"], data=json.loads(r["data"]), at=r["at"], seq=r["seq"]) for r in rows]

    def streams(self, prefix: str) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT stream, MIN(rowid) AS first FROM events WHERE stream LIKE ? GROUP BY stream ORDER BY first",
                (prefix.replace("%", r"\%") + "%",)).fetchall()
        return [r["stream"] for r in rows]

    def commit(self, pending: Sequence[Pending], notifications: Sequence[tuple[str, str, str, str]] = (),
               *, at: str) -> None:
        """Append to several streams and enqueue notifications, all or nothing.

        `notifications` are (dedupe, stream, recipient_role, message); a dedupe key that
        already exists is ignored, which is what makes replays of the same business
        event harmless.
        """
        with self.transaction() as connection:
            for item in pending:
                current = connection.execute(
                    "SELECT COALESCE(MAX(seq), 0) FROM events WHERE stream = ?", (item.stream,)).fetchone()[0]
                if current != item.expected:
                    raise ConcurrencyError(f"{item.stream} is at {current}, expected {item.expected}")
                for offset, event in enumerate(item.events, start=1):
                    connection.execute(
                        "INSERT INTO events (stream, seq, type, data, at) VALUES (?, ?, ?, ?, ?)",
                        (item.stream, current + offset, event.type,
                         json.dumps(dict(event.data), ensure_ascii=False, sort_keys=True), at))
            for dedupe, stream, role, message in notifications:
                connection.execute(
                    "INSERT OR IGNORE INTO outbox (dedupe, stream, recipient_role, message, state, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)", (dedupe, stream, role, message, NotificationState.PENDING, at))

    # --- outbox ------------------------------------------------------------------

    def notifications(self, states: Sequence[NotificationState] | None = None) -> list[Notification]:
        query, args = "SELECT * FROM outbox", ()
        if states:
            query += f" WHERE state IN ({','.join('?' * len(states))})"
            args = tuple(states)
        with self._connect() as connection:
            rows = connection.execute(query + " ORDER BY id", args).fetchall()
        return [Notification(id=r["id"], dedupe=r["dedupe"], stream=r["stream"], recipient_role=r["recipient_role"],
                             message=r["message"], state=NotificationState(r["state"]), attempts=r["attempts"],
                             last_error=r["last_error"], updated_at=r["updated_at"]) for r in rows]

    def record_attempt(self, notification: Notification, state: NotificationState, error: str, *, at: str) -> None:
        with self.transaction() as connection:
            updated = connection.execute(
                "UPDATE outbox SET state = ?, attempts = attempts + 1, last_error = ?, updated_at = ? "
                "WHERE id = ? AND attempts = ?", (state, error, at, notification.id, notification.attempts))
            if updated.rowcount != 1:
                raise ConcurrencyError(f"notification {notification.id} was attempted concurrently")
