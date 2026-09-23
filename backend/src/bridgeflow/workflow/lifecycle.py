"""The only place a status may change: explicit state machines over recorded events.

Three things move independently and must not be confused (#144's status table):

- an **artifact** — the material one department supplies, from received to data ready;
- a **handoff** — one downstream stage's work on it, from waiting to done;
- a **notification** — telling that stage, from pending to sent or failed.

A file uploaded is not data ready; data ready is not notified; notified is not
downstream done. Each machine is a transition table, and state is only ever obtained
by replaying events through it, so an impossible history cannot be stored.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ArtifactState(StrEnum):
    NEEDS_INPUT = "needs_input"
    READY_FOR_REVIEW = "ready_for_review"
    REVIEWED = "reviewed"
    SUBMITTING = "submitting"
    SUBMIT_FAILED = "submit_failed"
    DATA_READY = "data_ready"


class HandoffState(StrEnum):
    WAITING = "waiting"            # downstream may start
    IN_PROGRESS = "in_progress"
    RETURNED = "returned"          # sent back upstream with a reason
    COMPLETED = "completed"


class NotificationState(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"              # retryable until attempts run out
    ABANDONED = "abandoned"        # attempts exhausted; needs a person


class TransitionError(Exception):
    """An event that the current state does not allow."""


@dataclass(frozen=True)
class Event:
    type: str
    data: Mapping[str, Any] = field(default_factory=dict)
    at: str = ""
    seq: int = 0


# --- artifact -----------------------------------------------------------------------

#: Event → states it may follow. `None` stands for "nothing recorded yet".
#: `evaluated` is not listed: its target depends on the draft, see `ArtifactMachine`.
_ARTIFACT: dict[str, set[ArtifactState | None]] = {
    "material_received": {None},
    # New information is always welcome, and always re-opens review: approval was
    # given to specific values, not to the artifact in general.
    "answer_provided": {ArtifactState.NEEDS_INPUT, ArtifactState.READY_FOR_REVIEW, ArtifactState.REVIEWED,
                        ArtifactState.SUBMIT_FAILED, ArtifactState.DATA_READY},
    "reviewed": {ArtifactState.READY_FOR_REVIEW},
    "submission_started": {ArtifactState.REVIEWED, ArtifactState.SUBMIT_FAILED},
    "submission_succeeded": {ArtifactState.SUBMITTING},
    "submission_failed": {ArtifactState.SUBMITTING},
}


@dataclass
class ArtifactView:
    state: ArtifactState | None = None
    #: Increments when data that was already ready is revised.
    version: int = 1
    reviewed_digest: str = ""
    receipt: dict[str, Any] | None = None
    question_rounds: int = 0
    failures: int = 0


class ArtifactMachine:
    """Replays artifact events. Completeness of the draft decides where evaluation lands."""

    @staticmethod
    def next(view: ArtifactView, event: Event, *, complete: bool) -> ArtifactView:
        allowed = _ARTIFACT.get(event.type)
        if allowed is None:
            raise TransitionError(f"Unknown artifact event {event.type}")
        if view.state not in allowed:
            raise TransitionError(f"{event.type} is not allowed from {view.state}")
        evaluated = ArtifactState.READY_FOR_REVIEW if complete else ArtifactState.NEEDS_INPUT
        if event.type == "material_received":
            view.state = evaluated
        elif event.type == "answer_provided":
            if view.state is ArtifactState.DATA_READY:
                view.version += 1
                view.receipt = None
            view.question_rounds += 1
            view.reviewed_digest = ""
            view.state = evaluated
        elif event.type == "reviewed":
            view.reviewed_digest = str(event.data["digest"])
            view.state = ArtifactState.REVIEWED
        elif event.type == "submission_started":
            view.state = ArtifactState.SUBMITTING
        elif event.type == "submission_succeeded":
            view.receipt = dict(event.data["receipt"])
            view.state = ArtifactState.DATA_READY
        elif event.type == "submission_failed":
            view.failures += 1
            view.state = ArtifactState.SUBMIT_FAILED
        return view

    @classmethod
    def replay(cls, events: Iterable[Event], completeness: Iterable[bool]) -> ArtifactView:
        view = ArtifactView()
        for event, complete in zip(events, completeness, strict=True):
            view = cls.next(view, event, complete=complete)
        return view


# --- handoff ------------------------------------------------------------------------

_HANDOFF: dict[str, tuple[set[HandoffState | None], HandoffState]] = {
    "handoff_opened": ({None, HandoffState.RETURNED}, HandoffState.WAITING),
    "handoff_started": ({HandoffState.WAITING}, HandoffState.IN_PROGRESS),
    "handoff_returned": ({HandoffState.WAITING, HandoffState.IN_PROGRESS}, HandoffState.RETURNED),
    "handoff_completed": ({HandoffState.IN_PROGRESS}, HandoffState.COMPLETED),
}


@dataclass
class HandoffView:
    state: HandoffState | None = None
    #: The artifact versions this handoff was opened on, so a revision is visible.
    inputs: dict[str, int] = field(default_factory=dict)
    stale: bool = False
    reason: str = ""


class HandoffMachine:
    @staticmethod
    def next(view: HandoffView, event: Event) -> HandoffView:
        if event.type == "upstream_revised":
            # Not a transition: the work continues, but on something that changed.
            # Carries the new versions once the revision is data ready again; while it
            # is still being revised it only marks the handoff stale.
            if view.state is None:
                raise TransitionError("upstream_revised is not allowed before the handoff opened")
            if "inputs" in event.data:
                view.inputs = {str(k): int(v) for k, v in dict(event.data["inputs"]).items()}
            view.stale = True
            return view
        if event.type == "revision_acknowledged":
            if not view.stale:
                raise TransitionError("There is no upstream revision to acknowledge")
            view.stale = False
            return view
        rule = _HANDOFF.get(event.type)
        if rule is None:
            raise TransitionError(f"Unknown handoff event {event.type}")
        allowed, target = rule
        if view.state not in allowed:
            raise TransitionError(f"{event.type} is not allowed from {view.state}")
        if event.type == "handoff_opened":
            view.inputs = {str(k): int(v) for k, v in dict(event.data["inputs"]).items()}
            view.stale = False
            view.reason = ""
        # A return and a completion both rest on what a person stated; keep the latest so the
        # handoff shows why it is where it is (the full history stays in the event log).
        if event.type in ("handoff_returned", "handoff_completed"):
            view.reason = str(event.data.get("reason", ""))
        view.state = target
        return view

    @classmethod
    def replay(cls, events: Iterable[Event]) -> HandoffView:
        view = HandoffView()
        for event in events:
            view = cls.next(view, event)
        return view


# --- notification -------------------------------------------------------------------


def notification_after(state: NotificationState, delivered: bool, attempts: int, limit: int) -> NotificationState:
    """Where a delivery attempt leaves a notification. Sent is final; failed retries."""
    if state not in (NotificationState.PENDING, NotificationState.FAILED):
        raise TransitionError(f"Cannot attempt delivery from {state}")
    if delivered:
        return NotificationState.SENT
    return NotificationState.ABANDONED if attempts >= limit else NotificationState.FAILED
