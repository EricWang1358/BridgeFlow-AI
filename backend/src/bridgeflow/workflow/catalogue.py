"""Declarations people approve: templates, stages, lineage and the routes between them.

This is Agent 1's deliverable in data form (#143): which department produces which
artifact at which stage, what each field means, how a field travels into the next
stage, and who receives it. Agent 2 runs only against what is declared here and
approved; Agent 3 reads the same declarations to place what it observes.

The catalogue is validated as a whole before anything uses it. A route to a stage
that does not exist, a lineage edge to a field nobody declared, or a derived value
whose inputs are missing is a configuration error reported at load, not a surprise
halfway through somebody's submission.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from bridgeflow.config import REPO_ROOT, settings


class Status(StrEnum):
    """Where a declaration is in its approval. Only `approved` is used at runtime."""

    DRAFT = "draft"
    PROPOSED = "proposed"
    APPROVED = "approved"


class EdgeStatus(StrEnum):
    """How sure the catalogue is about a lineage edge. Shown, never upgraded silently."""

    CONFIRMED = "confirmed"
    INFERRED = "inferred"
    MISSING = "missing"
    CONFLICT = "conflict"


FieldType = Literal["string", "number", "date", "period", "enum"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FieldSpec(_Strict):
    label: str
    definition: str = ""
    dtype: FieldType = "string"
    required: bool = True
    #: Header or label variants that mean exactly this field. Declared, so matching
    #: an employee's wording is a lookup, not a guess.
    aliases: tuple[str, ...] = ()
    #: Canonical unit and the spellings accepted for it, e.g. {"方": "m3"}.
    unit: str = ""
    units: dict[str, str] = Field(default_factory=dict)
    #: A bare number is only read in `unit` when this says so; otherwise it is asked.
    bare_number_in_unit: bool = False
    minimum: float | None = None
    #: Accepted date spellings, strptime syntax. ISO dates are always accepted.
    formats: tuple[str, ...] = ()
    allowed: tuple[str, ...] = ()
    #: The value must arrive with its own supporting reference, e.g. a confirmation
    #: document. Stops one quantity being copied into another's place.
    evidence_required: bool = False
    question: str = ""


class CheckSpec(_Strict):
    """A non-blocking comparison shown to the reviewer and the next stage."""

    id: str
    title: str
    expression: dict[str, Any]
    attention_when: Literal["above", "below"]
    threshold: float = 0
    unit: str = ""


class TemplateSpec(_Strict):
    title: str
    department: str
    version: int = Field(ge=1)
    status: Status = Status.DRAFT
    #: The fields that identify one business object, so inputs from different
    #: departments about the same object can be recognised as such.
    business_key: tuple[str, ...]
    fields: dict[str, FieldSpec]
    derived: dict[str, dict[str, Any]] = Field(default_factory=dict)
    checks: tuple[CheckSpec, ...] = ()

    @model_validator(mode="after")
    def _references(self) -> TemplateSpec:
        unknown = [key for key in self.business_key if key not in self.fields]
        if unknown:
            raise ValueError(f"business_key names undeclared fields: {unknown}")
        clashes = set(self.derived) & set(self.fields)
        if clashes:
            raise ValueError(f"derived keys shadow declared fields: {sorted(clashes)}")
        seen: dict[str, str] = {}
        for key, spec in self.fields.items():
            for name in (spec.label, *spec.aliases):
                if seen.setdefault(name, key) != key:
                    raise ValueError(f"label or alias {name!r} is declared for two fields")
        return self


class StageSpec(_Strict):
    title: str
    department: str
    #: A role, never a person. Mapping roles to accounts belongs to the platform.
    owner_role: str
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    action: str = ""
    #: How long a handoff may wait before adoption signals mention it. Absent means
    #: nobody has agreed a time, and nothing is flagged.
    sla_hours: float | None = None


class LineageEdge(_Strict):
    source: str  # template.field
    target: str  # template.field
    transform: Literal["passthrough", "rename", "convert", "join", "aggregate", "compute"]
    status: EdgeStatus = EdgeStatus.INFERRED
    evidence: str = ""


class MvpDecision(_Strict):
    status: Status = Status.PROPOSED
    candidates: tuple[str, ...] = ()
    selected: str = ""
    #: Where the vote or confirmation is recorded. An AI ranking is not a decision.
    decision_record: str = ""


class AdoptionPolicy(_Strict):
    max_question_rounds: int = Field(2, ge=1)
    max_notification_attempts: int = Field(3, ge=1)


class SinkSpec(_Strict):
    kind: Literal["local_sqlite", "unconfigured"] = "unconfigured"


class NotifierSpec(_Strict):
    kind: Literal["local_outbox", "unconfigured"] = "unconfigured"


class Catalogue(_Strict):
    version: str
    status: Status
    case: str = ""
    templates: dict[str, TemplateSpec]
    stages: dict[str, StageSpec]
    lineage: tuple[LineageEdge, ...] = ()
    mvp: MvpDecision = MvpDecision()
    adoption: AdoptionPolicy = AdoptionPolicy()
    sink: SinkSpec = SinkSpec()
    notifier: NotifierSpec = NotifierSpec()

    @model_validator(mode="after")
    def _integrity(self) -> Catalogue:
        problems: list[str] = []
        for name, stage in self.stages.items():
            for artifact in (*stage.inputs, *stage.outputs):
                if artifact not in self.templates:
                    problems.append(f"stage {name} names unknown template {artifact}")
            widths = {len(self.templates[t].business_key) for t in stage.inputs if t in self.templates}
            if len(widths) > 1:
                # Inputs about the same object are recognised by their key values in
                # declared order, so every input must declare a key of the same shape.
                problems.append(f"stage {name} inputs declare business keys of different lengths")
        for edge in self.lineage:
            for end in (edge.source, edge.target):
                template, _, field = end.partition(".")
                spec = self.templates.get(template)
                if spec is None or (field not in spec.fields and field not in spec.derived):
                    problems.append(f"lineage end {end} is not a declared field")
        if self.mvp.selected and self.mvp.selected not in self.mvp.candidates:
            problems.append("mvp.selected is not one of mvp.candidates")
        if problems:
            raise ValueError("; ".join(problems))
        return self

    # --- queries ---------------------------------------------------------------

    def runnable(self, template: str) -> TemplateSpec:
        """The template, if people approved both it and the catalogue. Otherwise refuse."""
        spec = self.templates.get(template)
        if spec is None:
            raise CatalogueError(f"Template {template} is not declared")
        if self.status is not Status.APPROVED or spec.status is not Status.APPROVED:
            raise CatalogueError(
                f"Template {template} is {spec.status.value} in a {self.status.value} catalogue; "
                "only approved declarations accept data"
            )
        return spec

    def consumers(self, template: str) -> list[str]:
        """Stages that take this template as an input, in declaration order."""
        return [name for name, stage in self.stages.items() if template in stage.inputs]

    def lineage_of(self, template: str, field: str) -> dict[str, list[LineageEdge]]:
        """Every edge upstream of and downstream from one field, transitively."""
        node = f"{template}.{field}"

        def walk(start: str, forward: bool) -> list[LineageEdge]:
            found: list[LineageEdge] = []
            frontier, seen = [start], {start}
            while frontier:
                current = frontier.pop()
                for edge in self.lineage:
                    here, there = (edge.source, edge.target) if forward else (edge.target, edge.source)
                    if here == current:
                        found.append(edge)
                        if there not in seen:
                            seen.add(there)
                            frontier.append(there)
            return found

        return {"upstream": walk(node, forward=False), "downstream": walk(node, forward=True)}


class CatalogueError(Exception):
    """A declaration is missing, unapproved or inconsistent."""


def catalogue_path() -> Path | None:
    configured = settings.workflow_catalogue_path
    if not configured:
        return None
    path = Path(configured)
    return path if path.is_absolute() else REPO_ROOT / path


def load(path: Path | None = None) -> Catalogue:
    target = path or catalogue_path()
    if target is None or not target.is_file():
        raise CatalogueError("Workflow catalogue is not configured")
    try:
        raw = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
        return Catalogue.model_validate(raw)
    except (yaml.YAMLError, ValueError) as exc:
        raise CatalogueError(f"Workflow catalogue is invalid: {exc}") from exc
