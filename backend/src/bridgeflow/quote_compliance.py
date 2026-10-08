"""Contract terms of a quotation checked against the company's legal requirements (#302).

The first cut is a read-only sample: two built-in quotations, each with its own contract text
and the structured terms a person read off it, judged against one published version of the
legal requirements. Nothing here stores, edits or sends anything.

Two layers decide, and only one of them is a model:

- a requirement on a structured term (payment days, penalty cap, liability) is arithmetic on
  the value a person entered, and that value must quote the contract verbatim;
- a requirement that a kind of clause exist (intellectual property, warranty) is a model's
  reading of the text. Its conclusions are frozen in a file and re-admitted on every load:
  an excerpt that is not in the contract, a "compliant" without a citation, a number in the
  prose, or a conclusion made against another version degrades that line to undetermined.

Missing information is never compliance. A term the contract does not state is
"undetermined"; a clause can be declared absent only when the contract was entered in full.
The conclusion is a reference for the legal reviewer, never a release.
"""
from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal

import openpyxl
import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from bridgeflow.documents import DocumentContract, StructuredDocument, evaluate_document
from bridgeflow.schemas import SourceRef

ContractField = Literal["payment_days", "prepayment_ratio", "monthly_payment_ratio", "delivery_days",
                        "penalty_cap_ratio", "liability", "warranty_months"]
FIELD_UNITS: dict[str, str] = {"payment_days": "days", "prepayment_ratio": "ratio", "monthly_payment_ratio": "ratio",
                               "delivery_days": "days", "penalty_cap_ratio": "ratio", "liability": "", "warranty_months": "months"}
RATIO_FIELDS = {"prepayment_ratio", "monthly_payment_ratio", "penalty_cap_ratio"}
LIABILITY = ("capped", "unlimited")
Status = Literal["compliant", "non_compliant", "undetermined"]
NOTICE = "A reference for the legal reviewer only; it does not replace legal review, and a person decides."
MAX_EXPLANATION = 240


class CaseError(ValueError):
    """The sample bundle cannot be trusted as written; the page says so instead of guessing."""


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Clause(StrictModel):
    id: str
    heading: str
    text: str


class FieldValue(StrictModel):
    value: str = Field(min_length=1, max_length=64)
    clause: str = Field(min_length=1, max_length=16)
    excerpt: str = Field(min_length=2, max_length=240)


class ContractTerms(StrictModel):
    file: str
    complete: bool
    fields: dict[ContractField, FieldValue] = Field(default_factory=dict)


class LegalRequirement(StrictModel):
    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=160)
    basis: str = Field(min_length=1, max_length=160)
    kind: Literal["field_max", "field_min", "field_in", "clause_required", "clause_forbidden"]
    field: ContractField | None = None
    threshold: Decimal | None = Field(default=None, allow_inf_nan=False)
    allowed: list[str] | None = None
    topic: str | None = Field(default=None, max_length=80)
    guidance: str | None = Field(default=None, max_length=480)
    suggestion: str = Field(min_length=1, max_length=240)

    @model_validator(mode="after")
    def _shape(self) -> LegalRequirement:
        if self.kind in ("field_max", "field_min"):
            if self.field is None or self.field == "liability" or self.threshold is None or self.allowed or self.topic:
                raise ValueError(f"{self.id}: a bound needs a numeric field and a threshold")
        elif self.kind == "field_in":
            if self.field is None or not self.allowed or self.threshold is not None or self.topic:
                raise ValueError(f"{self.id}: field_in needs a field and allowed values")
        elif self.field is not None or self.threshold is not None or self.allowed or not self.topic or not self.guidance:
            raise ValueError(f"{self.id}: a clause requirement needs a topic and guidance, no field")
        return self

    @property
    def decided_by(self) -> Literal["rule", "model"]:
        return "rule" if self.kind.startswith("field_") else "model"


class Consistency(StrictModel):
    metric: str
    field: ContractField
    title: str


