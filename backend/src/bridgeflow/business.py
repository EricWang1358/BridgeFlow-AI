"""Declared business arithmetic and responsibility contracts, without model arithmetic."""
from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from decimal import Decimal, InvalidOperation
from math import isfinite
from typing import Any, NamedTuple

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from bridgeflow.api.batches import BatchSnapshot
from bridgeflow.schemas import SourceRef

ROLES = ("production", "procurement", "finance", "marketing")

# The language department explanations are written in, declared per review contract as
# `business_review.explanation_language` (absent = zh, every dictionary before it). Product wording,
# not business fields: what the agent is told, and what the host then holds it to (docs/38).
EXPLANATION_LANGUAGES = {
    "zh": {"language": "Simplified Chinese", "max_characters": 120, "threshold_term": "关注阈值",
           "out_of_scope": "不作为该结论的依据", "topics": ("已批准上限", "已批准标准", "现行批准标准")},
    "en": {"language": "English", "max_characters": 240, "threshold_term": "attention threshold",
           "out_of_scope": "not a basis for this conclusion",
           "topics": ("approved limit", "approved standard", "currently approved standard")},
}
# Every language's built-in topics apply to every explanation: writing in the other language must
# not be a way around them.
BUILT_IN_TOPICS = tuple(t for words in EXPLANATION_LANGUAGES.values() for t in words["topics"])
CJK = re.compile(r"[\u3400-\u9fff\uf900-\ufaff\u3000-\u303f\uff00-\uffef]")


class Value(NamedTuple):
    number: Decimal
    sources: list[SourceRef]
    count: int


def refuse(message: str):
    raise HTTPException(409, message)


