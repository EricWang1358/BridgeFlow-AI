from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any, NamedTuple

from pydantic import BaseModel

from bridgeflow import grain
from bridgeflow.agents.base import Agent
from bridgeflow.agents.semantic_resolver import FieldDictionary, load_field_dictionary
from bridgeflow.config import REPO_ROOT, settings
from bridgeflow.schemas import (
    ApprovalCard,
    CleanTable,
    Entity,
    EntityGraph,
    Finding,
    MasterTable,
    RiskReport,
    Tension,
)

_SEVERITY_ORDER = {"critical": 0, "warning": 1, "watch": 2, "info": 3}


class SOPInput(BaseModel):
    period: str
    tables: list[CleanTable]
    graph: EntityGraph
    findings: list[Finding] = []
    tensions: list[Tension] = []


class SOPOutput(BaseModel):
    master_table: MasterTable
    risk_report: RiskReport


class SOPFlowEngine(Agent[SOPInput, SOPOutput]):
    """Stage 4 — assemble the one table everybody argues over, and the decisions it implies.

    Deterministic on purpose: no LLM call. A number on the Master Table must be
    traceable to a source row, or a judge (and later an auditor) will not trust it.
    """

    slug = "sop"

    async def run(self, payload: SOPInput, *, dictionary: FieldDictionary | None = None) -> SOPOutput:
        master = self._build_master_table(payload, dictionary=dictionary)
        report = RiskReport(
            period=payload.period,
            findings=sorted(payload.findings, key=lambda f: _SEVERITY_ORDER[f.severity]),
            tensions=payload.tensions,
            cards=self._approval_cards(payload.findings),
        )
        return SOPOutput(master_table=master, risk_report=report)

    def _build_master_table(self, payload: SOPInput, *, dictionary: FieldDictionary | None = None) -> MasterTable:
        """One row per canonical entity per month, each department's column prefixed.

        Two things this stops doing on purpose.

        It keyed rows on the **raw cell**, so `SKU-A1` and `sku-a1` — already merged
        into one entity by the resolver, with an alias list to prove it — came out as
        two rows. The alignment was computed upstream and thrown away in the last
        step, which is the step the demo shows.

        It combined several source rows arriving in one cell by **overwriting**, so a
        material bought on three POs appeared as the last one: 4 units, no price, and
        the 4,850→5,200 drift inside the month invisible. Nothing raised about either.

        So cells now gather every value that arrives, and what happens next is
        declared rather than behavioural: a measurement folds by the `rollups` policy
        the dictionary states for it, an attribute that disagrees lists what it
        disagreed between, and a fold with no stated policy refuses the table.
        `CLAUDE.md`: 跑不动比静默出错好 — combining a quantity and a price the same way
        is arithmetically legal and wrong, and only the business knows which is which.
        """
        dictionary = dictionary if dictionary is not None else load_field_dictionary(_dictionary_path())
        canonical = _canonical_index(payload.graph)

        unjoinable: list[str] = []
        cells: dict[RowKey, dict[str, list[Any]]] = defaultdict(lambda: defaultdict(list))
        origins: dict[RowKey, int] = defaultdict(int)
        labels: dict[RowKey, str] = {}
        notes: dict[RowKey, str] = {}
        unmatched: set[str] = set()

        for table in payload.tables:
            key = _primary_key_column(table, dictionary)
            if key is None:
                # No declared join key. Merging on a guess would corrupt every row.
                unjoinable.append(table.department)
                continue
            date_column = _period_column(table, dictionary)

            for index, row in enumerate(table.rows):
                written = str(row.get(key.column, "")).strip()
                if not written:
                    continue
                entity = canonical.get((key.kind, written))
                if entity is None:
                    # Not in the graph, so nothing can be merged with it. It gets its
                    # own row and the table names it: an unaligned label is a fact
                    # about the dictionary's coverage, not a thing to hide in a split.
                    unmatched.add(f"{table.department}: {written}")
                    entity_id, label = written, written
                else:
                    entity_id, label = entity.id, entity.label

                # The month comes from the row's own date, not from the batch label.
                # A row dated 11 March inside a November upload belongs in March, and
                # filing it under the label is how a misread date stays invisible
                # (#18, #79). A row with no readable date keeps the batch label and
                # is marked, rather than being invented a month for.
                month = grain.month_of(row.get(date_column)) if date_column else None
                row_key: RowKey = (month or table.period, entity_id)
                labels.setdefault(row_key, label)
                origins[row_key] += 1
                if row_key not in notes:
                    if month is None:
                        notes[row_key] = "batch label — this row carries no readable date"
                    elif month != table.period:
                        notes[row_key] = (
                            f"row date, which puts it in {month} rather than the "
                            f"{table.period} batch it arrived in"
                        )

                for column, value in row.items():
                    if column == key.column or value is None or value == "":
                        continue
                    cells[row_key][f"{table.department}.{column}"].append(value)

        if unjoinable:
            raise UnjoinableTables(unjoinable)

        rows: list[dict[str, Any]] = []
        undescribed: dict[str, list[str]] = {}
        for row_key in sorted(cells):
            month, entity_id = row_key
            folded, policies, missing = _fold_row(cells[row_key], dictionary)
            for measure in missing:
                undescribed.setdefault(measure, []).append(entity_id)
            row: dict[str, Any] = {
                "period": month,
                "entity_id": entity_id,
                "entity": labels[row_key],
                "source_rows": origins[row_key],
                **folded,
            }
            if row_key in notes:
                row["period_from"] = notes[row_key]
            if policies:
                row["rollups"] = policies
            rows.append(row)

        if undescribed:
            raise MissingRollup(undescribed)

        periods = sorted({str(r["period"]) for r in rows})
        return MasterTable(
            grain="month",
            periods=periods,
            rows=rows,
            unmatched_entities=sorted(unmatched),
        )

    def _approval_cards(self, findings: list[Finding]) -> list[ApprovalCard]:
        """One card per department that raised something needing a decision."""
        by_role: dict[str, list[Finding]] = defaultdict(list)
        for finding in findings:
            if finding.severity in {"warning", "critical"}:
                by_role[finding.role].append(finding)

        due = (datetime.now(UTC) + timedelta(days=7)).date()
        return [
            ApprovalCard(
                title=f"{role.title()}: {len(group)} item(s) need a decision",
                owner=group[0].role,
                due=due,
                findings=group,
                options=["Accept risk", "Act on recommendation", "Request more data"],
            )
            for role, group in by_role.items()
        ]