class LegalRequirements(StrictModel):
    version: int = Field(ge=1)
    title: str
    published_by: str
    published_at: str
    requirements: list[LegalRequirement] = Field(min_length=1, max_length=48)
    consistency: list[Consistency] = Field(default_factory=list, max_length=24)

    @model_validator(mode="after")
    def _unique(self) -> LegalRequirements:
        if len({r.id for r in self.requirements}) != len(self.requirements):
            raise ValueError("Duplicate legal requirement id")
        return self


class QuoteCase(StrictModel):
    id: str
    title: str
    customer: str
    extraction: str
    contract: ContractTerms


class CaseBundle(StrictModel):
    dictionary: str
    legal: str
    judgements: str
    quotes: list[QuoteCase] = Field(min_length=1, max_length=16)


class Citation(StrictModel):
    clause: str = Field(max_length=16)
    excerpt: str = Field(max_length=240)


class ClauseJudgement(StrictModel):
    requirement_id: str = Field(max_length=64)
    status: Status
    citations: list[Citation] = Field(default_factory=list, max_length=4)
    explanation: str = Field(default="", max_length=2000)


class FrozenQuote(StrictModel):
    legal_version: int
    contract_sha256: str
    judgements: list[dict]


class FrozenJudgements(StrictModel):
    generated_by: str
    generated_at: str
    quotes: dict[str, FrozenQuote] = Field(default_factory=dict)


# --- contract text --------------------------------------------------------------------

_NUMERALS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def _chinese_number(text: str) -> int:
    if text.isdecimal():
        return int(text)
    if "十" in text:
        tens, _, ones = text.partition("十")
        return (_NUMERALS.get(tens, 1) if tens else 1) * 10 + (_NUMERALS[ones] if ones else 0)
    return _NUMERALS[text]


_CJK = re.compile(r"[\u3000-\u303f\u3400-\u9fff\uff00-\uffef]")


def _join(left: str, right: str) -> str:
    """A wrapped line rejoins with a space in English, with nothing between Chinese characters."""
    if not left or not right or _CJK.match(left[-1]) or _CJK.match(right[0]):
        return left + right
    return f"{left} {right}"


_ARTICLE = re.compile(r"^##\s*(?:第([一二三四五六七八九十\d]+)条|Article\s+(\d+))\s*(.*)$")


def split_clauses(text: str) -> list[Clause]:
    """`## Article N title` (or `## 第N条 标题`) is an article; a line opening `N.M ` inside it is a clause, otherwise the article is one."""
    clauses: list[Clause] = []
    article: tuple[int, str] | None = None
    body: list[str] = []

    def close() -> None:
        if article is None:
            return
        number, heading = article
        numbered = re.compile(rf"^{number}\.(\d+)\s+(.*)$")
        parts: list[Clause] = []
        loose: list[str] = []
        for line in body:
            match = numbered.match(line)
            if match:
                parts.append(Clause(id=f"{number}.{match[1]}", heading=heading, text=match[2].strip()))
            elif parts:
                parts[-1] = parts[-1].model_copy(update={"text": _join(parts[-1].text, line)})
            else:
                loose.append(line)
        if loose:
            text = ""
            for line in loose:
                text = _join(text, line)
            parts.insert(0, Clause(id=str(number), heading=heading, text=text))
        clauses.extend(parts)

    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            close()
            match = _ARTICLE.match(line)
            article = (_chinese_number(match[1] or match[2]), line[3:].strip()) if match else None
            body = []
        elif article is not None and line and not line.startswith(">"):
            body.append(line)
    close()
    if len({c.id for c in clauses}) != len(clauses):
        raise CaseError("Contract clause numbers repeat")
    return clauses


def _number(value: str) -> Decimal:
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise CaseError(f"Not a number: {value}") from exc
    if not result.is_finite():
        raise CaseError(f"Not a finite number: {value}")
    return result


def verify_terms(terms: ContractTerms, clauses: list[Clause]) -> None:
    """A structured term exists only if it quotes the contract verbatim."""
    by_id = {c.id: c for c in clauses}
    for name, field in terms.fields.items():
        clause = by_id.get(field.clause)
        if clause is None or field.excerpt not in clause.text:
            raise CaseError(f"Contract term {name} does not quote clause {field.clause} verbatim")
        if name == "liability":
            if field.value not in LIABILITY:
                raise CaseError("Liability must be capped or unlimited")
            continue
        value = _number(field.value)
        if value < 0 or (name in RATIO_FIELDS and value > 1):
            raise CaseError(f"Contract term {name} is out of range")


