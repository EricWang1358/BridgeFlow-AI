"""Rules compute; the model explains.

The evaluator used to serialise every cleaned row into the prompt and ask the model
to work the figures out — 5.3 KB for an eighteen-row sample, against a PRD that sizes
one batch at 200,000 rows. Two things were wrong with that. It does not scale past a
toy dataset, and a number the model arrived at by reading rows cannot be traced,
cannot be reproduced, and cannot be signed off (`docs/13`, and #58).

So arithmetic lives here, in rules, and the model receives the results with the cells
they came from. Which columns hold which measurement is declared in the field
dictionary rather than named in code: the customer's schema is still being negotiated
(`CLAUDE.md`, eighth hard constraint).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from bridgeflow.agents.semantic_resolver import FieldDictionary, load_field_dictionary
from bridgeflow.config import REPO_ROOT, settings
from bridgeflow.schemas import CleanTable, SourceRef

#: How many contributing cells a result may name. See #58 — a citation per row would
#: put the table back into the context the tools exist to keep it out of.
EVIDENCE_SAMPLE = 5


class MetricSpec(BaseModel):
    """One metric, defined by the measurements it needs rather than by column names."""

    name: str
    unit: str
    formula: str
    #: Declared measurement kinds, resolved to columns through the field dictionary.
    requires: list[str]
    #: Which role's brief this metric belongs in.
    role: str


class MetricValue(BaseModel):
    metric: str
    period: str
    value: float
    unit: str
    formula: str
    sources: list[SourceRef] = Field(default_factory=list)
    source_count: int = 0
    truncated: bool = False


class MetricRefused(Exception):
    """A metric that cannot be computed honestly is refused, never estimated."""


CATALOGUE: tuple[MetricSpec, ...] = (
    MetricSpec(
        name="total_output",
        unit="units",
        formula="sum of declared output quantity",
        requires=["output_quantity"],
        role="production",
    ),
    MetricSpec(
        name="capacity_hours",
        unit="hours",
        formula="sum of declared capacity hours",
        requires=["capacity_hours"],
        role="production",
    ),
    MetricSpec(
        name="material_spend",
        unit="currency",
        formula="sum of declared purchase amounts",
        requires=["purchase_amount"],
        role="procurement",
    ),
    MetricSpec(
        name="revenue",
        unit="currency",
        formula="sum of declared revenue amounts",
        requires=["revenue_amount"],
        role="finance",
    ),
    MetricSpec(
        name="receivable_days",
        unit="days",
        formula="sum of declared receivable days",
        requires=["receivable_days"],
        role="finance",
    ),
)


def dictionary_path() -> Path:
    configured = Path(settings.field_dictionary_path)
    return configured if configured.is_absolute() else REPO_ROOT / configured


def available(dictionary: FieldDictionary | None = None) -> list[MetricSpec]:
    """Metrics that can actually be computed with what the dictionary declares.

    Offering a metric whose columns are undeclared would invite a call that can only
    be refused, so the catalogue is filtered rather than advertised in full.
    """
    dictionary = dictionary or load_field_dictionary(dictionary_path())
    if dictionary.is_empty:
        return []
    declared = {measure for (_dept, _col), measure in dictionary.measures.items()}
    return [m for m in CATALOGUE if set(m.requires) <= declared]


def compute(
    name: str,
    period: str,
    tables: list[CleanTable],
    *,
    entity: str | None = None,
    dictionary: FieldDictionary | None = None,
) -> MetricValue:
    """Compute one metric, or refuse.

    Refuses in three cases, all of which would otherwise produce a plausible number
    with nothing behind it: an unknown metric, a dictionary that declares no column
    for it, and a declared column holding a value that cannot be read as a number —
    that last one because totalling the rows that happen to parse and presenting the
    result as the total is exactly the silent error this design exists to prevent.
    """
    spec = next((m for m in CATALOGUE if m.name == name), None)
    if spec is None:
        raise MetricRefused(
            f"No metric named {name!r}. Call list_metrics — the set is configured, not "
            "fixed in code."
        )

    dictionary = dictionary or load_field_dictionary(dictionary_path())
    if dictionary.is_empty:
        raise MetricRefused(
            "The OA field dictionary is not configured, so no column can be identified "
            "by meaning. Nothing is computed from column spelling."
        )

    total = 0.0
    sources: list[SourceRef] = []
    unreadable: list[str] = []

    for table in tables:
        for measure in spec.requires:
            declared = set(dictionary.columns_measuring(table.department, measure))
            for column in (c.name for c in table.columns if c.name in declared):
                for index, row in enumerate(table.rows):
                    if entity and entity.lower() not in str(row).lower():
                        continue
                    raw = row.get(column)
                    if raw is None or raw == "":
                        continue  # an absent measurement is absent, not zero
                    number = _as_number(raw)
                    if number is None:
                        unreadable.append(f"{table.department} row {index} {column}={raw!r}")
                        continue
                    total += number
                    sources.append(
                        SourceRef(
                            department=table.department,
                            period=table.period,
                            row=index,
                            column=column,
                        )
                    )

    if unreadable:
        raise MetricRefused(
            f"{name} cannot be computed: {len(unreadable)} declared value(s) could not "
            f"be read as numbers — " + "; ".join(unreadable[:5]) + ". Refusing rather "
            "than totalling the rows that happened to parse."
        )
    if not sources:
        raise MetricRefused(
            f"{name} needs {', '.join(spec.requires)}, and the field dictionary declares "
            f"no such column for {period}. Refusing rather than returning a figure with "
            "no source rows."
        )

    return MetricValue(
        metric=spec.name,
        period=period,
        value=round(total, 4),
        unit=spec.unit,
        formula=spec.formula,
        sources=sources[:EVIDENCE_SAMPLE],
        source_count=len(sources),
        truncated=len(sources) > EVIDENCE_SAMPLE,
    )


def for_role(
    role: str, period: str, tables: list[CleanTable], dictionary: FieldDictionary | None = None
) -> tuple[list[MetricValue], list[str]]:
    """Everything one role can be told, plus what had to be refused and why.

    The refusals go to the model too. A role that is not told a metric is missing will
    reason as though it does not matter.
    """
    dictionary = dictionary or load_field_dictionary(dictionary_path())
    values: list[MetricValue] = []
    refusals: list[str] = []
    for spec in CATALOGUE:
        if spec.role != role:
            continue
        try:
            values.append(compute(spec.name, period, tables, dictionary=dictionary))
        except MetricRefused as refused:
            refusals.append(str(refused))
    return values, refusals


def _as_number(value: object) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "").strip())
        except ValueError:
            return None
    return None
