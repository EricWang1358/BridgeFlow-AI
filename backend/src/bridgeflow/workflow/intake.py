"""Observations in, a draft out: every value with where it came from, every gap named.

An observation is one thing somebody supplied — a cell of their own sheet, a line of a
reply, a value an extraction step read — with its source. `evaluate` is a pure
function of the approved template and the observations so far, so the same inputs
always produce the same draft, and the draft's digest is what a reviewer approves.

The pipeline, in order:

1. resolve each observation's label to a declared field (key, label or alias only);
2. normalise it with the strategy for the field's type;
3. merge observations per field — equal values agree, a declared correction replaces,
   anything else is a conflict to be settled by a person;
4. check required fields and required evidence;
5. compute derived values and checks with the bounded arithmetic in `business`, and
   only when every input is present.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from typing import Any, Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field

from bridgeflow import business
from bridgeflow.workflow.catalogue import FieldSpec, TemplateSpec
from bridgeflow.workflow.normalise import normalise

IssueKind = Literal["missing", "invalid", "ambiguous", "conflict", "needs_evidence", "unmapped"]
#: An unmapped label loses nothing that is required, so it is shown, not blocking.
BLOCKING: frozenset[str] = frozenset({"missing", "invalid", "ambiguous", "conflict", "needs_evidence"})


class Source(BaseModel):
    kind: Literal["file", "reply", "extraction", "system"]
    #: File/sheet/cell, reply id, page and region — whatever lets a person find it.
    ref: str


class Observation(BaseModel):
    label: str
    value: Any = None
    source: Source
    #: A reference supporting the value itself, such as a confirmation document id.
    evidence: str = ""
    #: The person is correcting an earlier value for this field, not adding a rival.
    correction: bool = False


class FieldValue(BaseModel):
    value: str
    raw: str
    source: Source
    evidence: str = ""
    note: str = ""


class Issue(BaseModel):
    kind: IssueKind
    field: str = ""
    message: str
    question: str = ""
    #: Rival values for a conflict, each with its source, so nobody has to go looking.
    candidates: list[FieldValue] = Field(default_factory=list)

    @property
    def blocking(self) -> bool:
        return self.kind in BLOCKING


class CheckResult(BaseModel):
    id: str
    title: str
    value: str
    unit: str = ""
    attention: bool


class Draft(BaseModel):
    template: str
    template_version: int
    values: dict[str, FieldValue] = Field(default_factory=dict)
    derived: dict[str, str] = Field(default_factory=dict)
    checks: list[CheckResult] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)
    digest: str = ""

    @property
    def complete(self) -> bool:
        return not any(issue.blocking for issue in self.issues)

    def business_key(self, spec: TemplateSpec) -> dict[str, str]:
        return {key: self.values[key].value for key in spec.business_key if key in self.values}


def _question(spec: FieldSpec) -> str:
    """The declared question, or nothing. Wording in the reader's language belongs to
    whoever presents the issue, which has the field label to build it from."""
    return spec.question


def _resolver(template: TemplateSpec) -> dict[str, str]:
    names: dict[str, str] = {}
    for key, spec in template.fields.items():
        for name in (key, spec.label, *spec.aliases):
            names[name.strip()] = key
    return names


def evaluate(name: str, template: TemplateSpec, observations: list[Observation]) -> Draft:
    draft = Draft(template=name, template_version=template.version)
    names = _resolver(template)
    conflicts: dict[str, list[FieldValue]] = {}

    for observation in observations:
        key = names.get(observation.label.strip())
        if key is None:
            draft.issues.append(Issue(
                kind="unmapped", field="",
                message=f"{observation.label!r} is not a label this template declares; it was not used",
            ))
            continue
        spec = template.fields[key]
        result = normalise(observation.value, spec)
        raw = "" if observation.value is None else str(observation.value)
        if result.problem is not None:
            kind, message = result.problem
            draft.values.pop(key, None)
            draft.issues = [i for i in draft.issues if i.field != key]
            draft.issues.append(Issue(kind=kind, field=key, message=message, question=_question(spec)))  # type: ignore[arg-type]
            continue
        if result.value is None:
            continue
        current = FieldValue(value=result.value, raw=raw, source=observation.source,
                             evidence=observation.evidence, note=result.note)
        previous = draft.values.get(key)
        if observation.correction or previous is None:
            draft.values[key] = current
            conflicts.pop(key, None)
            draft.issues = [i for i in draft.issues if i.field != key]
        elif previous.value != current.value:
            conflicts.setdefault(key, [previous]).append(current)

    for key, rivals in conflicts.items():
        spec = template.fields[key]
        draft.values.pop(key, None)
        draft.issues.append(Issue(
            kind="conflict", field=key, candidates=rivals, question=_question(spec),
            message=f"{spec.label} was supplied with different values; confirm which one is right",
        ))

    flagged = {issue.field for issue in draft.issues}
    for key, spec in template.fields.items():
        if key in flagged:
            continue
        value = draft.values.get(key)
        if value is None:
            if spec.required:
                draft.issues.append(Issue(kind="missing", field=key, message=f"{spec.label} is required",
                                          question=_question(spec)))
        elif spec.evidence_required and not value.evidence:
            draft.issues.append(Issue(
                kind="needs_evidence", field=key, question=_question(spec),
                message=f"{spec.label} needs its own supporting reference; it cannot be taken from another field",
            ))

    _compute(draft, template)
    draft.digest = _digest(draft)
    return draft


def _compute(draft: Draft, template: TemplateSpec) -> None:
    numbers = {key: business.Value(Decimal(v.value), [], 1) for key, v in draft.values.items()
               if template.fields[key].dtype == "number"}

    def run(expression: dict[str, Any]) -> Decimal | None:
        try:
            return business.expression(expression, None, inputs=numbers).number
        except HTTPException:
            return None  # an input is absent or unusable; nothing is estimated

    for key, spec in template.derived.items():
        result = run(spec.get("expression", {}))
        if result is not None:
            draft.derived[key] = format(result.normalize(), "f")
            numbers[key] = business.Value(result, [], 1)
    for check in template.checks:
        result = run(check.expression)
        if result is None:
            continue
        threshold = Decimal(str(check.threshold))
        attention = result > threshold if check.attention_when == "above" else result < threshold
        draft.checks.append(CheckResult(id=check.id, title=check.title, unit=check.unit,
                                        value=format(result.normalize(), "f"), attention=attention))


def _digest(draft: Draft) -> str:
    """What a reviewer approves: the template version and every accepted value."""
    payload = {
        "template": draft.template, "version": draft.template_version,
        "values": {k: [v.value, v.evidence] for k, v in sorted(draft.values.items())},
        "derived": dict(sorted(draft.derived.items())),
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
