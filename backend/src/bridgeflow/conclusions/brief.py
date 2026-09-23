"""The one-page monthly brief (E13-UC01).

A deterministic projection of what is already saved: the finalized review report, the frozen
batch and its cross-department master. Nothing is computed that the review did not compute, and
no model is called. What goes on the page, and in which order, is declared by the dictionary
owner under `business_review.brief`:

    brief:
      key_metrics: [<metric id>, ...]        # 1–5, shown in this order
      severity: [<check id>, ...]            # attention items, most severe first
      conventions: {<metric id>: [<convention key>, ...]}   # optional

Without that declaration the brief is refused rather than guessed. A department whose review
did not validate is named as missing; its metrics are neither ranked nor shown as OK. The brief
is bound to the batch, report and declaration versions it was built from, and says when a newer
report has replaced the one it shows.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field, ValidationError

from bridgeflow.conclusions.comparison import Comparison
from bridgeflow.conclusions.grades import EvidenceGrader, advice, grade_master, review_check


class BriefDeclaration(BaseModel):
    key_metrics: list[str] = Field(min_length=1, max_length=5)
    severity: list[str] = Field(default_factory=list)
    conventions: dict[str, list[str]] = Field(default_factory=dict)


class MetricLine(BaseModel):
    metric: str
    check_id: str
    title: str
    value: float
    unit: str
    status: str
    formula: str
    source_count: int
    owner: str
    grade: dict[str, Any]
    #: Change against the base period (E13-UC02); state says why there is none.
    change: dict[str, Any] | None = None


class AttentionItem(BaseModel):
    check_id: str
    title: str
    metric: str
    value: float
    unit: str
    threshold: float
    attention_when: str
    #: The declared formula, so the page can say how the figure was computed next to it.
    formula: str = ""
    owner: str
    decision_owner: str
    action: str
    explanation: str
    grade: dict[str, Any]
    advice_grade: dict[str, Any]
    #: Where this figure came from: department, file, row and column, capped, with the true
    #: total beside it. References, never values — the browser opens the source to see those.
    sources: list[dict[str, Any]] = Field(default_factory=list)
    source_count: int = 0


class ConclusionBrief(BaseModel):
    period: str
    bound: dict[str, str]
    report_status: str
    stale: bool
    latest_report_id: str
    missing_departments: list[str]
    headline: dict[str, int]
    key_metrics: list[MetricLine]
    attention: list[AttentionItem]
    open_items: dict[str, int]
    completeness: dict[str, int]
    grade_summary: dict[str, int]
    manager_decision: str
    limitations: list[str]
    comparison: Comparison | None = None


def declaration(dictionary: dict | None) -> BriefDeclaration:
    raw = ((dictionary or {}).get("business_review") or {}).get("brief")
    if raw is None:
        raise HTTPException(409, "No brief is declared for this batch's review contract; ask the dictionary owner to declare business_review.brief")
    try:
        return BriefDeclaration.model_validate(raw)
    except ValidationError as exc:
        raise HTTPException(503, "The brief declaration is invalid; ask the dictionary owner to correct business_review.brief") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()[:16]


@dataclass
class BriefBuilder:
    """Assembles the brief step by step; each step can be exercised on its own in tests."""

    batch_id: str
    report: dict[str, Any]
    latest_report_id: str
    dictionary: dict[str, Any]
    batch_counts: dict[str, int]
    master: Any = None  # integration.MasterResult | None
    comparison: Comparison | None = None
    #: Conventions the business side has confirmed (E13-UC05): what rests on them grades G2.
    confirmed_conventions: frozenset[str] = frozenset()
    _declared: BriefDeclaration | None = None
    _validated: dict[str, dict] = field(default_factory=dict)
    _missing: list[str] = field(default_factory=list)
    _grader: EvidenceGrader = field(default_factory=EvidenceGrader)
    _grades: dict[str, int] = field(default_factory=lambda: {"G1": 0, "G2": 0, "G3": 0, "G4": 0, "missing": 0})

    def with_declaration(self) -> BriefBuilder:
        self._declared = declaration(self.dictionary)
        return self

    def with_report(self) -> BriefBuilder:
        for role in self.report.get("roles", []):
            if role.get("status") == "validated":
                for check in role.get("checks", []):
                    self._validated[check["check_id"]] = {**check, "role": role["role"]}
            else:
                self._missing.append(role["role"])
        return self

    def _count(self, grade: dict[str, Any]) -> dict[str, Any]:
        self._grades[grade["grade"] or "missing"] += 1
        return grade

    def _metric_grade(self, check: dict[str, Any]) -> dict[str, Any]:
        conventions = self._declared.conventions.get(check["metric"], []) if self._declared else []
        return self._count(self._grader.grade(review_check(check, conventions, self.confirmed_conventions)).as_dict())

    def key_metrics(self) -> list[MetricLine]:
        lines = []
        for metric in self._declared.key_metrics:
            check = next((c for c in self._validated.values() if c["metric"] == metric), None)
            if check is None:
                continue  # its department did not validate, or the metric has no check
            change = next((c for c in (self.comparison.metrics if self.comparison else []) if c.metric == metric), None)
            lines.append(MetricLine(metric=metric, check_id=check["check_id"], title=check["title"], value=check["value"],
                                    unit=check["unit"], status=check["expected_status"], formula=check["formula"],
                                    source_count=check["source_count"], owner=check["role"], grade=self._metric_grade(check),
                                    change=change.model_dump() if change else None))
        return lines

    def attention(self) -> list[AttentionItem]:
        rank = {check_id: i for i, check_id in enumerate(self._declared.severity)}
        flagged = [c for c in self._validated.values() if c["expected_status"] == "attention"]
        # Declared order first; anything the declaration does not rank follows in report order.
        flagged.sort(key=lambda c: rank.get(c["check_id"], len(rank)))
        items = []
        for check in flagged:
            conventions = self._declared.conventions.get(check["metric"], [])
            items.append(AttentionItem(
                check_id=check["check_id"], title=check["title"], metric=check["metric"], value=check["value"],
                unit=check["unit"], threshold=check["threshold"], attention_when=check["attention_when"],
                formula=str(check.get("formula", "")), owner=check["role"], decision_owner=check["decision_owner"], action=check["action"],
                explanation=check["explanation"], grade=self._metric_grade(check),
                advice_grade=self._count(self._grader.grade(advice(check, conventions, self.confirmed_conventions)).as_dict()),
                # Capped, with the real total beside it: a figure over 200k rows cites its
                # sources by reference and count, never by shipping every cell back.
                sources=[{k: v for k, v in source.items() if k in
                          ("department", "filename", "sheet", "row", "source_row", "column", "original_column")}
                         for source in check.get("sources", [])[:5]],
                source_count=int(check.get("source_count", 0))))
        return items

    def build(self) -> ConclusionBrief:
        if self._declared is None:
            self.with_declaration()
        if not self._validated and not self._missing:
            self.with_report()
        metrics, attention = self.key_metrics(), self.attention()
        master_issues = len(self.master.issues) if self.master is not None else 0
        complete_rows = sum(1 for r in self.master.rows if r.complete) if self.master is not None else 0
        if self.master is not None:
            _, cell_grades = grade_master([row.provenance for row in self.master.rows], self.confirmed_conventions)
            assumptions = len(self.master.assumptions)
        else:
            cell_grades, assumptions = {}, 0
        open_items = {"master_issues": master_issues, "quarantined_rows": self.batch_counts.get("quarantined_rows", 0),
                      "column_questions": self.batch_counts.get("column_questions", 0)}
        open_items["total"] = sum(open_items.values())
        ok = sum(1 for c in self._validated.values() if c["expected_status"] == "ok")
        return ConclusionBrief(
            period=str(self.report.get("period", "")),
            bound={"batch_id": self.batch_id, "report_id": self.report["report_id"],
                   "dictionary": _digest(self.dictionary), "integration": getattr(self.master, "version", "") or ""},
            report_status=self.report.get("status", "partial"),
            stale=self.report["report_id"] != self.latest_report_id,
            latest_report_id=self.latest_report_id,
            missing_departments=self._missing,
            headline={"attention": len(attention), "ok": ok, "open_items": open_items["total"],
                      "missing_departments": len(self._missing)},
            key_metrics=metrics, attention=attention, open_items=open_items,
            completeness={"master_rows": len(self.master.rows) if self.master is not None else 0,
                          "complete_rows": complete_rows, "assumptions": assumptions,
                          **{f"cells_{k}": v for k, v in cell_grades.items()}},
            grade_summary=self._grades,
            manager_decision=str(self.report.get("manager_decision", "")),
            limitations=list(self.report.get("limitations", [])),
            comparison=self.comparison,
        )
