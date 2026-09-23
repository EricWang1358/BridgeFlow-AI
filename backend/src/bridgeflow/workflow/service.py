"""Use cases: receive, answer, review, submit, hand off, notify.

The API calls this module and nothing below it. Each command reads a stream, asks the
state machine whether the event is legal, and appends — so a rule about what may
happen next lives in `lifecycle`, and a rule about what a value means lives in
`intake`, and neither is re-implemented here.

Submission is the one step that talks to another system, and it is ordered so every
failure is recoverable:

1. `submission_started` is recorded, so a second submit cannot race the first;
2. the sink is called with a key derived from artifact, version and reviewed digest,
   so repeating the call after a crash cannot create a second record;
3. `submission_succeeded`, any handoff it completes, and the notifications those
   handoffs need are committed in one transaction (`store.commit`).

An artifact left in `submitting` by a crash is resumed by submitting again: step 1 is
skipped and step 2 returns the receipt the sink already issued.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from bridgeflow.workflow import intake
from bridgeflow.workflow.catalogue import Catalogue, CatalogueError, TemplateSpec
from bridgeflow.workflow.lifecycle import (
    ArtifactMachine,
    ArtifactState,
    ArtifactView,
    Event,
    HandoffMachine,
    HandoffState,
    HandoffView,
    NotificationState,
    TransitionError,
    notification_after,
)
from bridgeflow.workflow.ports import Notifier, RecordSink, SinkError
from bridgeflow.workflow.store import Notification, Pending, WorkflowStore

Clock = Callable[[], datetime]


class NotFound(Exception):
    pass


class StaleRead(Exception):
    """The caller acted on a version of the draft that is no longer current."""


@dataclass
class ArtifactSnapshot:
    id: str
    template: str
    spec: TemplateSpec
    view: ArtifactView
    draft: intake.Draft
    observations: list[intake.Observation]
    seq: int
    updated_at: str

    @property
    def key(self) -> tuple[str, ...]:
        values = self.draft.business_key(self.spec)
        return tuple(values.get(name, "") for name in self.spec.business_key)


@dataclass
class HandoffSnapshot:
    id: str
    stage: str
    key: tuple[str, ...]
    view: HandoffView
    seq: int
    updated_at: str
    events: list[Event] = field(default_factory=list)


def _key_hash(key: tuple[str, ...]) -> str:
    return hashlib.sha256(json.dumps(key, ensure_ascii=False).encode()).hexdigest()[:16]


logger = logging.getLogger(__name__)


class WorkflowService:
    def __init__(self, catalogue: Catalogue, store: WorkflowStore, sink: RecordSink, notifier: Notifier,
                 clock: Clock = lambda: datetime.now(UTC)) -> None:
        self.catalogue, self.store, self.sink, self.notifier, self.clock = catalogue, store, sink, notifier, clock

    def _now(self) -> str:
        return self.clock().isoformat()

    # --- artifacts -------------------------------------------------------------------

    def artifact(self, artifact_id: str) -> ArtifactSnapshot:
        events = self.store.read(f"artifact:{artifact_id}")
        if not events:
            raise NotFound(f"Artifact {artifact_id} not found")
        template = str(events[0].data["template"])
        spec = self.catalogue.templates.get(template)
        if spec is None:
            raise CatalogueError(f"Artifact {artifact_id} uses template {template}, no longer declared")
        observations: list[intake.Observation] = []
        completeness: list[bool] = []
        draft = intake.evaluate(template, spec, [])
        for event in events:
            if event.type in ("material_received", "answer_provided"):
                observations += [intake.Observation.model_validate(o) for o in event.data["observations"]]
                draft = intake.evaluate(template, spec, observations)
            completeness.append(draft.complete)
        view = ArtifactMachine.replay(events, completeness)
        return ArtifactSnapshot(artifact_id, template, spec, view, draft, observations,
                                seq=events[-1].seq, updated_at=events[-1].at)

    def artifacts(self) -> list[ArtifactSnapshot]:
        return [self.artifact(stream.split(":", 1)[1]) for stream in self.store.streams("artifact:")]

    def receive(self, template: str, observations: list[intake.Observation]) -> ArtifactSnapshot:
        spec = self.catalogue.runnable(template)
        artifact_id = uuid.uuid4().hex
        event = Event("material_received", {
            "template": template, "template_version": spec.version,
            "observations": [o.model_dump(mode="json") for o in observations]})
        self._append(f"artifact:{artifact_id}", 0, [event])
        return self.artifact(artifact_id)

    def answer(self, artifact_id: str, observations: list[intake.Observation], expected_seq: int) -> ArtifactSnapshot:
        current = self.artifact(artifact_id)
        self.catalogue.runnable(current.template)
        # An answer is the person settling the field, so it replaces what was there.
        corrected = [o.model_copy(update={"correction": True}) for o in observations]
        self._transition(current, Event("answer_provided", {"observations": [o.model_dump(mode="json") for o in corrected]}),
                         expected_seq)
        snapshot = self.artifact(artifact_id)
        if current.view.state is ArtifactState.DATA_READY:
            self._flag_revision(snapshot)
        return snapshot

    def review(self, artifact_id: str, digest: str, reviewer: str, expected_seq: int) -> ArtifactSnapshot:
        current = self.artifact(artifact_id)
        if digest != current.draft.digest:
            raise StaleRead("The draft changed since it was shown; review the current values")
        self._transition(current, Event("reviewed", {"digest": digest, "by": reviewer}), expected_seq)
        return self.artifact(artifact_id)

    def submit(self, artifact_id: str) -> ArtifactSnapshot:
        current = self.artifact(artifact_id)
        self.catalogue.runnable(current.template)
        if current.view.state is not ArtifactState.SUBMITTING:
            if current.view.state not in (ArtifactState.REVIEWED, ArtifactState.SUBMIT_FAILED):
                raise TransitionError(f"Cannot submit from {current.view.state}")
            if current.view.reviewed_digest != current.draft.digest:
                raise StaleRead("The reviewed values are not the current values; review again")
            current = self._transition(current, Event("submission_started", {"digest": current.draft.digest}),
                                       current.seq)

        key = hashlib.sha256(f"{artifact_id}:{current.view.version}:{current.draft.digest}".encode()).hexdigest()
        try:
            receipt = self.sink.submit(key, self._record(current))
        except SinkError as exc:
            self._transition(current, Event("submission_failed", {"error": str(exc)}), current.seq)
            return self.artifact(artifact_id)

        succeeded = Event("submission_succeeded", {"receipt": receipt.as_dict(), "version": current.view.version})
        ArtifactMachine.next(current.view, succeeded, complete=True)  # legality, before any write
        pending = [Pending(f"artifact:{artifact_id}", current.seq, [succeeded])]
        notices: list[tuple[str, str, str, str]] = []
        ready = self._ready_versions(extra=(current.template, current.key, current.view.version))
        for stage in self.catalogue.consumers(current.template):
            self._plan_handoff(stage, current.key, ready, pending, notices)
        self.store.commit(pending, notices, at=self._now())
        return self.artifact(artifact_id)

    def _record(self, snapshot: ArtifactSnapshot) -> dict:
        draft = snapshot.draft
        return {
            "artifact_id": snapshot.id, "template": snapshot.template, "template_version": draft.template_version,
            "version": snapshot.view.version, "business_key": list(snapshot.key),
            "values": {k: v.value for k, v in draft.values.items()}, "derived": draft.derived,
            "provenance": {k: {"source": v.source.model_dump(), "evidence": v.evidence, "note": v.note}
                           for k, v in draft.values.items()},
            "reviewed_digest": snapshot.view.reviewed_digest,
        }

    def _transition(self, current: ArtifactSnapshot, event: Event, expected_seq: int) -> ArtifactSnapshot:
        if expected_seq != current.seq:
            raise StaleRead(f"Artifact is at {current.seq}, request was based on {expected_seq}")
        # Legality is checked on a copy before the write; a refused event is never stored.
        probe = ArtifactView(**vars(current.view))
        ArtifactMachine.next(probe, event, complete=current.draft.complete)
        self._append(f"artifact:{current.id}", current.seq, [event])
        return self.artifact(current.id)

    def _append(self, stream: str, expected: int, events: list[Event]) -> None:
        self.store.commit([Pending(stream, expected, events)], at=self._now())

    # --- handoffs --------------------------------------------------------------------

    def handoff(self, handoff_id: str) -> HandoffSnapshot:
        stream = f"handoff:{handoff_id}"
        events = self.store.read(stream)
        if not events:
            raise NotFound(f"Handoff {handoff_id} not found")
        opened = events[0].data
        return HandoffSnapshot(handoff_id, str(opened["stage"]), tuple(opened["business_key"]),
                               HandoffMachine.replay(events), events[-1].seq, events[-1].at, events)

    def handoffs(self) -> list[HandoffSnapshot]:
        return [self.handoff(stream.split(":", 1)[1]) for stream in self.store.streams("handoff:")]

    def act(self, handoff_id: str, action: str, reason: str, expected_seq: int) -> HandoffSnapshot:
        types = {"start": "handoff_started", "return": "handoff_returned", "complete": "handoff_completed",
                 "acknowledge": "revision_acknowledged"}
        if action not in types:
            raise TransitionError(f"Unknown handoff action {action}")
        if action == "return" and not reason.strip():
            raise TransitionError("Returning work upstream needs a reason the upstream department can act on")
        current = self.handoff(handoff_id)
        if expected_seq != current.seq:
            raise StaleRead(f"Handoff is at {current.seq}, request was based on {expected_seq}")
        if action in {"start", "complete"} and current.view.stale:
            raise TransitionError("Acknowledge the ready upstream revision before continuing work")
        if action == "acknowledge":
            ready = self._ready_versions()
            if any(ready.get((template, current.key)) != version
                   for template, version in current.view.inputs.items()):
                raise TransitionError("Upstream inputs are not ready at the handoff's current versions")
        event = Event(types[action], {"reason": reason.strip()})
        HandoffMachine.next(HandoffView(**{**vars(current.view), "inputs": dict(current.view.inputs)}), event)
        self._append(f"handoff:{handoff_id}", current.seq, [event])
        return self.handoff(handoff_id)

    def _ready_versions(self, extra: tuple[str, tuple[str, ...], int] | None = None) -> dict[tuple[str, tuple[str, ...]], int]:
        """Latest data-ready version per (template, business key)."""
        ready: dict[tuple[str, tuple[str, ...]], int] = {}
        for snapshot in self.artifacts():
            if snapshot.view.state is ArtifactState.DATA_READY:
                slot = (snapshot.template, snapshot.key)
                ready[slot] = max(ready.get(slot, 0), snapshot.view.version)
        if extra is not None:
            template, key, version = extra
            ready[(template, key)] = max(ready.get((template, key), 0), version)
        return ready

    def missing_inputs(self, stage: str, key: tuple[str, ...]) -> list[str]:
        ready = self._ready_versions()
        return [t for t in self.catalogue.stages[stage].inputs if (t, key) not in ready]

    def _plan_handoff(self, stage: str, key: tuple[str, ...], ready: dict[tuple[str, tuple[str, ...]], int],
                      pending: list[Pending], notices: list[tuple[str, str, str, str]]) -> None:
        spec = self.catalogue.stages[stage]
        inputs = {t: ready[(t, key)] for t in spec.inputs if (t, key) in ready}
        if len(inputs) != len(spec.inputs):
            return  # partial: the board says what is still awaited; nobody is told "ready"
        handoff_id = f"{stage}:{_key_hash(key)}"
        stream = f"handoff:{handoff_id}"
        events = self.store.read(stream)
        view = HandoffMachine.replay(events)
        shown = " · ".join(key)
        titles = "、".join(f"{self.catalogue.templates[t].department}「{self.catalogue.templates[t].title}」v{v}"
                          for t, v in inputs.items())
        if view.state in (None, HandoffState.RETURNED):
            pending.append(Pending(stream, len(events), [Event("handoff_opened", {
                "stage": stage, "business_key": list(key), "inputs": inputs})]))
            notices.append((f"{stream}:opened:{len(events) + 1}", stream, spec.owner_role,
                            f"{titles} 数据已就绪（{shown}），请{spec.department}{spec.action or '继续处理'}。"))
        elif view.inputs != inputs:
            pending.append(Pending(stream, len(events), [Event("upstream_revised", {"inputs": inputs})]))
            notices.append((f"{stream}:revised:{json.dumps(inputs, sort_keys=True)}", stream, spec.owner_role,
                            f"上游数据已修订：{titles}（{shown}），请{spec.department}按新版本复核。"))

    def _flag_revision(self, snapshot: ArtifactSnapshot) -> None:
        """Data that was ready is being revised: say so on every handoff built on it."""
        for stage in self.catalogue.consumers(snapshot.template):
            stream = f"handoff:{stage}:{_key_hash(snapshot.key)}"
            events = self.store.read(stream)
            view = HandoffMachine.replay(events)
            if view.state in (HandoffState.WAITING, HandoffState.IN_PROGRESS, HandoffState.COMPLETED) and not view.stale:
                self.store.commit([Pending(stream, len(events), [
                    Event("upstream_revised", {"revising": snapshot.template})])], at=self._now())

    # --- notifications ---------------------------------------------------------------

    def deliver_pending(self) -> None:
        """Deliver what a write just queued, without letting delivery undo the write.

        The record is already in the target system when this runs; a notifier that is down
        leaves the notice pending or failed for the next attempt (the outbox pattern), and
        nothing here may turn a successful submission into an error.
        """
        try:
            self.dispatch()
        except Exception:
            logger.warning("Notification delivery deferred", exc_info=True)

    def dispatch(self) -> list[Notification]:
        """Attempt every pending or retryable notification once."""
        limit = self.catalogue.adoption.max_notification_attempts
        for notice in self.store.notifications([NotificationState.PENDING, NotificationState.FAILED]):
            try:
                self.notifier.deliver(notice.recipient_role, notice.message, notice.dedupe)
                delivered, error = True, ""
            except SinkError as exc:
                delivered, error = False, str(exc)
            state = notification_after(notice.state, delivered, notice.attempts + 1, limit)
            self.store.record_attempt(notice, state, error, at=self._now())
        return self.store.notifications()
