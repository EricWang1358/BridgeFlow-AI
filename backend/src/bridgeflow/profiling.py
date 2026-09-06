"""What the columns look like, so a person is never asked to guess alone.

A batch whose dictionary declares no joinable column refuses to build a Master
Table, which is correct — a table joined on an arbitrary column is an evidence-free
conclusion wearing the shape of a result. But refusing and stopping there hands the
problem straight back to the operator, who is looking at four spreadsheets from four
departments and has no more idea than the machine did. That is the moment the agent
is supposed to earn its place.

This module gives the model enough to *propose* a dictionary without ever seeing the
data, which is the whole difficulty. Two hard constraints meet here and neither
bends:

- **No raw rows in context** (`CLAUDE.md`, seventh). So nothing here returns a cell.
  Column names, counts and ratios only. Whether two departments are talking about the
  same things is answered by comparing *hashes* of their values, so the evidence for
  a join survives without the values travelling.
- **No field names in code** (`CLAUDE.md`, eighth). So nothing here knows that `sku`
  means a product or that `customer` means a buyer. Every signal is structural —
  how unique a column is, how much of it is filled, whether it looks like an
  identifier, how far its values overlap another department's. The model reads those
  signals and proposes; the dictionary stays the customer's to declare.

The output is deliberately small: a batch of 200,000 rows profiles to the same
handful of numbers per column as a batch of four.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from pydantic import BaseModel, Field

from bridgeflow.schemas import CleanTable

#: Most columns profiled per department, and most overlap pairs reported overall.
#: A wide sheet must not turn into an unbounded prompt.
MAX_COLUMNS = 40
MAX_OVERLAPS = 40

#: Below this, an overlap is coincidence rather than evidence of a shared entity.
MIN_OVERLAP = 0.30

#: A column whose values barely repeat is identifier-shaped; one that repeats a lot
#: is a category. Neither is decisive, which is why both are reported rather than
#: turned into a verdict here.
IDENTIFIER_DISTINCT_RATIO = 0.60


def _norm(value: Any) -> str | None:
    """The comparable form of a cell: case-folded, trimmed, punctuation-flattened.

    `SKU-A1`, `sku a1` and `SKU_A1` are the same product written by three
    departments, and an overlap statistic that misses that is worse than none.
    """
    if value is None:
        return None
    text = re.sub(r"[\s_\-./]+", "", str(value).strip().casefold())
    return text or None


def _digest(value: str) -> str:
    """A value's identity without the value. Truncated: this compares, never reveals."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


class ColumnProfile(BaseModel):
    """Structural facts about one column. No cell content, by construction."""

    department: str
    column: str
    #: The header as the department actually wrote it, which is what a person
    #: recognises when they go back to the file.
    original: str = ""
    dtype: str = "string"
    rows: int = 0
    filled: int = 0
    distinct: int = 0
    #: Distinct values over filled values. Near 1.0 reads as an identifier.
    distinct_ratio: float = 0.0
    #: Filled values over rows. A mostly-empty column is a poor join key whatever
    #: else it looks like.
    fill_ratio: float = 0.0
    #: Structural, not semantic: does the text carry the shape identifiers usually
    #: have (letters and digits together, or a separator inside a short token)?
    identifier_shaped: bool = False
    average_length: float = 0.0


class ColumnOverlap(BaseModel):
    """Two columns in different departments that appear to name the same things."""

    left: str
    right: str
    #: Both sides' declared types. Two numeric columns matching is often arithmetic
    #: coincidence rather than a shared entity, and the model should discount it —
    #: which it can only do if it is told.
    left_dtype: str = "string"
    right_dtype: str = "string"
    #: Distinct values present in both, by hash.
    shared: int
    #: Of this column's distinct values, the fraction the other side also has.
    left_coverage: float
    right_coverage: float


class BatchProfile(BaseModel):
    """Everything the model gets to reason about, and nothing it should not."""

    batch_id: str
    period: str
    columns: list[ColumnProfile] = Field(default_factory=list)
    overlaps: list[ColumnOverlap] = Field(default_factory=list)
    #: Departments with no column the dictionary declares as a joinable entity —
    #: the ones actually blocking the Master Table.
    undeclared: list[str] = Field(default_factory=list)
    #: Departments the dictionary already covers, so a proposal does not re-litigate
    #: a decision somebody already made.
    declared: dict[str, list[str]] = Field(default_factory=dict)
    truncated: bool = False


