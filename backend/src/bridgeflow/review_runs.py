"""Durable identity and terminal state for one department review (#112, #113).

The host plugin orchestrates a review in memory: the captain opens it, four official
subagents answer, the captain finalizes. Memory is the wrong place for the facts
people rely on afterwards — which review this was, when it had to finish, and how it
ended — because a restart or a lost response would otherwise leave a review showing
"dispatching" forever, or let a late success overwrite a timeout.

So every review is registered here when it opens, with its deadline, and ends exactly
once with a saved report and a reason:

- `completed`        the captain finalized in time;
- `deadline_exceeded` the deadline passed first — whatever arrives later cannot turn it
                      into a success;
- `captain_ended` / `captain_disposed` the parent turn or session ended first;
- `host_restarted`   the host came back and found the review still open.

Finalizing twice returns the report already saved. That is what makes retries after a
lost response, and races between a timeout and a late finalize, harmless.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from bridgeflow.store import _root, _write

TerminalReason = Literal["completed", "deadline_exceeded", "captain_ended", "captain_disposed", "host_restarted"]
_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")


class ReviewRun(BaseModel):
    review_id: str
    batch_id: str
    parent_session_id: str
    opened_at: str
    deadline_at: str
    status: Literal["open", "finalized"] = "open"
    report_id: str = ""
    terminal_reason: str = ""
    finalized_at: str = ""


class RunError(Exception):
    pass


def _now() -> datetime:
    return datetime.now(UTC)


def _path(review_id: str) -> Path:
    if not _ID.fullmatch(review_id):
        raise RunError("Invalid review id")
    return _root() / "review-runs" / f"{review_id}.json"


def get(review_id: str) -> ReviewRun | None:
    path = _path(review_id)
    return ReviewRun.model_validate_json(path.read_text(encoding="utf-8")) if path.is_file() else None


def open_run(review_id: str, batch_id: str, parent_session_id: str, deadline_seconds: int) -> ReviewRun:
    existing = get(review_id)
    if existing is not None:
        if (existing.batch_id, existing.parent_session_id) != (batch_id, parent_session_id):
            raise RunError("Review id already belongs to another batch or session")
        return existing
    opened = _now()
    run = ReviewRun(review_id=review_id, batch_id=batch_id, parent_session_id=parent_session_id,
                    opened_at=opened.isoformat(), deadline_at=(opened + timedelta(seconds=deadline_seconds)).isoformat())
    _write(_path(review_id), run.model_dump())
    return run


def expired(run: ReviewRun, now: datetime | None = None) -> bool:
    return (now or _now()) > datetime.fromisoformat(run.deadline_at)


def close(run: ReviewRun, report_id: str, reason: str) -> ReviewRun:
    run = run.model_copy(update={"status": "finalized", "report_id": report_id, "terminal_reason": reason,
                                 "finalized_at": _now().isoformat()})
    _write(_path(run.review_id), run.model_dump())
    return run


def open_runs() -> list[ReviewRun]:
    folder = _root() / "review-runs"
    if not folder.is_dir():
        return []
    runs = [ReviewRun.model_validate_json(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))]
    return [run for run in runs if run.status == "open"]


# --- human notes on a saved report (#111) ------------------------------------------


class HumanNote(BaseModel):
    note_id: str
    report_id: str
    batch_id: str
    parent_session_id: str
    note: str
    recorded_at: str


def notes_path(batch_id: str, report_id: str) -> Path:
    return _root() / "batches" / "reviews" / batch_id / "notes" / f"{report_id}.json"


def notes(batch_id: str, report_id: str) -> list[HumanNote]:
    path = notes_path(batch_id, report_id)
    if not path.is_file():
        return []
    return [HumanNote.model_validate(n) for n in json.loads(path.read_text(encoding="utf-8"))]


def add_note(note: HumanNote) -> tuple[list[HumanNote], bool]:
    """Append once per note id. A repeated submission is acknowledged, never counted twice."""
    existing = notes(note.batch_id, note.report_id)
    if any(n.note_id == note.note_id for n in existing):
        return existing, False
    updated = [*existing, note]
    _write(notes_path(note.batch_id, note.report_id), [n.model_dump() for n in updated])  # type: ignore[arg-type]
    return updated, True
