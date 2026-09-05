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
    """One metric, defined by the measurements it needs rather than by column names.

    `op` is what turns a pile of declared columns into a figure. Sums were enough to
    prove the shape; the four sentences the demo actually says — margin turned
    negative, aluminium is up 18%, line 2 is at 94%, Acme is tier C — need division,
    month-on-month comparison and classification as well (#65).
    """

    name: str
    unit: str
    formula: str
    #: Declared measurement kinds, resolved to columns through the field dictionary.
    requires: list[str]
    #: Which role's brief this metric belongs in.
    role: str
    #: sum | ratio | signed_sum | change_mom
    op: str = "sum"
    #: For `signed_sum`: only rows whose account code matches this prefix count.
    account_prefix: str = ""
    #: For `change_mom`: the period to compare against, as an offset in months.
    compare_months_back: int = 1


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
    # The four the demo actually says out loud. Each needs an operation a sum
    # cannot express, which is why they were missing (#65).
    MetricSpec(
        name="capacity_utilisation",
        unit="ratio",
        formula="declared output quantity ÷ declared capacity hours",
        requires=["output_quantity", "capacity_hours"],
        role="production",
        op="ratio",
    ),
    MetricSpec(
        name="sales",
        unit="currency",
        formula="sum of revenue lines whose account code marks them as sales",
        requires=["revenue_amount"],
        role="finance",
        op="signed_sum",
        account_prefix="sales",
    ),
    MetricSpec(
        name="cost_of_sales",
        unit="currency",
        formula="sum of revenue lines whose account code marks them as cost",
        requires=["revenue_amount"],
        role="finance",
        op="signed_sum",
        account_prefix="cost",
    ),
    MetricSpec(
        name="gross_margin",
        unit="ratio",
        formula="(sales + cost of sales) ÷ sales, where cost lines are already negative",
        requires=["revenue_amount"],
        role="finance",
        op="margin",
    ),
    MetricSpec(
        name="material_price_change",
        unit="ratio",
        formula="this period's average declared unit price against the previous period's",
        requires=["purchase_amount", "purchase_quantity"],
        role="procurement",
        op="change_mom",
    ),
)


#: Which account-code fragments mark a line as revenue or as cost. Declared here
#: rather than parsed out of the code string, because chart-of-accounts conventions
#: differ per customer and the real one is still being negotiated. When the OA export
#: lands this moves into the dictionary alongside everything else.
ACCOUNT_MARKERS = {
    "sales": ("sales", "rev", "销售", "收入"),
    "cost": ("cogs", "cos", "cost", "成本"),
}


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
    prior: list[CleanTable] | None = None,
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

    if spec.op == "ratio":
        return _ratio(spec, period, tables, entity=entity, dictionary=dictionary)
    if spec.op == "margin":
        return _margin(spec, period, tables, entity=entity, dictionary=dictionary)
    if spec.op == "change_mom":
        return _change_mom(spec, period, tables, prior, entity=entity, dictionary=dictionary)

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
                    if spec.account_prefix and not _account_matches(row, spec.account_prefix):
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


def _account_matches(row: dict, kind: str) -> bool:
    """Whether this row's account code marks it as `kind`.

    Sales and cost lines live in the same column and are told apart by their account
    code. Summing them together is arithmetically fine and semantically wrong: it
    was how `revenue` came out as 11,700 on a month with 134,400 of sales.
    """
    markers = ACCOUNT_MARKERS.get(kind, ())
    text = " ".join(str(v) for v in row.values()).lower()
    return any(marker in text for marker in markers)


def _ratio(
    spec: MetricSpec,
    period: str,
    tables: list[CleanTable],
    *,
    entity: str | None,
    dictionary: FieldDictionary,
) -> MetricValue:
    """One declared measurement divided by another.

    Refuses on a zero denominator rather than returning infinity or nought — a
    capacity of zero means the figure has no meaning, not that utilisation is zero.
    """
    numerator, denominator = spec.requires
    top = _sum_measure(numerator, period, tables, entity, dictionary)
    bottom = _sum_measure(denominator, period, tables, entity, dictionary)

    if bottom.value == 0:
        raise MetricRefused(
            f"{spec.name} divides by {denominator}, which totals zero for {period}. "
            "A zero denominator means the ratio has no meaning, not that it is zero."
        )

    sources = (top.sources + bottom.sources)[:EVIDENCE_SAMPLE]
    return MetricValue(
        metric=spec.name,
        period=period,
        value=round(top.value / bottom.value, 4),
        unit=spec.unit,
        formula=spec.formula,
        sources=sources,
        source_count=top.source_count + bottom.source_count,
        truncated=(top.source_count + bottom.source_count) > len(sources),
    )