# --- quotation draft ------------------------------------------------------------------


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_extraction(base: Path, name: str, contract: DocumentContract, books: dict | None = None) -> StructuredDocument:
    """Re-open each original and confirm its excerpt or cell, as the human record claims."""
    books = {} if books is None else books
    record = yaml.safe_load((base / name).read_text(encoding="utf-8"))
    facts = {}
    for key, fact in record["facts"].items():
        path = base / fact["file"]
        digest = _sha256(path)
        spec = contract.inputs.get(key)
        unit = spec.unit if spec else ""
        if "cell" in fact:
            sheet, cell = fact["cell"].split("!")
            if path not in books:
                books[path] = openpyxl.load_workbook(path, data_only=True, read_only=True)
            stored = books[path][sheet][cell].value
            if stored is None or _number(str(stored)) != _number(str(fact["value"])):
                raise CaseError(f"{name}: {key} does not match {fact['cell']}")
            source = SourceRef(department=fact["department"], batch=record["document_id"], filename=path.name,
                               sheet=sheet, paragraph=cell, excerpt=f"{sheet}!{cell} = {stored}", document_sha256=digest)
        else:
            section = path.read_text(encoding="utf-8").split(f"## {fact['paragraph']}", 1)
            if len(section) != 2 or fact["excerpt"] not in section[1].split("\n## ", 1)[0]:
                raise CaseError(f"{name}: {key} excerpt is not in {fact['file']}")
            source = SourceRef(department=fact["department"], batch=record["document_id"], filename=path.name,
                               paragraph=fact["paragraph"], excerpt=fact["excerpt"], document_sha256=digest)
        facts[key] = {"status": "extracted", "value": str(fact["value"]), "unit": unit, "sources": [source.model_dump()]}
    return StructuredDocument.model_validate({"id": record["document_id"], "status": "extracted", "facts": facts})


# --- judgement ------------------------------------------------------------------------


def _result(requirement: LegalRequirement, status: Status, reason: str, *, evidence: list[Citation] | None = None,
            observed: str | None = None, explanation: str = "") -> dict:
    return {"requirement_id": requirement.id, "title": requirement.title, "basis": requirement.basis,
            "kind": requirement.kind, "decided_by": requirement.decided_by, "status": status, "reason_code": reason,
            "evidence": [c.model_dump() for c in evidence or []], "observed": observed,
            "unit": FIELD_UNITS.get(requirement.field or "", ""), "explanation": explanation,
            "explanation_status": "model_advice" if explanation else "",
            "suggestion": requirement.suggestion if status == "non_compliant" else None}


def judge_rule(requirement: LegalRequirement, terms: ContractTerms) -> dict:
    field = terms.fields.get(requirement.field) if requirement.field else None
    if field is None:
        return _result(requirement, "undetermined", "missing_field")
    evidence = [Citation(clause=field.clause, excerpt=field.excerpt)]
    if requirement.kind == "field_in":
        ok = field.value in (requirement.allowed or [])
    else:
        value, threshold = _number(field.value), requirement.threshold
        assert threshold is not None
        ok = value <= threshold if requirement.kind == "field_max" else value >= threshold
    return _result(requirement, "compliant" if ok else "non_compliant", "within_bound" if ok else "outside_bound",
                   evidence=evidence, observed=field.value)


