"""The queue a person actually answers.

`ctx.approval` is fail-closed by construction: with no answerer composed, every ask
resolves `unavailable` and the tool is denied (`docs/13` §7.3). That is the right
posture for an unattended run, and it was what shipped in #39 — verified against the
live runtime, which refused `confirm_mapping` with

    tool "confirm_mapping" requires approval, but no approval channel is available

and wrote nothing. What it is *not* is a human in the loop. Nobody could say yes.

This module is the other half: a pending-decision queue that a `approval/request`
answerer publishes into and an operator console answers out of. Four properties are
load-bearing, and each of them is a way this could have been done wrong:

- **Fail closed stays fail closed.** Nothing here can produce `allowed-once` except
  a person calling `decide()`. A full queue, an expired question and a withdrawn one
  all end as refusals, because the answerer falls through the waterfall rather than
  inventing a grant. Absence of an operator must never read as consent.
- **The question is bounded.** It carries a tool name, a call id, a reason and a few
  short label/value pairs — never rows. The whole point of the 200,000-row scenario
  is that no part of the system quietly grows with the data (`CLAUDE.md`, seventh
  hard constraint), and an approval prompt is not an exception.
- **A withdrawn question cannot be answered late.** When the answerer gives up, the
  question leaves the console. An approval that lands after the tool call already
  failed is a confused deputy waiting to happen: the operator believes they are
  authorising the call they are looking at, and they are not.
- **Who decided is recorded, and is an assertion.** The console sends an operator
  name; there is no authentication behind it. `decided_by` is therefore evidence of
  *what a person claimed*, which is what a local demo can honestly offer, and it is
  written to the log either way so the claim is reviewable.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from bridgeflow.config import REPO_ROOT, settings

#: The only grant. Anything else denies.
GRANT = "allowed-once"

ApprovalOutcome = Literal["allowed-once", "rejected"]
ApprovalState = Literal["pending", "decided", "withdrawn"]

#: How many questions may wait at once. A queue that grows without bound is a way to
#: make the console unusable, and an unusable console is a way to make a tired
#: operator approve whatever is on top. Refusing the 33rd question is safer.
MAX_PENDING = 32

#: Per-value and total caps on what a question may carry to the console. The values
#: are model-authored tool arguments, so they are both untrusted and unbounded.
MAX_DETAIL_VALUE = 120
MAX_DETAIL_ITEMS = 12


class ApprovalDetail(BaseModel):
    """One label/value pair the operator reads before deciding.

    The label is an argument name from the tool's own declaration, not a spreadsheet
    field name — nothing here is a schema commitment (`CLAUDE.md`, eighth constraint).
    """

    label: str
    value: str


class ApprovalQuestion(BaseModel):
    """A decision waiting for a person."""

    id: str
    tool_name: str
    call_id: str | None = None
    reason: str = ""
    detail: list[ApprovalDetail] = Field(default_factory=list)
    asked_at: str
    state: ApprovalState = "pending"
    outcome: ApprovalOutcome | None = None
    decided_by: str | None = None
    decided_at: str | None = None

    #: Why a person refused, in their own words. It travels back to the agent on
    #: purpose: a denial the model can only read as "not allowed" is a denial it will
    #: narrate as "done" (#86). Bounded like everything else on this path.
    decision_note: str = ""


class QueueFull(RuntimeError):
    """Raised when too many questions are already waiting."""


class UnknownQuestion(KeyError):
    """Raised when a question id is not in the queue."""


class AlreadySettled(RuntimeError):
    """Raised when a question has already been decided or withdrawn."""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _clip(text: str, limit: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


class ApprovalQueue:
    """Pending decisions, in the process that serves both halves.

    In-process is not a shortcut here: the answerer and the console talk to the same
    uvicorn, and a decision is meaningful only while the tool call it belongs to is
    still waiting. Nothing survives a restart *as pending*, which is correct — a
    question whose caller is gone must not be answerable. Decisions themselves are
    appended to a log, because those outlive the request.
    """

    def __init__(self) -> None:
        self._questions: dict[str, ApprovalQuestion] = {}
        self._settled: dict[str, asyncio.Event] = {}

    # --- the answerer's side -------------------------------------------------

    def ask(
        self,
        *,
        tool_name: str,
        call_id: str | None = None,
        reason: str = "",
        detail: list[ApprovalDetail] | None = None,
    ) -> ApprovalQuestion:
        """Publish one question. Raises `QueueFull` rather than dropping it silently."""
        if len(self.pending()) >= MAX_PENDING:
            raise QueueFull(f"{MAX_PENDING} approvals already waiting; refusing to queue more")

        question = ApprovalQuestion(
            id=uuid.uuid4().hex,
            tool_name=tool_name,
            call_id=call_id or None,
            reason=_clip(reason, 600),
            detail=[
                ApprovalDetail(label=_clip(item.label, 40), value=_clip(item.value, MAX_DETAIL_VALUE))
                for item in (detail or [])[:MAX_DETAIL_ITEMS]
            ],
            asked_at=_now(),
        )
        self._questions[question.id] = question
        self._settled[question.id] = asyncio.Event()
        return question

    async def wait(self, question_id: str, timeout: float) -> ApprovalQuestion:
        """Wait up to `timeout` seconds for a decision; return the question either way.

        A timeout is not an outcome. The caller polls again or gives up, and giving up
        means withdrawing — never proceeding.
        """
        question = self.get(question_id)
        if question.state != "pending":
            return question
        try:
            await asyncio.wait_for(self._settled[question_id].wait(), timeout)
        except TimeoutError:
            pass
        return self.get(question_id)

    def release(self, question_id: str) -> ApprovalQuestion:
        """The caller is done with this question — it leaves the console either way.

        Still pending means nobody answered in time, so it becomes `withdrawn` and can
        never be answered afterwards. Already decided means the caller has read the
        outcome, so the entry is dropped; the decision itself lives in the log, not
        here. Both paths bound how much this queue can hold over a long session.
        """
        question = self.get(question_id)
        if question.state == "pending":
            question.state = "withdrawn"
            self._settled[question_id].set()
        else:
            self.forget(question_id)
        return question

    # --- the operator's side -------------------------------------------------

    def pending(self) -> list[ApprovalQuestion]:
        """Oldest first: the question that has kept somebody waiting longest is first."""
        waiting = [q for q in self._questions.values() if q.state == "pending"]
        return sorted(waiting, key=lambda q: q.asked_at)

    def decide(
        self, question_id: str, *, outcome: ApprovalOutcome, by: str, note: str = ""
    ) -> ApprovalQuestion:
        """Record a person's decision. The only path to a grant."""
        question = self.get(question_id)
        if question.state != "pending":
            raise AlreadySettled(
                f"approval {question_id} is already {question.state}"
                + (f" ({question.outcome})" if question.outcome else "")
            )
        question.state = "decided"
        question.outcome = outcome
        question.decided_by = _clip(by, 80) or "unnamed-operator"
        question.decision_note = _clip(note, 240)
        question.decided_at = _now()
        self._settled[question_id].set()
        _append_to_log(question)
        return question

    def get(self, question_id: str) -> ApprovalQuestion:
        try:
            return self._questions[question_id]
        except KeyError as exc:
            raise UnknownQuestion(question_id) from exc

    def forget(self, question_id: str) -> None:
        """Drop a settled question. Called once its caller has read the outcome."""
        self._questions.pop(question_id, None)
        self._settled.pop(question_id, None)


