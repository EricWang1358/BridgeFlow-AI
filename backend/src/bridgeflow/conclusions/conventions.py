"""Conventions the business side has not confirmed, and what happens when they do (E13-UC05).

Where the dictionary is silent, `integration.yaml` fills the gap by convention and says so
under `assumptions`. Every figure that depends on one is graded G3 (docs/requirements/00
§5.3) until the business side speaks. This module is how they speak:

- **Confirm** — the convention is our rule after all. The declaration does not change; what
  changes is that figures depending on it stop being labelled "filled in by convention"
  and grade G2. This is the only runtime effect (D9).
- **Replace** — the convention is wrong. The decision, its source and the requested value
  are recorded and the exact declaration change is produced for the dictionary owner to
  apply. The system never rewrites a formula, a threshold or a roll-up policy from free
  text: the declaration stays the single source of truth (D8).

Frozen batches are never rewritten by either path. A batch keeps the declaration it was
imported with; a newer convention version is reported so a person can re-import.

Decisions are versioned and need an approval receipt; a decision without a source is
refused, because "we confirmed it" with nothing behind it is exactly the unevidenced
conclusion this product refuses everywhere else.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field

from bridgeflow.store import _root, _write

#: Which part of the declaration a convention key names. Read from the declaration, never
#: from the key's spelling: a convention is a constant, a formula, a rule table or a
#: roll-up policy depending on where it is referenced.
Kind = Literal["constant", "derived", "classification", "rollup", "field"]
State = Literal["unconfirmed", "confirmed", "replacement_requested"]


class ConventionDecision(BaseModel):
    convention: str
    version: int = Field(ge=1)
    state: State
    source: str = Field(min_length=1, max_length=400)
    note: str = Field(default="", max_length=400)
    #: Only meaningful for a constant; other kinds need a declaration edit (D8).
    requested_value: str = ""
    decided_by: str
    at: str


class ConventionView(BaseModel):
    id: str
    text: str
    kind: Kind
    affected_fields: list[str]
    state: State = "unconfirmed"
    version: int = 0
    source: str = ""
    note: str = ""
    requested_value: str = ""
    decided_by: str = ""
    at: str = ""
    #: For a requested replacement: the declaration change a dictionary owner must apply.
    declaration_change: str = ""


def _folder():
    return _root() / "conventions"


def _path(convention: str) -> Any:
    safe = "".join(ch for ch in convention if ch.isalnum() or ch in "._-") or "unnamed"
    return _folder() / f"{safe}.json"


def decisions(convention: str) -> list[ConventionDecision]:
    path = _path(convention)
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []
    return [ConventionDecision.model_validate(item) for item in raw.get("decisions", [])]


def latest(convention: str) -> ConventionDecision | None:
    history = decisions(convention)
    return history[-1] if history else None


def kind_of(spec: dict, convention: str) -> tuple[Kind, list[str]]:
    """What the convention governs and which declared fields depend on it."""
    if convention.startswith("rollup."):
        department = convention.split(".", 1)[1]
        policy = (spec.get("rollup") or {}).get(department) or {}
        fields = sorted({*policy.get("sum", []), *policy.get("concat", []), *policy.get("recompute", [])})
        return "rollup", fields
    if convention in (spec.get("constants") or {}):
        affected = [name for name, tree in (spec.get("derived") or {}).items() if convention in _constants_in(tree)]
        return "constant", sorted(affected)
    if convention in (spec.get("classifications") or {}):
        return "classification", [convention]
    if convention in (spec.get("derived") or {}):
        return "derived", [convention]
    return "field", [convention] if convention in (spec.get("fields") or {}) else []


def _constants_in(tree: Any) -> list[str]:
    if not isinstance(tree, dict):
        return []
    found = [tree["key"]] if tree.get("op") == "declared" and "key" in tree else []
    for child in tree.get("args", []):
        found += _constants_in(child)
    return found


def _declaration_change(kind: Kind, convention: str, requested_value: str, note: str) -> str:
    if kind == "constant":
        return f"integration.yaml: constants.{convention} → {requested_value or '<业务方给出的值 / value from the business>'}"
    where = {"derived": f"derived.{convention}", "classification": f"classifications.{convention}",
             "rollup": f"rollup.{convention.split('.', 1)[-1]}", "field": f"fields.{convention}"}[kind]
    return f"integration.yaml: {where} —— 由字典维护人按业务方说明修改 / to be edited by the dictionary owner: {note or requested_value}"


def views(spec: dict) -> list[ConventionView]:
    """Every declared convention with its current decision state."""
    result = []
    for convention, text in sorted((spec.get("assumptions") or {}).items()):
        kind, fields = kind_of(spec, convention)
        view = ConventionView(id=convention, text=text, kind=kind, affected_fields=fields)
        decision = latest(convention)
        if decision is not None:
            view = view.model_copy(update={
                "state": decision.state, "version": decision.version, "source": decision.source,
                "note": decision.note, "requested_value": decision.requested_value,
                "decided_by": decision.decided_by, "at": decision.at,
                "declaration_change": _declaration_change(kind, convention, decision.requested_value, decision.note)
                if decision.state == "replacement_requested" else ""})
        result.append(view)
    return result


def confirmed(spec: dict) -> set[str]:
    """Conventions the business side has confirmed: figures depending on them grade G2."""
    return {view.id for view in views(spec) if view.state == "confirmed"}


def decide(*, spec: dict, convention: str, action: Literal["confirm", "replace"], source: str,
           note: str = "", requested_value: str = "", expected_version: int | None, actor: str) -> ConventionView:
    """Record a decision. Refuses without a source, on a version conflict, or off-declaration."""
    declared = {view.id: view for view in views(spec)}
    if convention not in declared:
        raise HTTPException(404, "No such convention is declared for this batch")
    if not source.strip():
        raise HTTPException(422, "A decision needs a source: the file, meeting note or written statement it comes from")
    current = declared[convention]
    if expected_version is not None and expected_version != current.version:
        raise HTTPException(409, f"This convention is at version {current.version}; re-read it before deciding")
    kind = current.kind
    if action == "replace" and kind == "constant" and not requested_value.strip():
        raise HTTPException(422, "A replaced constant needs the value the business side gives")
    state: State = "confirmed" if action == "confirm" else "replacement_requested"
    decision = ConventionDecision(convention=convention, version=current.version + 1, state=state,
                                  source=source.strip(), note=note.strip(), requested_value=requested_value.strip(),
                                  decided_by=actor, at=datetime.now(UTC).isoformat())
    history = [item.model_dump(mode="json") for item in decisions(convention)] + [decision.model_dump(mode="json")]
    _write(_path(convention), {"convention": convention, "decisions": history})
    return next(view for view in views(spec) if view.id == convention)


def preview(spec: dict, batch, convention: str, requested_value: str, integrate, sheets_of) -> dict:
    """What a replaced constant would change, without writing anything (dry run).

    Only a constant can be previewed: a formula, rule table or roll-up policy is replaced by
    editing the declaration, and guessing what free text means is exactly what this product
    refuses to do (D8).
    """
    kind, _fields = kind_of(spec, convention)
    if kind != "constant":
        raise HTTPException(422, "Only a constant can be previewed; other conventions change the declaration itself")
    try:
        value = float(requested_value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(422, "The replacement value must be a number") from exc
    from bridgeflow import integration

    before = integrate(integration.IntegrationSpec.model_validate(spec), sheets_of(batch))
    changed_spec = {**spec, "constants": {**(spec.get("constants") or {}), convention: value}}
    after = integrate(integration.IntegrationSpec.model_validate(changed_spec), sheets_of(batch))
    # Counted in full, sampled small: at 200k rows the count is the answer and the cells are not.
    changed, sample, fields = 0, [], set()
    for old_row, new_row in zip(before.rows, after.rows, strict=False):
        for name in before.columns:
            if old_row.values.get(name) != new_row.values.get(name):
                changed += 1
                fields.add(name)
                if len(sample) < 20:
                    sample.append({"key": old_row.key, "field": name,
                                   "before": old_row.values.get(name), "after": new_row.values.get(name)})
    return {"convention": convention, "requested_value": requested_value, "changed_cells": changed,
            "changed_fields": sorted(fields), "changed_rows": sum(1 for o, n in zip(before.rows, after.rows, strict=False)
                                                                    if o.values != n.values), "sample": sample,
            "issues_before": len(before.issues), "issues_after": len(after.issues)}