def _identifier_shaped(samples: list[str]) -> bool:
    if not samples:
        return False
    hits = sum(
        1 for text in samples
        if len(text) <= 40 and re.search(r"[a-z]", text) and re.search(r"\d", text)
    )
    return hits / len(samples) >= 0.6


def profile_table(table: CleanTable) -> tuple[list[ColumnProfile], dict[str, set[str]]]:
    """One department's columns, plus the hashed value sets used for overlap."""
    dtypes = {spec.name: spec.dtype for spec in table.columns}
    names = list(dict.fromkeys(key for row in table.rows for key in row))[:MAX_COLUMNS]
    profiles: list[ColumnProfile] = []
    digests: dict[str, set[str]] = {}

    for name in names:
        values = [_norm(row.get(name)) for row in table.rows]
        filled = [v for v in values if v is not None]
        seen = set(filled)
        digests[name] = {_digest(v) for v in seen}
        profiles.append(ColumnProfile(
            department=table.department,
            column=name,
            original=table.original_columns.get(name, ""),
            dtype=dtypes.get(name, "string"),
            rows=len(table.rows),
            filled=len(filled),
            distinct=len(seen),
            distinct_ratio=round(len(seen) / len(filled), 3) if filled else 0.0,
            fill_ratio=round(len(filled) / len(table.rows), 3) if table.rows else 0.0,
            identifier_shaped=_identifier_shaped(sorted(seen)[:50]),
            average_length=round(sum(len(v) for v in filled) / len(filled), 1) if filled else 0.0,
        ))
    return profiles, digests


def profile(
    batch_id: str,
    period: str,
    tables: list[CleanTable],
    declared: dict[str, list[str]] | None = None,
) -> BatchProfile:
    """Profile a whole batch and rank the cross-department overlaps.

    The overlap is the load-bearing signal: two departments declaring the same
    entity will share most of each other's values, and no amount of column naming
    proves that. It is computed over hashes, so the evidence exists without the
    values leaving the process.
    """
    declared = declared or {}
    columns: list[ColumnProfile] = []
    digests: dict[str, dict[str, set[str]]] = {}
    types: dict[tuple[str, str], str] = {}
    truncated = False

    for table in tables:
        profiles, table_digests = profile_table(table)
        if len({key for row in table.rows for key in row}) > MAX_COLUMNS:
            truncated = True
        columns.extend(profiles)
        for spec in profiles:
            types[(spec.department, spec.column)] = spec.dtype
        digests[table.department] = table_digests

    overlaps: list[ColumnOverlap] = []
    departments = sorted(digests)
    for index, left_dept in enumerate(departments):
        for right_dept in departments[index + 1:]:
            for left_name, left_values in digests[left_dept].items():
                for right_name, right_values in digests[right_dept].items():
                    if not left_values or not right_values:
                        continue
                    shared = len(left_values & right_values)
                    if not shared:
                        continue
                    left_coverage = shared / len(left_values)
                    right_coverage = shared / len(right_values)
                    if max(left_coverage, right_coverage) < MIN_OVERLAP:
                        continue
                    overlaps.append(ColumnOverlap(
                        left=f"{left_dept}.{left_name}", right=f"{right_dept}.{right_name}",
                        left_dtype=types.get((left_dept, left_name), "string"),
                        right_dtype=types.get((right_dept, right_name), "string"),
                        shared=shared,
                        left_coverage=round(left_coverage, 3),
                        right_coverage=round(right_coverage, 3),
                    ))

    # Strongest evidence first: an operator reads the top of this list, not all of it.
    overlaps.sort(key=lambda o: min(o.left_coverage, o.right_coverage), reverse=True)
    if len(overlaps) > MAX_OVERLAPS:
        overlaps = overlaps[:MAX_OVERLAPS]
        truncated = True

    return BatchProfile(
        batch_id=batch_id, period=period, columns=columns, overlaps=overlaps,
        # A department is blocked when no column it ACTUALLY HAS is declared. Testing
        # only whether the dictionary mentions the department gets this exactly wrong:
        # the default dictionary names `gl_account` and `customer` for finance, the
        # sheet carries neither, and the batch is unjoinable while the department
        # looks covered. That is the case this whole path exists for.
        undeclared=sorted(
            t.department for t in tables
            if not (set(declared.get(t.department, [])) & {key for row in t.rows for key in row})
        ),
        declared={k: sorted(v) for k, v in declared.items() if v},
        truncated=truncated,
    )