class UnjoinableTables(RuntimeError):
    """No declared join key, so the Master Table is refused rather than guessed.

    `CLAUDE.md`: an evidence-free conclusion is rejected, not downgraded. A table
    joined on an arbitrary column is exactly an evidence-free conclusion wearing the
    shape of a result.
    """

    def __init__(self, departments: list[str]) -> None:
        self.departments = departments
        super().__init__(
            "No column is declared as a joinable entity for: "
            + ", ".join(departments)
            + ". Add it to the OA field dictionary — the Master Table is not built "
            "from a guessed key."
        )


class MissingRollup(RuntimeError):
    """Several rows reached one cell and the dictionary states no policy for it.

    Summing a price and averaging a quantity are both arithmetic, and both wrong here
    or there, and the sheet cannot say which the business means. `FR 09` asks for the
    method per metric to be configurable and *displayed*; refusing to invent one is the
    same half of that requirement as showing it.
    """

    def __init__(self, measures: dict[str, list[str]]) -> None:
        self.measures = measures
        named = "; ".join(
            f"{measure} ({', '.join(sorted(set(entities))[:3])})"
            for measure, entities in sorted(measures.items())
        )
        super().__init__(
            "Several source rows landed in one Master Table cell for: "
            + named
            + ". Give each a rollups entry (sum / average / period_end) in the field "
            "dictionary — combining them any other way is a guess wearing the shape "
            "of a total."
        )


#: One Master Table row: the month it belongs to and the canonical entity it describes.
RowKey = tuple[str, str]


class EntityKey(NamedTuple):
    """The column a department's rows are joined on, and the entity kind it holds."""

    column: str
    kind: str


def _canonical_index(graph: EntityGraph) -> dict[tuple[str, str], Entity]:
    """Every spelling the resolver recognised, pointing at what it means.

    Scoped by kind deliberately: two departments could write the same string for a
    customer and for a material, and collapsing them would be its own mis-merge.
    """
    index: dict[tuple[str, str], Entity] = {}
    for entity in graph.entities:
        for spelling in [entity.label, *entity.aliases]:
            written = str(spelling).strip()
            if written:
                index.setdefault((str(entity.kind), written), entity)
    return index