def number(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        refuse("Declared numeric cell is missing or unreadable")
    if not result.is_finite():
        refuse("Non-finite numbers cannot support a business decision")
    return result


def expression(node: dict, batch: BatchSnapshot | None, depth: int = 0, *,
               inputs: Mapping[str, Value] | None = None,
               metric: Callable[[str, int], Value] | None = None) -> Value:
    """A bounded arithmetic tree; no eval, inferred fields, joins or currencies."""
    if depth > 8 or not isinstance(node, dict):
        refuse("Invalid or excessively nested business formula")
    op = node.get("op")
    if op == "input":
        key = node.get("key")
        if inputs is None or key not in inputs:
            refuse(f"Missing declared input: {key}")
        return inputs[key]
    if op == "metric":
        if metric is None or not isinstance(node.get("key"), str):
            refuse("Metric reference is not configured")
        return metric(node["key"], depth + 1)
    if op == "constant":
        return Value(number(node["value"]), [], 0)
    if op in ("sum", "sum_product"):
        if batch is None:
            refuse("A table expression requires an immutable table batch")
        department = node.get("department")
        tables = [table for table in batch.clean_tables if table.department == department]
        if len(tables) != 1 or not tables[0].rows:
            refuse(f"Missing usable department: {department}")
        table = tables[0]
        dictionary = batch.dictionary_snapshot or {}
        declared = dictionary.get("measures", {}).get(department, {})
        measures = node.get("measures", [])
        if not 1 <= len(measures) <= 4 or (op == "sum" and len(measures) != 1):
            refuse("Formula needs explicit measurement factors")
        columns = []
        for measure in measures:
            matches = [column for column, meaning in declared.items() if meaning == measure]
            if len(matches) != 1:
                refuse(f"{department}: measurement {measure} is absent or ambiguous")
            columns.append(matches[0])
        total, count, sources = Decimal(0), 0, []
        for index, row in enumerate(table.rows):
            product = Decimal(1)
            for column in columns:
                product *= number(row.get(column))
                count += 1
                if len(sources) < 5:
                    sources.append(SourceRef(department=table.department, period=batch.period,
                        row=index, column=column, batch=table.batch, filename=table.filename,
                        sheet=table.sheet, original_column=table.original_columns.get(column, column),
                        source_row=table.source_rows[index] if index < len(table.source_rows) else None))
            total += product
        return Value(total, sources, count)
    operands = node.get("args", [])
    if op not in ("add", "subtract", "divide", "multiply") or len(operands) != 2:
        refuse("Unsupported business arithmetic operation")
    a, b = [expression(child, batch, depth + 1, inputs=inputs, metric=metric) for child in operands]
    if op == "divide" and b.number == 0:
        refuse("Zero denominator; no ratio can be reported")
    value = {"add": lambda: a.number + b.number, "subtract": lambda: a.number - b.number,
             "multiply": lambda: a.number * b.number, "divide": lambda: a.number / b.number}[op]()
    return Value(value, (a.sources + b.sources)[:5], a.count + b.count)


def data_blockers(batch: BatchSnapshot) -> list[str]:
    """Row-level data problems that stop a review, each in the words the review refuses with.

    These are declared import contracts, not column-name guesses. The batch status reads the
    same list, so a batch is never shown as ready for review while the review would refuse
    it — before this, a negative quantity or a row from another month imported as "ready"
    and was only refused when somebody started the review.
    """
    config = (batch.dictionary_snapshot or {}).get("business_review") or {}
    reasons: list[str] = []
    for table in batch.clean_tables:
        if any(c.rule == "duplicate_row" for c in table.corrections):
            reasons.append(f"{table.department}: identical rows need transaction identity review before totals; import a corrected source")
        schema = config.get("inputs", {}).get(table.department, {})
        date_column = schema.get("date_column")
        if not date_column:
            continue
        for row in table.rows:
            for column in schema.get("nonnegative_columns", []):
                try:
                    value = number(row.get(column))
                except HTTPException:
                    # Named here, where department and column are known; the bare check
                    # only knows that some declared cell could not be read.
                    reasons.append(f"{table.department}: {column} is missing or unreadable")
                    continue
                if value < 0:
                    reasons.append(f"{table.department}: {column} violates the declared nonnegative convention")
            if not str(row.get(date_column, "")).startswith(batch.period + "-"):
                reasons.append(f"{table.department}: a row is outside the requested period or lacks a date")
            currency = schema.get("currency")
            if currency and row.get(currency["column"]) != currency["value"]:
                reasons.append(f"{table.department}: currency missing or mismatched; conversion is not configured")
    return list(dict.fromkeys(reasons))


def context(batch_id: str, batch: BatchSnapshot) -> dict:
    if batch.refusal or any(t.quarantine for t in batch.clean_tables):
        refuse("Resolve batch configuration or quarantined rows and import a new batch before review")
    config = (batch.dictionary_snapshot or {}).get("business_review")
    if not config:
        refuse("No business review contract configured for this batch")
    if {t.department for t in batch.clean_tables} != set(ROLES):
        refuse("Business review requires all four departments")
    for table in batch.clean_tables:
        if not config.get("inputs", {}).get(table.department, {}).get("date_column"):
            refuse(f"No period field declared for {table.department}")
    blockers = data_blockers(batch)
    if blockers:
        refuse(blockers[0])
    code = config.get("explanation_language", "zh")
    if code not in EXPLANATION_LANGUAGES:
        refuse(f"Unknown explanation language {code!r}; declare one of {sorted(EXPLANATION_LANGUAGES)}")
    words = EXPLANATION_LANGUAGES[code]
    explanation = {"code": code, **{k: v for k, v in words.items() if k != "topics"}}
    definitions = config.get("metrics", {})
    if not 1 <= len(definitions) <= 24:
        refuse("Business metric catalogue must contain 1–24 entries")
    facts = {}
    for metric, spec in definitions.items():
        result = expression(spec["expression"], batch)
        if not isfinite(float(result.number)):
            refuse(f"{metric}: formula result is outside the supported finite numeric range")
        facts[metric] = {"metric": metric, "value": float(round(result.number, 4)), "unit": spec["unit"],
            "formula": spec["formula"], "sources": [x.model_dump() for x in result.sources],
            "source_count": result.count, "source_count_basis": "formula input cell occurrences",
            "truncated": result.count > len(result.sources)}
    packets = []
    for role in ROLES:
        policy = config.get("roles", {}).get(role)
        if not policy:
            refuse(f"Missing responsibility contract: {role}")
        checks = []
        for check in config.get("checks", []):
            if check["owner"] != role:
                continue
            fact = facts[check["metric"]]
            threshold = facts[check["threshold_metric"]]["value"] if "threshold_metric" in check else check["threshold"]
            if check["attention_when"] not in ("above", "below"):
                refuse("Unknown business threshold comparison")
            attention = fact["value"] > threshold if check["attention_when"] == "above" else fact["value"] < threshold
            checks.append({"check_id": check["id"], **fact, "threshold": threshold,
                "attention_when": check["attention_when"], "expected_status": "attention" if attention else "ok",
                "actions": check["actions"], "title": check["title"]})
        if not 1 <= len(checks) <= 6:
            refuse(f"{role}: expected 1–6 declared checks")
        packets.append({"role": role, "responsibility": policy["responsibility"],
            "decision_owner": policy["decision_owner"], "constraints": policy["constraints"],
            "explanation": explanation,
            "unsupported_topics": [*words["topics"], *policy.get("unsupported_topics", [])], "checks": checks})
    return {"batch_id": batch_id, "period": batch.period, "case": config["case"], "facts": facts,
            "roles": packets, "limitations": config.get("limitations", []),
            "manager_decision": config.get("manager_decision", "Review the proposed actions with department owners")}


class Judgement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    check_id: str
    metric: str
    value: float = Field(allow_inf_nan=False)
    unit: str
    status: str
    action: str
    # The outer bound; each language's own limit is checked in validate_role.
    explanation: str = Field(min_length=1, max_length=max(w["max_characters"] for w in EXPLANATION_LANGUAGES.values()))


class RoleJudgement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    checks: list[Judgement] = Field(min_length=1, max_length=6)


def validate_role(packet: dict, judgement: dict) -> dict:
    """Reconstruct evidence and owners from trusted facts; reject model substitutions."""
    parsed = RoleJudgement.model_validate(judgement)
    expected = {check["check_id"]: check for check in packet["checks"]}
    if len(parsed.checks) != len(expected) or {c.check_id for c in parsed.checks} != set(expected):
        refuse("Role output omitted, duplicated or invented a required check")
    verified = []
    for answer in parsed.checks:
        fact = expected[answer.check_id]
        if (answer.metric != fact["metric"] or abs(answer.value - fact["value"]) > 0.00001
                or answer.unit != fact["unit"] or answer.status != fact["expected_status"]):
            refuse(f"Unverified numeric claim or status in {answer.check_id}")
        if answer.action not in fact["actions"][answer.status]:
            refuse(f"Action exceeds declared responsibility in {answer.check_id}")
        # Numeric assertions belong in validated fields, not free-form prose.
        if any(char.isdigit() for char in answer.explanation):
            refuse("Explanation must use qualitative language; numeric claims belong in validated fields")
        rules = packet["explanation"]
        if len(answer.explanation) > rules["max_characters"]:
            refuse(f"Explanation in {answer.check_id} exceeds {rules['max_characters']} characters")
        # Written in the declared language, or the topic check below could be sidestepped.
        if (rules["code"] == "en") == bool(CJK.search(answer.explanation)):
            refuse(f"Explanation in {answer.check_id} is not written in {rules['language']}, as this batch declares")
        said = answer.explanation.casefold()
        if any(topic.casefold() in said for topic in (*BUILT_IN_TOPICS, *packet.get("unsupported_topics", []))):
            refuse("Explanation discusses a topic outside this department's declared evidence scope")
        verified.append({**fact, "action": answer.action, "explanation": answer.explanation,
            "explanation_status": "model_advice", "owner": packet["role"],
            "decision_owner": packet["decision_owner"], "execution_status": "proposed_only"})
    return {"role": packet["role"], "responsibility": packet["responsibility"],
            "decision_owner": packet["decision_owner"], "constraints": packet["constraints"], "checks": verified}
