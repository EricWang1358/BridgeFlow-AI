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
from typing import NamedTuple

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
    #: An alternative set of measurements that yields the same figure when the
    #: primary one is not declared. A spend, for instance, is summed from a line
    #: amount when the sheet states one and derived from price × quantity when it
    #: does not. The primary set wins when both exist: a figure the customer wrote
    #: down is the one an auditor signs.
    fallback_requires: list[str] = Field(default_factory=list)
    #: Which role's brief this metric belongs in.
    role: str
    #: sum | ratio | signed_sum | change_mom | spend
    op: str = "sum"
    #: For `signed_sum`: only rows whose account code the dictionary classes as this count.
    account_class: str = ""
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
        formula="money actually spent on purchases",
        requires=["purchase_amount"],
        #: Sheets state a line amount; many state only a price and a quantity.
        fallback_requires=["unit_price", "purchase_quantity"],
        role="procurement",
        op="spend",
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
        account_class="sales",
    ),
    MetricSpec(
        name="cost_of_sales",
        unit="currency",
        formula="sum of revenue lines whose account code marks them as cost",
        requires=["revenue_amount"],
        role="finance",
        op="signed_sum",
        account_class="cost_of_sales",
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
        formula="this period's quantity-weighted unit price against the previous "
        "period's",
        requires=["purchase_amount", "purchase_quantity"],
        fallback_requires=["unit_price", "purchase_quantity"],
        role="procurement",
        op="change_mom",
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
    return [m for m in CATALOGUE if _satisfies(m, dictionary.declared_measures)]


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

    if spec.op == "spend":
        spend = _spend(period, tables, entity, dictionary)
        return spend.model_copy(update={"metric": spec.name, "unit": spec.unit})

    if spec.op == "ratio":
        return _ratio(spec, period, tables, entity=entity, dictionary=dictionary)
    if spec.op == "margin":
        return _margin(spec, period, tables, entity=entity, dictionary=dictionary)
    if spec.op == "change_mom":
        return _change_mom(spec, period, tables, prior, entity=entity, dictionary=dictionary)

    total = 0.0
    sources: list[SourceRef] = []
    unreadable: list[str] = []

    classed = [t.department for t in tables if dictionary.account_classes.get(t.department)
               and any(dictionary.columns_measuring(t.department, m) for m in spec.requires)]
    if spec.name == "revenue" and classed:
        # The declared amount column carries both sales and cost lines here, so its plain
        # sum is a net movement. Calling that revenue is the misreading #92 is about.
        raise MetricRefused(
            f"{', '.join(classed)}: amount lines mix declared account classes, so their sum is a net, "
            "not revenue. Use sales and cost_of_sales."
        )

    for table in tables:
        markers: list[str] = []
        if spec.account_class and any(dictionary.columns_measuring(table.department, m) for m in spec.requires):
            markers = dictionary.account_classes.get(table.department, {}).get(spec.account_class, [])
            if not markers:
                raise MetricRefused(
                    f"{table.department}: the dictionary declares no account_classes.{spec.account_class}, "
                    f"so {spec.name} cannot be told apart from other lines. Nothing is guessed from account names."
                )
        # What this department's rows are *about*, as the dictionary declares it.
        # Both filters below read identity, and reading it off the whole row let the
        # figures themselves decide which figures to include.
        identity_columns = [
            c.name for c in table.columns
            if dictionary.kind_for(table.department, c.name) is not None
        ]
        for measure in spec.requires:
            declared = set(dictionary.columns_measuring(table.department, measure))
            for column in (c.name for c in table.columns if c.name in declared):
                for index, row in enumerate(table.rows):
                    if entity and entity.lower() not in _identity_text(row, identity_columns):
                        continue
                    if spec.account_class and not _account_matches(row, markers, identity_columns):
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


def _identity_text(row: dict, columns: list[str]) -> str:
    """What this row says about *what it is*, ignoring what it measures.

    Deciding anything by searching the stringified row lets every column vote: an
    amount, a date, a currency and a customer name all get a say in whether a line
    is a cost. Restricting the search to the columns the dictionary declares as
    entities is not a tightening for its own sake — it is the difference between
    reading the account code and reading whatever else happened to be on the line.
    """
    if not columns:
        return ""
    return " ".join(str(row.get(column, "")) for column in columns).lower()


def _account_matches(row: dict, markers: list[str], identity_columns: list[str]) -> bool:
    """Whether this row's account code carries one of the declared markers.

    Sales and cost lines live in the same column and are told apart by their account
    code. Summing them together is arithmetically fine and semantically wrong: it
    was how `revenue` came out as 11,700 on a month with 134,400 of sales.

    Matched against the declared entity columns only. A customer called
    "Cost Cutters Ltd" must not turn a sales line into a cost line, and before this
    it did — the marker was searched for anywhere in the row.
    """
    text = _identity_text(row, identity_columns)
    return any(marker in text for marker in markers)


#: The money a purchase line costs, and how many units it buys. A sheet may state
#: either directly, or only in pieces — which is why the two metrics below resolve
#: their lines together and then differ on what a missing piece means.
SPEND = "purchase_amount"
QUANTITY = "purchase_quantity"


def _satisfies(spec: MetricSpec, declared: set[str]) -> bool:
    """Whether the dictionary can supply what this metric needs, by either route."""
    return set(spec.requires) <= declared or (
        bool(spec.fallback_requires) and set(spec.fallback_requires) <= declared
    )


def _ref(table: CleanTable, row: int, column: str) -> SourceRef:
    """One cell that fed a figure — the unit of evidence the PRD asks for."""
    return SourceRef(
        department=table.department, period=table.period, row=row, column=column
    )


def _exactly_one(department: str, measure: str, dictionary: FieldDictionary) -> str | None:
    """The single column a department declares for one measurement.

    Two matches is a real question about which column the dictionary means, so it is
    refused rather than settled by whichever appears first in the file.
    """
    matches = dictionary.columns_measuring(department, measure)
    if not matches:
        return None
    if len(matches) > 1:
        raise MetricRefused(
            f"{measure} cannot be resolved for {department}: it matches "
            + f"{len(matches)} columns ({', '.join(sorted(matches))}). "
            "The field dictionary needs to name exactly one."
        )
    return matches[0]


def _product(values: dict[str, float | None], columns: list[str]) -> float:
    """The cells multiplied together. Callers have already ruled out the blanks."""
    total = 1.0
    for column in columns:
        total *= values[column]  # type: ignore[operator]
    return total


class PurchaseLine(NamedTuple):
    """One purchase line: what it cost, how many units, and the cells saying so.

    `quantity` is None when the sheet carries no quantity column at all — an amount
    on its own is still an amount, and refusing such a sheet would be its own kind
    of capability regression.
    """

    amount: float
    quantity: float | None
    sources: list[SourceRef]


class PurchaseLines(NamedTuple):
    """Every resolvable line, plus three separate accounts of what is missing.

    The lists stay distinct on purpose: what a missing piece costs a caller depends
    on the caller. A sum and a ratio do not survive the same omission, and collapsing
    the two into one "holes" list is how a ratio ends up refusing work it could have
    done, or a sum quietly accepting work it must not.
    """

    lines: list[PurchaseLine]
    #: A quantity with no amount. Fatal for a sum — the month cost at least what the
    #: complete lines say, and possibly more.
    missing_amount: list[str]
    #: An amount with no quantity. Harmless for a sum, unusable in a denominator.
    missing_quantity: list[str]
    #: Declared values that would not parse as numbers.
    unreadable: list[str]
    #: How the amounts were obtained, phrased for a `formula` field.
    basis: str


def _purchase_lines(
    tables: list[CleanTable],
    entity: str | None,
    dictionary: FieldDictionary,
) -> PurchaseLines:
    """Resolve every purchase line into (amount, quantity, the cells behind them).

    Returns the lines plus three separate lists of what is missing, because the
    metrics reading this differ in what they can survive — see `_spend` and
    `_unit_price` — plus a phrase naming the route the amounts came by.

    Two routes, and they are not interchangeable:

    * **A stated line amount.** The sheet already says what the line cost, and this
      wins wherever it exists — a figure the customer wrote down is the one an
      auditor signs, and recomputing it from a price and a quantity would replace
      their arithmetic with ours.
    * **A derived amount**: price × quantity, per line. Available only when the
      dictionary declares that product (`FieldDictionary.derived`), because which
      two columns multiply into an amount is a fact about the customer's schema and
      that is still being negotiated (`CLAUDE.md`, eighth hard rule). Nothing here
      infers it from a column name.

    Departments resolve separately, so an estate where one source states amounts and
    another does not is handled rather than averaged away.

    A line carrying a quantity with no amount comes back as a hole. What the caller
    does with a hole differs by metric, and that difference is why these two metrics
    share a resolver instead of each reading columns its own way.
    """
    factors = dictionary.derived.get(SPEND) or []
    routes: dict[str, dict[str, object]] = {}

    for department in sorted({table.department for table in tables}):
        # A quantity column is not required to know what a line cost — a ledger of
        # amounts with no units is a real shape (finance exports it), and refusing
        # one would be its own kind of capability regression.
        quantity = _exactly_one(department, QUANTITY, dictionary)
        stated = _exactly_one(department, SPEND, dictionary)
        if stated is not None:
            routes[department] = {"amount": stated, "factors": {}, "quantity": quantity}
            continue
        derived: dict[str, str] = {}
        for factor in factors:
            column = _exactly_one(department, factor, dictionary)
            if column is None:
                derived = {}
                break
            derived[factor] = column
        if derived:
            routes[department] = {"amount": None, "factors": derived, "quantity": quantity}

    if not routes:
        raise MetricRefused(
            f"nothing declares a {SPEND}, or the factors to derive one"
            + (f" ({' × '.join(factors)})" if factors else "")
            + f", for any of {', '.join(sorted({t.department for t in tables}))}. Refusing "
            "rather than reading a price column as though it were an amount — which is "
            "how a month of 117,250 was reported as 13,540."
        )

    lines: list[PurchaseLine] = []
    missing_amount: list[str] = []
    missing_quantity: list[str] = []
    unreadable: list[str] = []
    seen: set[str] = set()

    for table in tables:
        route = routes.get(table.department)
        if route is None:
            continue
        amount_column: str | None = route["amount"]  # type: ignore[assignment]
        quantity_column: str | None = route["quantity"]  # type: ignore[assignment]
        factor_columns: list[str] = list(route["factors"].values())  # type: ignore[union-attr]
        # Every cell that has to carry a value for this line to have an amount at all.
        needed = sorted(
            set(factor_columns)
            | ({quantity_column} if quantity_column else set())
            | ({amount_column} if amount_column else set())
        )

        for index, row in enumerate(table.rows):
            if entity and entity.lower() not in str(row).lower():
                continue

            values: dict[str, float | None] = {}
            for column in needed:
                raw = row.get(column)
                if raw is None or raw == "":
                    values[column] = None
                    continue
                number = _as_number(raw)
                if number is None:
                    unreadable.append(f"{table.department} row {index} {column}={raw!r}")
                values[column] = number

            if amount_column:
                amount, feeding = values[amount_column], [amount_column]
            else:
                feeding = factor_columns
                amount = (
                    None
                    if any(values[column] is None for column in feeding)
                    else _product(values, feeding)
                )

            quantity = values[quantity_column] if quantity_column else None
            if amount is None:
                # A line stating units and not their cost is a hole in a sum; a line
                # stating nothing at all is simply absent, and absent is not a hole.
                if quantity is not None:
                    missing_amount.append(
                        f"{table.department} row {index} states no amount for its {QUANTITY}"
                    )
                continue
            if quantity_column and quantity is None:
                missing_quantity.append(
                    f"{table.department} row {index} states no {quantity_column}"
                )

            refs = [
                _ref(table, index, column) for column in feeding if values[column] is not None
            ]
            if (
                quantity_column
                and quantity_column not in feeding
                and values[quantity_column] is not None
            ):
                refs.append(_ref(table, index, quantity_column))
            lines.append(PurchaseLine(amount, quantity, refs))
            seen.add("stated" if amount_column else "derived")

    basis = {
        "stated": "the line amounts the sheet states",
        "derived": "unit price × quantity per line",
    }.get(
        next(iter(seen)) if len(seen) == 1 else "",
        "stated line amounts and derived price × quantity",
    )

    return PurchaseLines(lines, missing_amount, missing_quantity, unreadable, basis)



def _spend(
    period: str,
    tables: list[CleanTable],
    entity: str | None,
    dictionary: FieldDictionary,
) -> MetricValue:
    """Money actually spent on purchases.

    A hole refuses the whole metric here. A sum that quietly omits a purchase line
    reports a month as having spent less than it did while citing nothing but real
    cells — which is exactly how a wrong figure survives review. `compute` already
    refuses rather than totalling the rows that happened to parse; this is the same
    rule applied to a value that was never entered, which is the case a partly-filled
    purchase ledger actually hits.
    """
    resolved = _purchase_lines(tables, entity, dictionary)

    if resolved.unreadable:
        raise MetricRefused(
            f"material_spend cannot be computed: {len(resolved.unreadable)} declared "
            "value(s) could not be read as numbers — "
            + "; ".join(resolved.unreadable[:5])
            + ". Refusing rather than multiplying the lines that happened to parse."
        )
    if resolved.missing_amount:
        raise MetricRefused(
            f"material_spend is refused: {len(resolved.missing_amount)} purchase line(s) "
            "state a quantity with no amount — "
            + "; ".join(resolved.missing_amount[:5])
            + ". Their spend is unknown, not zero, and summing the complete lines alone "
            "would report fewer purchases than were made. Fill the cell or declare the "
            "line out of scope; either is honest, omitting it is not."
        )
    if not resolved.lines:
        raise MetricRefused(
            f"material_spend found no purchase line stating an amount for {period}. "
            "Refusing rather than returning a figure with no source rows."
        )

    sources = [ref for line in resolved.lines for ref in line.sources]
    return MetricValue(
        metric="material_spend",
        period=period,
        value=round(sum(line.amount for line in resolved.lines), 4),
        unit="currency",
        formula=f"sum of {resolved.basis}",
        sources=sources[:EVIDENCE_SAMPLE],
        source_count=len(sources),
        truncated=len(sources) > EVIDENCE_SAMPLE,
    )



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

    now = _unit_price(period, tables, entity, dictionary)
    before = _unit_price(period, prior, entity, dictionary)

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
    period: str,
    tables: list[CleanTable],
    entity: str | None,
    dictionary: FieldDictionary,
) -> MetricValue:
    """What one unit cost, over the lines that can say so.

    Two properties this has to get right, and the version it replaces got neither:

    * **Quantity-weighted, not the mean of the stated prices.** Lines priced 4,850,
      5,200 and 3,490 bought very different numbers of units, and the unweighted mean
      of three invoice headers is not a cost per unit.
    * **Numerator and denominator from the same lines.** Counting the units of a line
      whose amount is unknown divides a partial spend by a full quantity and reports
      a price lower than anything that was actually paid. The hole must leave both
      sides together.

    That is why a hole behaves differently here than in `_spend`: a sum over
    incomplete lines understates money and is refused outright, while a ratio over
    the lines stating both figures is a real answer — provided the formula says how
    many lines it covers, so nobody mistakes it for the whole month.
    """
    resolved = _purchase_lines(tables, entity, dictionary)
    usable = [line for line in resolved.lines if line.quantity is not None]

    if not usable:
        raise MetricRefused(
            f"no declared {QUANTITY} for {period} alongside a known amount, so a unit "
            "price has no meaning."
        )

    amount = sum(line.amount for line in usable)
    units = 0.0
    for line in usable:
        units += line.quantity if line.quantity is not None else 0.0
    if units == 0:
        raise MetricRefused(
            f"every declared {QUANTITY} for {period} is zero, so a unit price has no "
            "meaning."
        )

    left_out = len(resolved.missing_amount) + len(resolved.missing_quantity)
    note = f" ({left_out} line(s) left out for stating half a pair)" if left_out else ""
    sources = [ref for line in usable for ref in line.sources]
    return MetricValue(
        metric="unit_price",
        period=period,
        value=amount / units,
        unit="currency",
        formula=(
            f"quantity-weighted price over {len(usable)} line(s), from {resolved.basis}"
            + note
        ),
        sources=sources[:EVIDENCE_SAMPLE],
        source_count=len(sources),
        truncated=len(sources) > EVIDENCE_SAMPLE,
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