def _fold_row(
    arrived: dict[str, list[Any]], dictionary: FieldDictionary
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    """Combine what reached one entity-month into one value per column.

    Returns the cells, the policy behind each cell that needed one, and the
    measurements whose policy the dictionary does not state.
    """
    folded: dict[str, Any] = {}
    policies: dict[str, str] = {}
    missing: list[str] = []

    for cell, seen in sorted(arrived.items()):
        department, _, column = cell.partition(".")
        measure = dictionary.measure_for(department, column)

        if measure is None:
            # Not a measurement — a supplier, a line, an account. Nothing combines
            # here, so agreement is checked rather than assumed, and a disagreement
            # stays visible instead of being settled by whichever row came first.
            distinct = _distinct(seen)
            folded[cell] = distinct[0] if len(distinct) == 1 else distinct
            if len(distinct) > 1:
                policies[cell] = "disagreed"
            continue

        if len(seen) == 1:
            folded[cell] = seen[0]
            continue

        policy = dictionary.rollups.get(measure)
        if policy is None:
            missing.append(measure)
            continue

        folded[cell] = _combine(policy, seen)
        policies[cell] = policy

    return folded, policies, missing


def _combine(policy: str, seen: list[Any]) -> Any:
    """Fold several values of one measurement by the stated policy."""
    if policy == "period_end":
        return seen[-1]

    numbers = [_number(value) for value in seen]
    if any(number is None for number in numbers):
        # Text in a numeric column. Listing what arrived is honest; adding up the
        # rows that happened to parse and calling that a total is the exact error
        # metrics.compute refuses for, one stage later.
        return _distinct(seen)

    total = sum(number for number in numbers if number is not None)
    return round(total / len(numbers), 4) if policy == "average" else round(total, 4)


def _distinct(values: list[Any]) -> list[Any]:
    """The values, in arrival order, with repeats removed."""
    seen: list[Any] = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return seen


def _number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "").strip())
        except ValueError:
            return None
    return None


def _dictionary_path():
    from pathlib import Path

    configured = Path(settings.field_dictionary_path)
    return configured if configured.is_absolute() else REPO_ROOT / configured


def _period_column(table: CleanTable, dictionary: FieldDictionary) -> str | None:
    """The date that files a row under a month: declared, or the only date the sheet has.

    Several date columns and no declaration is not resolved by taking the first one —
    the row keeps the batch label and says it carries no readable period.
    """
    declared = dictionary.period_columns.get(table.department)
    dates = [c.name for c in table.columns if c.dtype == "date"]
    if declared:
        return declared if declared in {c.name for c in table.columns} else None
    return dates[0] if len(dates) == 1 else None


#: Entity kinds that can serve as a join key, in the order we prefer them.
_JOIN_KINDS: tuple[str, ...] = ("project", "sku", "customer", "raw_material", "gl_account")
#: After the starter vocabulary, any kind the dictionary declares counts. A published
#: draft from the business's own dictionary produces kinds like 项目名称 or material —
#: PR #60 already moved validation from the vocabulary to the declaration, and
#: `kind_for` respects a non-empty dictionary exactly, so this opens the door to the
#: business's nouns without reopening name guessing.
_ANY_DECLARED = object()


def _primary_key_column(table: CleanTable, dictionary: FieldDictionary) -> EntityKey | None:
    """The column this department's rows are joined on, and its entity kind.

    Only a column the field dictionary declares as a joinable entity counts. The
    previous version guessed from five English column names and, failing that,
    returned the first column — so a sheet whose headers were in Chinese, or simply
    named differently, was joined on whatever happened to come first. Nothing threw,
    nothing was quarantined, nothing was logged: the Master Table came out looking
    ordinary and was wrong throughout, and every finding downstream inherited it.

    Returning None is the honest answer, and the caller refuses rather than inventing
    a join. The kind comes back with the column because merging a written label into
    its canonical entity only means something if you know what kind of thing it is:
    the same string can name a customer in one sheet and a material in another.
    """
    for kind in (*_JOIN_KINDS, _ANY_DECLARED):
        for column in table.columns:
            declared = dictionary.kind_for(table.department, column.name)
            if declared is not None and (kind is _ANY_DECLARED or declared == kind):
                return EntityKey(column.name, declared)
    return None
