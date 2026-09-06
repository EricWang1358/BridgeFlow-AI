"""Evaluate human-declared documents over trusted extraction results, without an LLM.

This is an internal boundary, not a raw-file parser or a public ingestion API.
Arithmetic is shared with monthly business reviews.
"""
from __future__ import annotations

import hashlib
import json
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal, DecimalException, localcontext
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from bridgeflow.business import Value, expression, number
from bridgeflow.schemas import SourceRef


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExtractedFact(StrictModel):
    status: Literal["extracted", "missing", "ambiguous", "unreadable"]
    value: str | None = Field(default=None, max_length=128)
    unit: str = Field(default="", max_length=80)
    sources: list[SourceRef] = Field(default_factory=list, max_length=4)


class StructuredDocument(StrictModel):
    id: str = Field(min_length=1, max_length=128)
    status: Literal["extracted", "failed"]
    facts: dict[str, ExtractedFact] = Field(max_length=64)


class InputSpec(StrictModel):
    title: str = Field(min_length=1, max_length=160)
    unit: str = Field(min_length=1, max_length=80)
    owner: str
    minimum: Decimal | None = Field(default=None, allow_inf_nan=False)
    exclusive_minimum: Decimal | None = Field(default=None, allow_inf_nan=False)


class Rounding(StrictModel):
    places: int = Field(ge=0, le=8)
    mode: Literal["ceiling", "half_up"]


class MetricSpec(StrictModel):
    title: str = Field(min_length=1, max_length=160)
    unit: str = Field(min_length=1, max_length=80)
    formula: str = Field(min_length=1, max_length=800)
    expression: dict
    rounding: Rounding | None = None


class RoleSpec(StrictModel):
    responsibility: str = Field(min_length=1, max_length=480)
    decision_owner: str = Field(min_length=1, max_length=160)


class CheckSpec(StrictModel):
    id: str
    title: str = Field(min_length=1, max_length=160)
    owner: str
    metric: str
    attention_when: Literal["above", "below"]
    threshold: Decimal | None = Field(default=None, allow_inf_nan=False)
    threshold_metric: str | None = None
    block_on_attention: bool


class DocumentContract(StrictModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=800)
    inputs: dict[str, InputSpec] = Field(min_length=1, max_length=64)
    roles: dict[str, RoleSpec] = Field(min_length=1, max_length=8)
    metrics: dict[str, MetricSpec] = Field(min_length=1, max_length=24)
    checks: list[CheckSpec] = Field(max_length=24)
    outputs: list[str] = Field(min_length=1, max_length=24)
    manager_decision: str = Field(min_length=1, max_length=480)

    def verify(self) -> None:
        for mapping in (self.inputs, self.roles, self.metrics):
            if any(not key or len(key) > 128 for key in mapping):
                raise ValueError("Declaration identifiers exceed the supported boundary")
        def formula(node: dict, depth: int = 0):
            if not isinstance(node, dict) or depth > 8:
                raise ValueError("Invalid formula tree")
            op = node.get("op")
            if op in ("input", "metric"):
                catalogue = self.inputs if op == "input" else self.metrics
                if set(node) != {"op", "key"} or not isinstance(node.get("key"), str) or node["key"] not in catalogue:
                    raise ValueError("References must name declared inputs or metrics")
            elif op == "constant":
                if set(node) != {"op", "value"} or len(str(node["value"])) > 128:
                    raise ValueError("Invalid constant")
                try:
                    if abs(number(node["value"]).adjusted()) > 24:
                        raise ValueError("Constant exceeds supported range")
                except HTTPException as exc:
                    raise ValueError("Invalid constant") from exc
            elif op in ("add", "subtract", "multiply", "divide"):
                if set(node) != {"op", "args"} or not isinstance(node["args"], list) or len(node["args"]) != 2:
                    raise ValueError("Binary arithmetic requires exactly two operands")
                for child in node["args"]:
                    formula(child, depth + 1)
            else:
                raise ValueError("Undeclared arithmetic operation")
        for spec in self.metrics.values():
            formula(spec.expression)
        if len(set(self.outputs)) != len(self.outputs) or any(key not in self.metrics for key in self.outputs):
            raise ValueError("Outputs must name distinct declared metrics")
        if len({check.id for check in self.checks}) != len(self.checks):
            raise ValueError("Duplicate check identity")
        if any(spec.owner not in self.roles for spec in self.inputs.values()):
            raise ValueError("Input responsibility must be declared")
        for check in self.checks:
            if (check.owner not in self.roles or check.metric not in self.metrics
                    or (check.threshold is None) == (check.threshold_metric is None)
                    or check.threshold_metric is not None and check.threshold_metric not in self.metrics):
                raise ValueError("Check must declare its owner, metric and exactly one threshold")
            if check.threshold_metric and self.metrics[check.metric].unit != self.metrics[check.threshold_metric].unit:
                raise ValueError("Compared metrics require the same declared unit")


def valid_text_source(source: SourceRef) -> bool:
    return bool(source.filename.strip() and source.document_sha256
                and (source.page is not None or source.paragraph.strip()) and source.excerpt.strip()
                and all(len(value) <= 256 for value in (source.filename, source.period, source.sheet, source.column, source.original_column)))