def admit_judgements(requirements: list[LegalRequirement], clauses: list[Clause], complete: bool,
                     answers: list[dict] | None, *, stale: bool = False) -> list[dict]:
    """Re-check a model's clause conclusions against the contract; a bad line degrades, the rest stand."""
    by_clause = {c.id: c for c in clauses}
    if answers is None or stale:
        reason = "judgement_stale" if stale else "judgement_missing"
        return [_result(r, "undetermined", reason) for r in requirements]
    parsed: dict[str, ClauseJudgement | None] = {}
    for raw in answers:
        try:
            answer = ClauseJudgement.model_validate(raw)
        except ValidationError:
            continue
        # A duplicate is not resolved by picking one: both are discarded.
        parsed[answer.requirement_id] = None if answer.requirement_id in parsed else answer
    results = []
    for requirement in requirements:
        found = parsed.get(requirement.id)
        if found is None:
            results.append(_result(requirement, "undetermined", "judgement_missing"))
            continue
        answer = found
        cited = all(c.clause in by_clause and len(c.excerpt) >= 2 and c.excerpt in by_clause[c.clause].text
                    for c in answer.citations)
        prose = answer.explanation.strip()
        if (not cited or not prose or len(prose) > MAX_EXPLANATION
                or any(ch.isdecimal() for ch in prose)
                or (answer.status == "compliant" and not answer.citations)
                or (answer.status == "non_compliant" and requirement.kind == "clause_forbidden" and not answer.citations)):
            results.append(_result(requirement, "undetermined", "model_rejected"))
            continue
        if answer.status == "non_compliant" and requirement.kind == "clause_required" and not complete:
            results.append(_result(requirement, "undetermined", "clause_absent_terms_incomplete"))
            continue
        reason = {"compliant": "clause_found", "undetermined": "model_undetermined",
                  "non_compliant": "clause_absent" if requirement.kind == "clause_required" else "clause_present"}[answer.status]
        results.append(_result(requirement, answer.status, reason, evidence=answer.citations, explanation=prose))
    return results


def check_consistency(rules: list[Consistency], draft: dict, terms: ContractTerms) -> list[dict]:
    fields = {f["metric"]: f for f in draft.get("fields", [])} if draft.get("status") == "draft" else None
    out = []
    for rule in rules:
        item: dict = {"metric": rule.metric, "field": rule.field, "title": rule.title, "quote_value": None, "quote_unit": "",
                "quote_sources": [], "contract_value": None, "evidence": [], "status": "undetermined"}
        term = terms.fields.get(rule.field)
        if term is not None:
            item.update(contract_value=term.value, evidence=[Citation(clause=term.clause, excerpt=term.excerpt).model_dump()])
        quoted = None if fields is None else fields.get(rule.metric)
        if quoted is not None:
            item.update(quote_value=quoted["value"], quote_unit=quoted["unit"], quote_sources=quoted["sources"])
        if fields is None:
            item["reason_code"] = "quote_draft_refused"
        elif quoted is None:
            item["reason_code"] = "metric_not_in_draft"
        elif term is None:
            item["reason_code"] = "missing_field"
        else:
            same = _number(quoted["value"]) == _number(term.value)
            item.update(status="consistent" if same else "inconsistent", reason_code="equal" if same else "differs")
        out.append(item)
    return out


def overall(requirements: list[dict], consistency: list[dict]) -> Status:
    if any(r["status"] == "non_compliant" for r in requirements) or any(c["status"] == "inconsistent" for c in consistency):
        return "non_compliant"
    if any(r["status"] == "undetermined" for r in requirements) or any(c["status"] == "undetermined" for c in consistency):
        return "undetermined"
    return "compliant"


# --- the sample bundle ----------------------------------------------------------------


def _yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise CaseError(f"{path.name} must be a mapping")
    return data


def contract_shape(config: dict) -> str:
    """The arithmetic of a quotation contract, without its words: a translated declaration has the same shape."""
    contract = DocumentContract.model_validate(config)
    shape = {"inputs": {k: [v.owner, str(v.minimum), str(v.exclusive_minimum)] for k, v in contract.inputs.items()},
             "metrics": {k: [v.expression, v.rounding.model_dump() if v.rounding else None] for k, v in contract.metrics.items()},
             "checks": [[c.id, c.owner, c.metric, c.attention_when, str(c.threshold), c.threshold_metric, c.block_on_attention]
                        for c in contract.checks],
             "roles": sorted(contract.roles), "outputs": contract.outputs}
    return hashlib.sha256(json.dumps(shape, sort_keys=True).encode()).hexdigest()


