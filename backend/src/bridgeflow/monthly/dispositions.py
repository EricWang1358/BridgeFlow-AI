"""What happens to a risk finding after the review names it (E07-UC07).

A report saying "attention" is not a decision: somebody has to confirm it, reject it, take it
on, or close it, and the company has to be able to see who did which and on what grounds.

The machine itself is declared (`risk_disposition` in the dictionary), because which states a
company uses and who may move between them is the company's own process — the business side
has not settled its closure rules, and a plausible-looking default would read as though the
system already knew them. With nothing declared, this refuses rather than inventing states.

What is code here is the part that does not vary: transitions are only what the declaration
allows from the current state, a transition that the declaration says needs a reason is
refused without one, every move records the approver as its actor with a timestamp, and the
log is append-only — a later decision never rewrites an earlier one, so the history of a
finding stays readable.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field

from bridgeflow.store import _root, _write


class Transition(BaseModel):
    action: str
    #: The state this action may be taken from; "*" means any state that is not closed.
    from_state: str
    to_state: str
    #: Which declared role may take it; empty means any authorized role.
    by_role: str = ""
    requires_note: bool = False


class Machine(BaseModel):
    states: list[str] = Field(default_factory=list)
    initial: str = ""
    closed: list[str] = Field(default_factory=list)
    transitions: list[Transition] = Field(default_factory=list)

    def allowed(self, state: str) -> list[Transition]:
        return [t for t in self.transitions
                if (t.from_state == state or (t.from_state == "*" and state not in self.closed))]


class Move(BaseModel):
    check_id: str
    action: str
    from_state: str
    to_state: str
    note: str = ""
    decided_by: str
    at: str
    version: int = Field(ge=1)


class Disposition(BaseModel):
    check_id: str
    state: str
    version: int = 0
    note: str = ""
    decided_by: str = ""
    at: str = ""
    available: list[str] = Field(default_factory=list)
    closed: bool = False


def declared(dictionary: dict | None) -> Machine | None:
    raw = (dictionary or {}).get("risk_disposition")
    if not isinstance(raw, dict) or not raw.get("states"):
        return None
    machine = Machine.model_validate(raw)
    unknown = [t.action for t in machine.transitions
               if t.to_state not in machine.states or (t.from_state != "*" and t.from_state not in machine.states)]
    if unknown or machine.initial not in machine.states or not set(machine.closed) <= set(machine.states):
        raise HTTPException(503, "The risk disposition declaration names states it does not declare; its owner corrects it")
    return machine


def _path(batch_id: str, report_id: str) -> Any:
    safe = "".join(ch for ch in f"{batch_id}--{report_id}" if ch.isalnum() or ch in "-_")
    return _root() / "dispositions" / f"{safe}.json"


def history(batch_id: str, report_id: str) -> list[Move]:
    path = _path(batch_id, report_id)
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []
    return [Move.model_validate(item) for item in raw.get("moves", [])]


def state_of(machine: Machine, moves: list[Move], check_id: str) -> Disposition:
    mine = [move for move in moves if move.check_id == check_id]
    latest = mine[-1] if mine else None
    state = latest.to_state if latest else machine.initial
    return Disposition(check_id=check_id, state=state, version=len(mine),
                       note=latest.note if latest else "", decided_by=latest.decided_by if latest else "",
                       at=latest.at if latest else "",
                       available=[t.action for t in machine.allowed(state)],
                       closed=state in machine.closed)


def current(dictionary: dict | None, batch_id: str, report_id: str, check_ids: list[str]) -> dict:
    machine = declared(dictionary)
    if machine is None:
        return {"batch_id": batch_id, "report_id": report_id, "dispositions": [],
                "refusal": "No risk disposition process is declared; its owner declares states, "
                           "transitions and who may take them under risk_disposition"}
    moves = history(batch_id, report_id)
    items = [state_of(machine, moves, check_id).model_dump(mode="json") for check_id in check_ids]
    return {"batch_id": batch_id, "report_id": report_id, "states": machine.states,
            "closed_states": machine.closed, "dispositions": items,
            "open": sum(1 for item in items if not item["closed"])}


def record(*, dictionary: dict | None, batch_id: str, report_id: str, check_id: str, action: str,
           note: str, expected_version: int | None, actor: str, roles: set[str] | None = None) -> Disposition:
    """Take one declared action on one finding. Refuses anything the declaration does not allow."""
    machine = declared(dictionary)
    if machine is None:
        raise HTTPException(409, "No risk disposition process is declared for this batch")
    moves = history(batch_id, report_id)
    state = state_of(machine, moves, check_id)
    if expected_version is not None and expected_version != state.version:
        raise HTTPException(409, f"This finding is at version {state.version}; re-read it before deciding")
    transition = next((t for t in machine.allowed(state.state) if t.action == action), None)
    if transition is None:
        raise HTTPException(409, f"{action} is not allowed from {state.state}; available: {', '.join(state.available) or 'none'}")
    if transition.by_role and roles is not None and transition.by_role not in roles:
        raise HTTPException(403, f"{action} is declared for {transition.by_role}")
    if transition.requires_note and not note.strip():
        raise HTTPException(422, f"{action} needs the reason it was taken on")
    move = Move(check_id=check_id, action=action, from_state=state.state, to_state=transition.to_state,
                note=note.strip(), decided_by=actor, at=datetime.now(UTC).isoformat(), version=state.version + 1)
    # Append-only: a later decision never rewrites an earlier one, so the history stays readable.
    _write(_path(batch_id, report_id), {"batch_id": batch_id, "report_id": report_id,
                                        "moves": [m.model_dump(mode="json") for m in [*moves, move]]})
    return state_of(machine, [*moves, move], check_id)
