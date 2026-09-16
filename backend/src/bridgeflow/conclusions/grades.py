"""How much a number or conclusion can be relied on, as a reader sees it (E13-UC06).

Every figure BridgeFlow shows already carries provenance: a department's cell, a formula over
cells, a convention the business side has not confirmed, or a department subagent's advice.
This module turns that provenance into one of four grades so a reader knows how much review a
conclusion needs (docs/requirements/00-foundations.md §5.3):

    G1 source      a department's original cell
    G2 formula     a declared formula over sources
    G3 convention  depends on a convention the business side has not confirmed
    G4 judgement   a subagent's explanation or proposed action

A provenance tree takes the **weakest** grade among its nodes (Composite). A broken chain is a
node of its own, `MissingSource`, so it is reported rather than silently graded. The grader is a
separate visitor so node classes stay plain data. No business name appears here; conventions are
referred to by the keys their declarations use.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class Grade(IntEnum):
    SOURCE = 1
    FORMULA = 2
    CONVENTION = 3
    JUDGEMENT = 4

    @property
    def label(self) -> str:
        return f"G{int(self)}"


@dataclass(frozen=True)
class ProvenanceNode:
    """A step in why a figure has its value."""

    def children(self) -> tuple[ProvenanceNode, ...]:
        return ()


@dataclass(frozen=True)
class SourceCell(ProvenanceNode):
    reference: str


@dataclass(frozen=True)
class FormulaNode(ProvenanceNode):
    name: str
    inputs: tuple[ProvenanceNode, ...] = ()

    def children(self) -> tuple[ProvenanceNode, ...]:
        return self.inputs


@dataclass(frozen=True)
class ConventionNode(ProvenanceNode):
    key: str
    inner: ProvenanceNode
    confirmed: bool = False

    def children(self) -> tuple[ProvenanceNode, ...]:
        return (self.inner,)


@dataclass(frozen=True)
class JudgementNode(ProvenanceNode):
    cites: tuple[ProvenanceNode, ...] = ()

    def children(self) -> tuple[ProvenanceNode, ...]:
        return self.cites


@dataclass(frozen=True)
class MissingSource(ProvenanceNode):
    reason: str


@dataclass
class GradeResult:
    grade: Grade | None
    #: Human-readable steps, weakest first, for the "why this grade" disclosure.
    chain: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"grade": self.grade.label if self.grade else None, "chain": self.chain, "missing": self.missing}


class EvidenceGrader:
    """Grades a provenance tree: the weakest node wins; any missing source leaves it ungraded."""

    def grade(self, node: ProvenanceNode) -> GradeResult:
        own, step = self._own(node)
        result = GradeResult(own, [step] if step else [])
        if isinstance(node, MissingSource):
            result.missing.append(node.reason)
        for child in node.children():
            inner = self.grade(child)
            result.missing.extend(inner.missing)
            result.chain.extend(s for s in inner.chain if s not in result.chain)
            if inner.grade is not None and (result.grade is None or inner.grade > result.grade):
                result.grade = inner.grade
        if result.missing:
            result.grade = None
        result.chain.sort(key=lambda s: -int(s[1]) if s[:1] == "G" and s[1:2].isdigit() else 0)
        return result

    @staticmethod
    def _own(node: ProvenanceNode) -> tuple[Grade | None, str]:
        if isinstance(node, SourceCell):
            return Grade.SOURCE, f"G1 {node.reference}"
        if isinstance(node, FormulaNode):
            return Grade.FORMULA, f"G2 {node.name}"
        if isinstance(node, ConventionNode):
            return (Grade.FORMULA, f"G2 {node.key} (confirmed)") if node.confirmed else (Grade.CONVENTION, f"G3 {node.key}")
        if isinstance(node, JudgementNode):
            return Grade.JUDGEMENT, "G4 model advice"
        return None, ""


def _assumption_key(note: str) -> str:
    # Integration writes each dependency as "<key>: <declared text>"; the key is the handle.
    return note.split(":", 1)[0].strip()


def master_cell(column: str, provenance: dict[str, dict[str, Any]], seen: frozenset[str] = frozenset()) -> ProvenanceNode:
    """The provenance tree of one master-table cell, from the integration provenance record."""
    cell = provenance.get(column)
    if cell is None:
        return MissingSource(f"{column}: no provenance")
    if "conflict" in cell:
        return MissingSource(f"{column}: departments disagree or the formula contradicts the value")
    if "formula" in cell or "rule" in cell:
        name = str(cell.get("formula") or cell.get("rule"))
        inputs = tuple(master_cell(i, provenance, seen | {column}) if i not in seen else MissingSource(f"{i}: cyclic")
                       for i in cell.get("inputs", []))
        node: ProvenanceNode = FormulaNode(name, inputs)
    elif "department" in cell:
        rows = cell.get("rows") or [cell.get("row")]
        node = SourceCell(f"{cell['department']} · {cell.get('file', '')} · row {','.join(map(str, rows))} · {cell.get('column', '')}")
    else:
        return MissingSource(f"{column}: provenance has no source or formula")
    for note in cell.get("assumptions", []):
        key = _assumption_key(note)
        # A roll-up convention only shapes summed, joined or recomputed fields; a field that
        # must merely be identical across the rolled-up rows does not rest on it.
        if key.startswith("rollup.") and cell.get("rollup") == "identical":
            continue
        node = ConventionNode(key, node)
    return node


def review_check(check: dict[str, Any], conventions: list[str]) -> ProvenanceNode:
    """A validated review check: its metric is a declared formula over cited cells."""
    sources = tuple(SourceCell(f"{s.get('department', '')} · {s.get('filename', '')} · row {s.get('source_row') or s.get('row')} · "
                               f"{s.get('original_column') or s.get('column', '')}") for s in check.get("sources", []))
    if not sources:
        return MissingSource(f"{check.get('metric', '')}: no cited cells")
    node: ProvenanceNode = FormulaNode(str(check.get("metric", "")), sources)
    for key in conventions:
        node = ConventionNode(key, node)
    return node


def advice(check: dict[str, Any], conventions: list[str]) -> ProvenanceNode:
    """A subagent's proposed action and explanation rest on the check they cite."""
    return JudgementNode((review_check(check, conventions),))


def grade_master(provenance_rows: list[dict[str, dict[str, Any]]]) -> tuple[list[dict[str, dict[str, Any]]], dict[str, int]]:
    """Grade every cell of every row; returns per-row grade maps and the grade distribution."""
    grader, graded, counts = EvidenceGrader(), [], {"G1": 0, "G2": 0, "G3": 0, "G4": 0, "missing": 0}
    for provenance in provenance_rows:
        row = {}
        for column in provenance:
            result = grader.grade(master_cell(column, provenance))
            row[column] = result.as_dict()
            counts[result.grade.label if result.grade else "missing"] += 1
        graded.append(row)
    return graded, counts
