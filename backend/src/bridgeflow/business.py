"""Declared business arithmetic and responsibility contracts, without model arithmetic."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from math import isfinite
from typing import Any, NamedTuple

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from bridgeflow.api.batches import BatchSnapshot
from bridgeflow.schemas import SourceRef

ROLES = ("production", "procurement", "finance", "marketing")


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


def expression(node: dict, batch: BatchSnapshot, depth: int = 0) -> Value:
    """A bounded arithmetic tree; no eval, inferred fields, joins or currencies."""
    if depth > 8 or not isinstance(node, dict):
        refuse("Invalid or excessively nested business formula")
    op = node.get("op")
    if op == "constant":
        return Value(number(node["value"]), [], 0)
    if op in ("sum", "sum_product"):
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
    a, b = [expression(child, batch, depth + 1) for child in operands]
    if op == "divide" and b.number == 0:
        refuse("Zero denominator; no ratio can be reported")
    value = {"add": lambda: a.number + b.number, "subtract": lambda: a.number - b.number,
             "multiply": lambda: a.number * b.number, "divide": lambda: a.number / b.number}[op]()
    return Value(value, (a.sources + b.sources)[:5], a.count + b.count)


def context(batch_id: str, batch: BatchSnapshot) -> dict:
    if batch.refusal or any(t.quarantine for t in batch.clean_tables):
        refuse("Resolve batch configuration or quarantined rows and import a new batch before review")
    config = (batch.dictionary_snapshot or {}).get("business_review")
    if not config:
        refuse("No business review contract configured for this batch")
    if {t.department for t in batch.clean_tables} != set(ROLES):
        refuse("Business review requires all four departments")
    # These are declared import contracts, not column-name guesses.
    for table in batch.clean_tables:
        if any(c.rule == "duplicate_row" for c in table.corrections):
            refuse(f"{table.department}: identical rows need transaction identity review before totals; import a corrected source")
        schema = config.get("inputs", {}).get(table.department, {})
        date_column = schema.get("date_column")
        if not date_column:
            refuse(f"No period field declared for {table.department}")
        for row in table.rows:
            for column in schema.get("nonnegative_columns", []):
                if number(row.get(column)) < 0:
                    refuse(f"{table.department}: {column} violates the declared nonnegative convention")
            if not str(row.get(date_column, "")).startswith(batch.period + "-"):
                refuse(f"{table.department}: a row is outside the requested period or lacks a date")
            currency = schema.get("currency")
            if currency and row.get(currency["column"]) != currency["value"]:
                refuse(f"{table.department}: currency missing or mismatched; conversion is not configured")
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
            "unsupported_topics": ["已批准上限", "已批准标准", "现行批准标准", *policy.get("unsupported_topics", [])], "checks": checks})
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
    explanation: str = Field(min_length=1, max_length=120)


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
        if any(topic in answer.explanation for topic in packet.get("unsupported_topics", [])):
            refuse("Explanation discusses a topic outside this department's declared evidence scope")
        verified.append({**fact, "action": answer.action, "explanation": answer.explanation,
            "explanation_status": "model_advice", "owner": packet["role"],
            "decision_owner": packet["decision_owner"], "execution_status": "proposed_only"})
    return {"role": packet["role"], "responsibility": packet["responsibility"],
            "decision_owner": packet["decision_owner"], "constraints": packet["constraints"], "checks": verified}