def log_path() -> Path:
    configured = Path(settings.result_store_path)
    root = configured if configured.is_absolute() else REPO_ROOT / configured
    return root / "approvals.jsonl"


def _append_to_log(question: ApprovalQuestion) -> None:
    """Append one decision, so who allowed what survives the process that asked.

    dsh writes its own `approval/asked` + `approval/decided` pair to the session log;
    this is the operator-facing record of the same event, and #84 is the issue about
    reading dsh's pair back rather than keeping two.
    """
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(question.model_dump(), ensure_ascii=False) + "\n")


#: How far back `granted_by` looks. A confirmation is written moments after its
#: approval, so the answer is always near the end; scanning the whole file would make
#: an audit lookup grow with the number of decisions ever made.
LOG_TAIL = 200


def granted_by(call_id: str | None) -> str | None:
    """Who allowed this exact tool call, if anybody did.

    The tool body knows which agent it is running as, and that is what it has always
    recorded. It is not who decided. Joining on `call_id` is what turns "the agent
    wrote this" into "a person allowed the agent to write this", which is the sentence
    an auditor is actually looking for.
    """
    if not call_id:
        return None
    for entry in reversed(read_log()[-LOG_TAIL:]):
        if entry.call_id == call_id and entry.outcome == GRANT:
            return entry.decided_by
    return None


def read_log() -> list[ApprovalQuestion]:
    """Every decision on file, oldest first. Empty when nothing has been decided."""
    path = log_path()
    if not path.exists():
        return []
    entries: list[ApprovalQuestion] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(ApprovalQuestion.model_validate_json(line))
    return entries


#: The queue the API serves. One per process, which is one per uvicorn worker — see
#: the class docstring for why that is the correct scope rather than a limitation.
queue = ApprovalQueue()
