"""Uploaded columns matched onto columns a person already declared.

The dictionary is written by people, in advance (`CLAUDE.md`, 「字典由人预设，模型只做匹配」).
A department that exports its sheet with a header the dictionary does not know is not
a reason to edit the dictionary; it is a question with a closed answer set: *which of
the columns this department is declared to have is this one?* The model proposes, a
person decides through the approval gate, and the decision is remembered so next
month's import does not ask again.

Three properties keep this a match and never a creation:

- **The candidate set is closed.** A target must be a column the frozen dictionary
  declares for the same department and that the upload does not already carry. The
  host checks this when a decision is written, not only the prompt.
- **The dictionary is never touched.** A decision renames an uploaded column at import
  time. The original header stays in `original_columns`, so every source reference
  still points at what the department actually wrote.
- **A decision is about specific evidence.** It records the column's structural
  fingerprint; when a later upload's column has a different shape, the decision is
  not applied and the question is asked again.

Batches already frozen are never recomputed. A decision affects imports after it.

No cell value appears in anything this module returns, and no field name appears in
its code: every name comes from the dictionary snapshot or the upload.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from bridgeflow import profiling
from bridgeflow.config import REPO_ROOT, settings
from bridgeflow.schemas import CleanTable
from bridgeflow.store import _write

MAX_QUESTIONS = 40

#: What each declaration role expects a column's cleaned type to be. Structural
#: vocabulary of the dictionary format, not of any customer's schema.
_EXPECTED_DTYPE = {"entity": "string", "measure": "number", "period": "date", "currency": "string"}


class ColumnMatch(BaseModel):
    """One decision: this uploaded column is (or is not) that declared column."""

    department: str
    column: str
    target: str
    accepted: bool
    #: The column's structural fingerprint when decided. See `fingerprint`.
    evidence: str
    reason: str = ""
    period: str = ""
    batch_id: str = ""
    confirmed_by: str = ""
    confirmed_at: str = ""
    authorised_by: str = ""

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.department, self.column, self.target)


class MatchMemory(BaseModel):
    version: str = ""
    matches: list[ColumnMatch] = Field(default_factory=list)


class Candidate(BaseModel):
    target: str
    #: `entity:<kind>`, `measure:<name>`, `period` or `currency`, from the dictionary.
    role: str
    #: Whether the uploaded column's cleaned type is what this role needs.
    type_fits: bool
    #: For entity targets: the strongest share of distinct values this column has in
    #: common with a column another department declares as the same kind, by hash.
    #: `None` when there is nothing comparable, which is not evidence against.
    entity_overlap: float | None = None
    overlap_with: str = ""
    #: A decision already on file for this exact pair, if any.
    decided: str = ""


class ColumnQuestion(BaseModel):
    department: str
    column: str
    original: str = ""
    profile: profiling.ColumnProfile
    candidates: list[Candidate]


class CandidateList(BaseModel):
    batch_id: str
    period: str
    questions: list[ColumnQuestion] = Field(default_factory=list)
    #: Matches applied when this batch was imported, as `department.column → target`.
    applied: list[str] = Field(default_factory=list)
    #: Departments whose undeclared columns have no declared column left to match to.
    #: That is a dictionary gap only its owner can close.
    needs_dictionary_owner: list[str] = Field(default_factory=list)
    truncated: bool = False


class AppliedMatch(BaseModel):
    department: str
    column: str
    target: str
    confirmed_at: str


# --- the closed candidate set ----------------------------------------------------


def declared_columns(snapshot: dict | None, department: str) -> dict[str, str]:
    """Every column the dictionary declares for one department, with its role."""
    snapshot = snapshot or {}
    roles: dict[str, str] = {}
    for name, kind in ((snapshot.get("columns") or {}).get(department) or {}).items():
        roles[str(name)] = f"entity:{kind}"
    for name, measure in ((snapshot.get("measures") or {}).get(department) or {}).items():
        roles.setdefault(str(name), f"measure:{measure}")
    inputs = ((snapshot.get("business_review") or {}).get("inputs") or {}).get(department) or {}
    if isinstance(inputs.get("date_column"), str):
        roles.setdefault(inputs["date_column"], "period")
    currency = inputs.get("currency")
    if isinstance(currency, dict) and isinstance(currency.get("column"), str):
        roles.setdefault(currency["column"], "currency")
    return roles


def _present(table: CleanTable) -> list[str]:
    return [spec.name for spec in table.columns]


def open_columns(snapshot: dict | None, table: CleanTable) -> tuple[list[str], dict[str, str]]:
    """Uploaded columns the dictionary does not know, and declared columns absent."""
    declared = declared_columns(snapshot, table.department)
    present = _present(table)
    unknown = [name for name in present if name not in declared]
    missing = {name: role for name, role in declared.items() if name not in present}
    return unknown, missing


def count_questions(snapshot: dict | None, tables: list[CleanTable]) -> int:
    """How many declared columns are missing while unknown columns could be them. No profiling.

    The question a person answers is per missing declared column — which uploaded column is
    it, or is it really absent — not per unknown column. Counting unknown columns reported
    every undeclared header in the sheet (20 for one renamed column under the demo
    dictionary), which buried the one real question.
    """
    total = 0
    for table in tables:
        unknown, missing = open_columns(snapshot, table)
        if unknown:
            total += len(missing)
    return total


def fingerprint(profile: profiling.ColumnProfile) -> str:
    """The shape a decision was made about. Deliberately coarse: a month's row count
    changing is not new evidence; the column turning from text into numbers is."""
    return f"dtype={profile.dtype};identifier_shaped={profile.identifier_shaped}"


def candidates(batch_id: str, period: str, tables: list[CleanTable], snapshot: dict | None,
               applied: list[AppliedMatch] | None = None,
               memory: MatchMemory | None = None) -> CandidateList:
    memory = memory or load()
    batch_profile = profiling.profile(batch_id, period, tables)
    profiles = {(p.department, p.column): p for p in batch_profile.columns}
    kinds = {
        (table.department, name): role.split(":", 1)[1]
        for table in tables
        for name, role in declared_columns(snapshot, table.department).items()
        if role.startswith("entity:")
    }

    questions: list[ColumnQuestion] = []
    blocked: list[str] = []
    truncated = False
    for table in tables:
        unknown, missing = open_columns(snapshot, table)
        if unknown and not missing:
            blocked.append(table.department)
            continue
        for column in unknown:
            profile = profiles.get((table.department, column))
            if profile is None:
                continue
            if len(questions) >= MAX_QUESTIONS:
                truncated = True
                break
            options = []
            for target, role in missing.items():
                kind = role.split(":", 1)[1] if role.startswith("entity:") else None
                overlap, partner = _entity_overlap(batch_profile, table.department, column, kind, kinds)
                prior = memory_for(memory, table.department, column, target)
                options.append(Candidate(
                    target=target, role=role,
                    type_fits=profile.dtype == _EXPECTED_DTYPE.get(role.split(":", 1)[0]),
                    entity_overlap=overlap, overlap_with=partner,
                    decided=("" if prior is None else
                             ("accepted" if prior.accepted else "rejected")
                             + ("" if prior.evidence == fingerprint(profile) else " (evidence changed)")),
                ))
            questions.append(ColumnQuestion(
                department=table.department, column=column,
                original=table.original_columns.get(column, ""), profile=profile, candidates=options,
            ))
    return CandidateList(
        batch_id=batch_id, period=period, questions=questions,
        applied=[f"{a.department}.{a.column} → {a.target}" for a in applied or []],
        needs_dictionary_owner=sorted(blocked), truncated=truncated,
    )


def _entity_overlap(batch_profile: profiling.BatchProfile, department: str, column: str,
                    kind: str | None, kinds: dict[tuple[str, str], str]) -> tuple[float | None, str]:
    if kind is None:
        return None, ""
    here = f"{department}.{column}"
    best: tuple[float | None, str] = (None, "")
    for overlap in batch_profile.overlaps:
        if here not in (overlap.left, overlap.right):
            continue
        other, coverage = ((overlap.right, overlap.left_coverage) if overlap.left == here
                           else (overlap.left, overlap.right_coverage))
        other_department, other_column = other.split(".", 1)
        if kinds.get((other_department, other_column)) != kind:
            continue
        if best[0] is None or coverage > best[0]:
            best = (coverage, other)
    return best


# --- memory ------------------------------------------------------------------------


def _path() -> Path:
    configured = Path(settings.column_match_path)
    return configured if configured.is_absolute() else REPO_ROOT / configured


def load() -> MatchMemory:
    path = _path()
    if not path.is_file():
        return MatchMemory()
    return MatchMemory.model_validate_json(path.read_text(encoding="utf-8"))


def memory_for(memory: MatchMemory, department: str, column: str, target: str) -> ColumnMatch | None:
    return next((m for m in memory.matches if m.key == (department, column, target)), None)


def decide(match: ColumnMatch) -> MatchMemory:
    """Record a decision. Accepting a target retires any other accepted target for the
    same uploaded column: one column is one declared column."""
    memory = load()
    match.confirmed_at = datetime.now(UTC).isoformat()
    kept = []
    for existing in memory.matches:
        if existing.key == match.key:
            continue
        if (match.accepted and existing.accepted and existing.department == match.department
                and existing.column == match.column):
            continue
        kept.append(existing)
    memory.matches = [*kept, match]
    memory.version = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    payload = memory.model_dump(mode="json")
    _write(_path(), payload)
    # A batch imported under an older set of decisions must stay explainable.
    _write(_path().parent / "versions" / f"column-matches--{memory.version}.json", payload)
    return memory


# --- applying decisions at import --------------------------------------------------


def apply(tables: list[CleanTable], snapshot: dict | None,
          memory: MatchMemory | None = None) -> tuple[list[AppliedMatch], list[str]]:
    """Rename uploaded columns a person matched, before anything reads the tables.

    Returns what was applied and, separately, decisions that were not applied because
    the column's shape changed, so the batch can say so instead of silently asking.
    """
    memory = memory or load()
    applied: list[AppliedMatch] = []
    stale: list[str] = []
    for table in tables:
        accepted = [m for m in memory.matches if m.accepted and m.department == table.department]
        if not accepted:
            continue
        unknown, missing = open_columns(snapshot, table)
        profiles = {p.column: p for p in profiling.profile_table(table)[0]}
        renames: dict[str, str] = {}
        for match in accepted:
            if match.column not in unknown or match.target not in missing:
                continue
            if match.target in renames.values():
                continue
            profile = profiles.get(match.column)
            if profile is None or fingerprint(profile) != match.evidence:
                stale.append(f"{table.department}.{match.column} → {match.target}")
                continue
            renames[match.column] = match.target
            applied.append(AppliedMatch(department=table.department, column=match.column,
                                        target=match.target, confirmed_at=match.confirmed_at))
        if renames:
            _rename(table, renames)
    return applied, stale


def _rename(table: CleanTable, renames: dict[str, str]) -> None:
    table.columns = [spec.model_copy(update={"name": renames.get(spec.name, spec.name)})
                     for spec in table.columns]
    table.rows = [{renames.get(k, k): v for k, v in row.items()} for row in table.rows]
    table.quarantine = [{renames.get(k, k): v for k, v in row.items()} for row in table.quarantine]
    table.original_columns = {renames.get(k, k): v for k, v in table.original_columns.items()}