def _margin(
    spec: MetricSpec,
    period: str,
    tables: list[CleanTable],
    *,
    entity: str | None,
    dictionary: FieldDictionary,
) -> MetricValue:
    """Gross margin, with sales and cost told apart by account code.

    Cost lines are already negative in the source data, so the sum of the two is the
    margin in currency and dividing by sales gives the ratio.
    """
    sales = compute("sales", period, tables, entity=entity, dictionary=dictionary)
    cost = compute("cost_of_sales", period, tables, entity=entity, dictionary=dictionary)

    if sales.value == 0:
        raise MetricRefused(
            f"{spec.name} divides by sales, which totals zero for {period}."
        )

    sources = (sales.sources + cost.sources)[:EVIDENCE_SAMPLE]
    return MetricValue(
        metric=spec.name,
        period=period,
        value=round((sales.value + cost.value) / sales.value, 4),
        unit=spec.unit,
        formula=spec.formula,
        sources=sources,
        source_count=sales.source_count + cost.source_count,
        truncated=(sales.source_count + cost.source_count) > len(sources),
    )


def _change_mom(
    spec: MetricSpec,
    period: str,
    tables: list[CleanTable],
    prior: list[CleanTable] | None,
    *,
    entity: str | None,
    dictionary: FieldDictionary,
) -> MetricValue:
    """How much a unit price moved against the previous period.

    Refuses without the previous period rather than reporting no change. "We have no
    comparison" and "nothing changed" are different answers, and a warning that says
    prices are flat when nobody looked is worse than one that says it cannot tell.
    """
    if not prior:
        raise MetricRefused(
            f"{spec.name} compares {period} against the previous period, and the "
            "previous period was not supplied. Refusing rather than reporting no change."
        )

    amount, quantity = spec.requires
    now = _unit_price(amount, quantity, period, tables, entity, dictionary)
    before = _unit_price(amount, quantity, period, prior, entity, dictionary)

    if before.value == 0:
        raise MetricRefused(f"{spec.name} divides by the previous period's unit price, which is zero.")

    sources = (now.sources + before.sources)[:EVIDENCE_SAMPLE]
    return MetricValue(
        metric=spec.name,
        period=period,
        value=round((now.value - before.value) / before.value, 4),
        unit=spec.unit,
        formula=spec.formula,
        sources=sources,
        source_count=now.source_count + before.source_count,
        truncated=(now.source_count + before.source_count) > len(sources),
    )


def _unit_price(
    amount: str,
    quantity: str,
    period: str,
    tables: list[CleanTable],
    entity: str | None,
    dictionary: FieldDictionary,
) -> MetricValue:
    total = _sum_measure(amount, period, tables, entity, dictionary)
    units = _sum_measure(quantity, period, tables, entity, dictionary)
    if units.value == 0:
        raise MetricRefused(f"no declared {quantity} for {period}, so a unit price has no meaning")
    return MetricValue(
        metric="unit_price",
        period=period,
        value=total.value / units.value,
        unit="currency",
        formula=f"declared {amount} ÷ declared {quantity}",
        sources=total.sources,
        source_count=total.source_count + units.source_count,
    )


def _sum_measure(
    measure: str,
    period: str,
    tables: list[CleanTable],
    entity: str | None,
    dictionary: FieldDictionary,
) -> MetricValue:
    """Sum one declared measurement, reusing the refusal rules of `compute`."""
    spec = MetricSpec(
        name=measure, unit="", formula=f"sum of declared {measure}", requires=[measure], role=""
    )
    saved = CATALOGUE
    try:
        globals()["CATALOGUE"] = saved + (spec,)
        return compute(measure, period, tables, entity=entity, dictionary=dictionary)
    finally:
        globals()["CATALOGUE"] = saved


def _as_number(value: object) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "").strip())
        except ValueError:
            return None
    return None