class Bundle:
    """The sample, loaded and verified once per request."""

    def __init__(self, path: Path):
        self.base = path.parent
        try:
            self.spec = CaseBundle.model_validate(_yaml(path))
            self.legal = LegalRequirements.model_validate(_yaml(self.base / self.spec.legal))
            self.config = _yaml(self.base / self.spec.dictionary)["quotation"]
            frozen_path = self.base / self.spec.judgements
            self.frozen = FrozenJudgements.model_validate(_yaml(frozen_path)) if frozen_path.is_file() else None
        except (OSError, KeyError, yaml.YAMLError, ValidationError) as exc:
            raise CaseError(f"Quotation sample is invalid: {exc}") from exc
        if len({q.id for q in self.spec.quotes}) != len(self.spec.quotes):
            raise CaseError("Duplicate quotation id")

    def quote(self, quote_id: str) -> QuoteCase | None:
        return next((q for q in self.spec.quotes if q.id == quote_id), None)

    def contract(self, quote: QuoteCase) -> tuple[list[Clause], str]:
        path = self.base / quote.contract.file
        try:
            clauses = split_clauses(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise CaseError(f"Contract file missing: {quote.contract.file}") from exc
        if not clauses:
            raise CaseError(f"No clauses found in {quote.contract.file}")
        verify_terms(quote.contract, clauses)
        return clauses, _sha256(path)

    def clause_packet(self, quote: QuoteCase) -> dict:
        clauses, _ = self.contract(quote)
        return {"requirements": [{"id": r.id, "title": r.title, "kind": r.kind, "topic": r.topic, "guidance": r.guidance}
                                 for r in self.legal.requirements if r.decided_by == "model"],
                "clauses": [c.model_dump() for c in clauses], "complete": quote.contract.complete}

    def evaluate(self, quote: QuoteCase, config: dict, declaration: SourceRef) -> dict:
        contract = DocumentContract.model_validate(config)
        try:
            document = load_extraction(self.base, quote.extraction, contract)
        except (OSError, KeyError, ValueError, ValidationError) as exc:
            raise CaseError(f"Extraction for {quote.id} is invalid: {exc}") from exc
        draft = evaluate_document(config, document, declaration)
        clauses, sha = self.contract(quote)
        rule_reqs = [r for r in self.legal.requirements if r.decided_by == "rule"]
        model_reqs = [r for r in self.legal.requirements if r.decided_by == "model"]
        frozen = self.frozen.quotes.get(quote.id) if self.frozen else None
        stale = frozen is not None and (frozen.legal_version != self.legal.version or frozen.contract_sha256 != sha)
        judged = {r["requirement_id"]: r for r in (
            [judge_rule(r, quote.contract) for r in rule_reqs]
            + admit_judgements(model_reqs, clauses, quote.contract.complete,
                               frozen.judgements if frozen else None, stale=stale))}
        requirements = [judged[r.id] for r in self.legal.requirements]
        consistency = check_consistency(self.legal.consistency, draft, quote.contract)
        return {
            "quote": {"id": quote.id, "title": quote.title, "customer": quote.customer},
            "draft": draft,
            "contract": {"file": quote.contract.file, "document_sha256": sha, "complete": quote.contract.complete,
                         "clauses": [c.model_dump() for c in clauses],
                         "fields": {name: {**f.model_dump(), "unit": FIELD_UNITS[name]} for name, f in quote.contract.fields.items()}},
            "compliance": {"legal_version": self.legal.version, "overall": overall(requirements, consistency),
                           "requirements": requirements, "consistency": consistency, "notice": NOTICE,
                           "judgement": {"generated_by": self.frozen.generated_by if self.frozen else "",
                                         "generated_at": self.frozen.generated_at if self.frozen else "",
                                         "stale": stale, "present": frozen is not None}},
        }

    def summary(self) -> dict:
        return {"legal": self.legal.model_dump(mode="json"),
                "quotes": [{"id": q.id, "title": q.title, "customer": q.customer} for q in self.spec.quotes]}
