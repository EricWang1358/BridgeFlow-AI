"""One check chain for a department file, shared by self-check and import (E14-UC03).

A contributor can ask "will this file be accepted?" before submitting. The answer is only worth
something if it is the answer import will give, so self-check and import run **the same
chain on the same prepared subject**; there is no second implementation to drift. The chain
groups what it finds:

- must fix: the file cannot be read as declared, rows were quarantined, or the declared
  templates and formulas reject a value (missing columns, text in number columns, empty keys,
  unrolled duplicate rows, a written figure that contradicts its formula);
- review: repairs the cleaner made on its own (formats, separators, header spelling);
- passed: checks that found nothing.

Findings name rows, columns and reasons from declarations; no business name is written here.
Cross-department checks (a department missing, formulas needing another department's columns)
belong to the batch and are not the contributor's to fix, so they are left out.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from pydantic import BaseModel, Field, computed_field

from bridgeflow.schemas import CleanTable

if TYPE_CHECKING:  # integration → business → api.batches imports this module
    from bridgeflow import integration

#: Integration issues a single department's file can cause, and so can fix.
DEPARTMENT_ISSUES = ("missing_column", "invalid_number", "invalid_period", "missing_key", "needs_rollup", "derived_mismatch")
#: Cap per check so a 200,000-row file returns a readable report, with the true count kept.
FINDINGS_PER_CHECK = 20


class Finding(BaseModel):
    check: str
    message: str
    row: int | None = None
    column: str = ""
    count: int = 1


class CheckReport(BaseModel):
    department: str
    filename: str
    declaration: str
    must_fix: list[Finding] = Field(default_factory=list)
    review: list[Finding] = Field(default_factory=list)
    passed: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def accepts(self) -> bool:
        return not self.must_fix


@dataclass
class CheckSubject:
    department: str
    filename: str
    declaration: str
    refusal: str | None = None
    table: CleanTable | None = None
    source: dict[str, Any] | None = None
    spec: integration.IntegrationSpec | None = None


class IntakeCheck(Protocol):
    id: str

    def run(self, subject: CheckSubject) -> tuple[list[Finding], list[Finding]]:
        """(must_fix, review)."""


class ReadableCheck:
    """The file parses as the declared sheet and header, with data rows."""

    id = "readable"

    def run(self, subject: CheckSubject) -> tuple[list[Finding], list[Finding]]:
        return ([Finding(check=self.id, message=subject.refusal)] if subject.refusal else []), []


class CleaningCheck:
    """What the cleaner quarantined (must fix) or repaired on its own (review)."""

    id = "cleaning"

    def run(self, subject: CheckSubject) -> tuple[list[Finding], list[Finding]]:
        table = subject.table
        if table is None:
            return [], []
        must: list[Finding] = []
        # A data-row correction that leaves no value is the cleaner refusing the row; its own reason is quoted.
        refused = [c for c in table.corrections if c.after is None and c.row >= 0]
        for correction in refused[:FINDINGS_PER_CHECK]:
            row = correction.source.source_row if correction.source and correction.source.source_row else correction.row + 2
            must.append(Finding(check=self.id, message=correction.reason, row=row, column=correction.column))
        unexplained = len(table.quarantine) - len({c.row for c in refused})
        if unexplained > 0:
            must.append(Finding(check=self.id, count=unexplained,
                                message="rows quarantined because fewer than half of their cells are filled; complete or remove them"))
        review: dict[str, Finding] = {}
        for correction in table.corrections:
            if correction in refused:
                continue
            finding = review.setdefault(correction.rule, Finding(check=self.id, message=correction.reason, column=correction.column, count=0))
            finding.count += 1
        return must, list(review.values())


class DeclarationCheck:
    """The declared templates and formulas accept this department's values."""

    id = "declaration"

    def run(self, subject: CheckSubject) -> tuple[list[Finding], list[Finding]]:
        from bridgeflow import integration

        spec, source = subject.spec, subject.source
        if spec is None or source is None or subject.department not in spec.departments:
            return [], []
        result = integration.integrate(spec, [integration.sheet_from_preview(subject.department, source)])
        must: dict[str, list[Finding]] = {}
        for issue in result.issues:
            if issue.kind in DEPARTMENT_ISSUES:
                must.setdefault(issue.kind, []).append(Finding(check=f"{self.id}:{issue.kind}", message=issue.message, column=issue.field))
        findings: list[Finding] = []
        for group in must.values():
            findings.extend(group[:FINDINGS_PER_CHECK])
            if len(group) > FINDINGS_PER_CHECK:
                findings.append(Finding(check=group[0].check, count=len(group) - FINDINGS_PER_CHECK,
                                        message="more findings of this kind"))
        return findings, []


@dataclass
class CheckChain:
    checks: tuple[IntakeCheck, ...]

    def run(self, subject: CheckSubject) -> CheckReport:
        report = CheckReport(department=subject.department, filename=subject.filename, declaration=subject.declaration)
        for check in self.checks:
            if subject.refusal and check.id != ReadableCheck.id:
                continue  # nothing else can be checked in a file that cannot be read
            must, review = check.run(subject)
            report.must_fix.extend(must)
            report.review.extend(review)
            if not must and not review:
                report.passed.append(check.id)
        return report


CHAIN = CheckChain((ReadableCheck(), CleaningCheck(), DeclarationCheck()))