def evaluate_document(config: dict, document: StructuredDocument | dict, declaration: SourceRef) -> dict:
    """All-or-nothing internal draft. Neither draft nor refusal grants permission to send."""
    result = {"status": "refused", "document_id": "", "fields": [], "checks": [], "refusals": [],
              "execution_status": "not_approved_not_sent"}

    def fail(code: str, key: str = "", title: str = "", owner: str = ""):
        result["refusals"].append({"code": code, "field": key, "title": title, "decision_owner": owner})

    try:
        contract = DocumentContract.model_validate(config)
        contract.verify()
    except (ValidationError, ValueError):
        fail("invalid_contract", title="A complete human-declared document contract is required")
        return result
    if not valid_text_source(declaration):
        fail("missing_declaration_source", title="The human policy needs a traceable frozen source")
        return result
    result["contract_digest"] = hashlib.sha256(json.dumps(contract.model_dump(mode="json"), sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    result["declaration"] = declaration.model_dump()
    try:
        document = StructuredDocument.model_validate(document)
    except ValidationError:
        fail("invalid_extraction", title="Extraction structure or citation exceeds the declared boundary")
        return result
    result["document_id"] = document.id
    result["document_digest"] = hashlib.sha256(json.dumps(document.model_dump(mode="json"), sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    if document.status != "extracted":
        fail("extraction_failed", title="The input could not be completely extracted")
        return result
    for key in sorted(document.facts.keys() - contract.inputs.keys()):
        if not key or len(key) > 128:
            fail("invalid_extraction", title="Fact identifiers exceed the supported boundary")
            return result
        fail("undeclared_input", key, "Input is outside the human dictionary")
    inputs: dict[str, Value] = {}
    versions: dict[str, str] = {}
    for key, spec in contract.inputs.items():
        owner = contract.roles[spec.owner].decision_owner
        fact = document.facts.get(key)
        if fact is None or fact.status == "missing":
            fail("missing_input", key, spec.title, owner)
            continue
        if fact.status != "extracted":
            fail("extraction_failed", key, spec.title, owner)
            continue
        if fact.unit != spec.unit:
            fail("unit_mismatch", key, spec.title, owner)
            continue
        if not fact.sources or any(not valid_text_source(s) or s.batch != document.id for s in fact.sources):
            fail("missing_source", key, spec.title, owner)
            continue
        for source in fact.sources:
            previous = versions.setdefault(source.filename, source.document_sha256)
            if previous != source.document_sha256:
                fail("source_version_conflict", key, spec.title, owner)
        try:
            value = number(fact.value)
            if abs(value.adjusted()) > 24:
                raise ValueError("Numeric range exceeded")
            if ((spec.minimum is not None and value < spec.minimum)
                    or (spec.exclusive_minimum is not None and value <= spec.exclusive_minimum)):
                raise ValueError("Declared input constraint violated")
            inputs[key] = Value(value, fact.sources, len(fact.sources))
        except (HTTPException, ValueError, DecimalException):
            fail("invalid_value", key, spec.title, owner)
    if result["refusals"]:
        return result
    checks = []
    active: set[str] = set()
    values: dict[str, Value] = {}

    def metric(key: str, depth: int = 0) -> Value:
        if key not in contract.metrics or key in active or depth > 8:
            raise ValueError("Undeclared, cyclic or excessively nested metric")
        # Evaluate every reference with its actual depth; caching must not bypass bounds.
        active.add(key)
        try:
            spec = contract.metrics[key]
            value = expression(spec.expression, None, depth, inputs=inputs, metric=metric)
            if not value.number.is_finite() or abs(value.number.adjusted()) > 24:
                raise ValueError("Numeric range exceeded")
            if spec.rounding:
                quantum = Decimal(1).scaleb(-spec.rounding.places)
                mode = ROUND_CEILING if spec.rounding.mode == "ceiling" else ROUND_HALF_UP
                value = value._replace(number=value.number.quantize(quantum, rounding=mode))
            values[key] = value
            return value
        finally:
            active.remove(key)

    try:
        with localcontext() as arithmetic:
            arithmetic.prec = 64
            for key in contract.metrics:
                metric(key)
            for check in contract.checks:
                value = values[check.metric].number
                threshold = values[check.threshold_metric].number if check.threshold_metric else check.threshold
                attention = value > threshold if check.attention_when == "above" else value < threshold
                checks.append({"id": check.id, "title": check.title, "status": "attention" if attention else "ok",
                               "decision_owner": contract.roles[check.owner].decision_owner})
                if attention and check.block_on_attention:
                    fail("threshold_exceeded", check.id, check.title, contract.roles[check.owner].decision_owner)
            for key in contract.outputs:
                if values[key].count == 0:
                    fail("ungrounded_output", key, contract.metrics[key].title)
    except (HTTPException, ValueError, KeyError, TypeError, DecimalException):
        fail("invalid_formula", title="A declared expression cannot be evaluated from the supplied evidence")
    if result["refusals"]:
        return result
    for key in contract.outputs:
        value, spec = values[key], contract.metrics[key]
        result["fields"].append({"metric": key, "title": spec.title, "value": format(value.number, "f"),
            "unit": spec.unit, "formula": spec.formula, "sources": [s.model_dump() for s in value.sources],
            "source_count": value.count, "truncated": value.count > len(value.sources),
            "source_count_basis": "formula input citation occurrences"})
    result.update(status="draft", checks=checks, manager_decision=contract.manager_decision)
    return result
