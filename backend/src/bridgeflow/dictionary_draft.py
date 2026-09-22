"""The dictionary draft: proposed declarations, decided one by one, published as a version.

`needs_configuration` names the department whose rows cannot be joined. Until now the
only exit was a person hand-editing the dictionary file on the server. #205 (2026-09-18)
revised the 2026-09-07 boundary: the model may now **draft** the missing declarations,
but a draft becomes the dictionary only after a person decides **every** entry and a
publish is approved. The revision changed that one rule; everything the older boundary
established still holds here:

- an undecided draft never affects anything — no import, no batch, no metric reads it;
- drafting inputs are column statistics, never cell contents (E05-UC02's guarantee);
- a draft entry without evidence does not exist — the host drops it, not the prompt;
- publishing writes a *new version* and moves on; frozen batches keep their snapshot;
- cross-department `relations` are not drafted (D33) — their evidence bar is higher
  than a column's, and string similarity stays forbidden.

Two roads produce a draft (E05-UC07 plus the OA-export road the 2026-09-22 dictionary
spreadsheet proved): transcribing a business-supplied OA dictionary (`parse_oa_bytes`),
or proposing from a batch's column profiles (the LLM agent in `agents/` — its plumbing
lives in the API layer). Both converge on the same review-and-publish gate.
"""

from __future__ import annotations

import copy
import hashlib
import io
import json
import re
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import openpyxl
import yaml
from pydantic import BaseModel, Field

from bridgeflow.agents.semantic_resolver import FieldDictionary
from bridgeflow.agents.sop_flow import UnjoinableTables
from bridgeflow.config import REPO_ROOT, settings
from bridgeflow.schemas import Department

#: The four units the deployment names, as the OA dictionary writes them. The English
#: identifiers are the system's own department keys; the Chinese labels are how the
#: business writes them in its spreadsheets (same pairing as `batches._mock_import`).
DEPARTMENT_LABELS: dict[str, str] = {
    "production": "生产部",
    "procurement": "物资部",
    "finance": "财务部",
    "marketing": "市场部",
}
_LABEL_TO_DEPARTMENT = {label: department for department, label in DEPARTMENT_LABELS.items()}
_LABEL_TO_DEPARTMENT.update({department: department for department in DEPARTMENT_LABELS})

#: The OA dictionary's own header row — the standard format the business set, not any
#: customer's sheet schema (docs/12: the OA export format is the delivery contract).
_OA_HEADERS = ("字段名称", "关联部门", "数据类型", "详细含义与用途描述", "来源表字段", "变更说明")

#: Same cleaning the sanitizer applies to uploaded headers, so a declaration names the
#: column the pipeline will actually see (`data/mappings/README.md`: cleaned names only).
_HEADER_NOISE = re.compile(r"[\W_]+")

_ENTITY_ROLE = re.compile(r"^entity:[^\s:]+$")
_MEASURE_ROLE = re.compile(r"^measure:[^\s:]+$")
_ROLES = ("period", "currency")
_ROLLUPS = ("sum", "average", "period_end")

Decision = Literal["pending", "accepted", "modified", "rejected"]


class DictionaryPublishError(RuntimeError):
    """Publishing refused; the message carries import's own error semantics."""


class ModelCall(BaseModel):
    """The one billed call behind a model-drafted dictionary (E05-UC07 AC-4).

    Recorded whether the provider answered well or not — the cost is real either way,
    and mock output is explicitly not evidence of quality.
    """

    provider: str
    model: str
    started_at: str
    finished_at: str


class DraftEntry(BaseModel):
    """One proposed declaration: this department's column plays this role."""

    entry_id: str
    department: Department
    #: The column as the sanitizer will clean it, which is what the dictionary must name.
    column: str
    #: The header as the source wrote it, for the person recognising it on screen.
    original: str = ""
    #: `entity:<kind>` / `measure:<name>` / `period` / `currency`.
    role: str
    #: Where this proposal came from. Non-empty by validation: an entry without
    #: evidence does not exist.
    evidence: str = Field(min_length=1)
    uncertainty: str = ""
    source: Literal["import", "model"] = "import"
    #: For `measure:<name>` entries: how the measure combines across periods. The
    #: importer never fills this — 期末余额 summed and 借方金额 period-ended are both
    #: plausible numbers, only one is right, and only the person knows which.
    rollup: Literal["", "sum", "average", "period_end"] = ""
    decision: Decision = "pending"
    decided_by: str = ""
    decided_at: str = ""
    reason: str = ""
    #: When the decision was `modified`: the person's replacements, which win.
    column_override: str = ""
    role_override: str = ""
    rollup_override: Literal["", "sum", "average", "period_end"] = ""

    @property
    def effective_column(self) -> str:
        return self.column_override or self.column

    @property
    def effective_role(self) -> str:
        return self.role_override or self.role

    @property
    def effective_rollup(self) -> str:
        return self.rollup_override or self.rollup


class UnmappedRow(BaseModel):
    """An OA row the transcriber deliberately did not turn into a declaration.

    Recorded rather than skipped, so nothing disappears silently and the person can
    promote one by hand if the reason is wrong.
    """

    label: str
    department: str
    reason: str


class Draft(BaseModel):
    draft_id: str
    created_at: str
    created_by: str
    #: `import` — transcribed from a business dictionary spreadsheet; `model` —
    #: proposed from a batch's column statistics.
    source: Literal["import", "model"]
    #: What the drafter worked from: the spreadsheet's name, or the batch's id.
    basis: str = ""
    batch_id: str = ""
    entries: list[DraftEntry] = Field(default_factory=list)
    unmapped: list[UnmappedRow] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    model_call: ModelCall | None = None
    #: The active dictionary's fingerprint when the draft was made. Publishing
    #: refuses if it moved — somebody published meanwhile, and their version wins.
    basis_fingerprint: str = ""
    published: bool = False
    published_at: str = ""
    published_version: str = ""

    @property
    def pending(self) -> list[DraftEntry]:
        return [entry for entry in self.entries if entry.decision == "pending"]

    @property
    def effective(self) -> list[DraftEntry]:
        """Accepted plus modified entries; rejected ones never reach the dictionary."""
        return [entry for entry in self.entries if entry.decision in ("accepted", "modified")]


# --- storage ----------------------------------------------------------------------


def _dir() -> Path:
    configured = Path(settings.dictionary_draft_path)
    return configured if configured.is_absolute() else REPO_ROOT / configured


def draft_path(draft_id: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{32}", draft_id):
        raise ValueError("Invalid draft id")
    return _dir() / f"{draft_id}.json"


def load(draft_id: str) -> Draft:
    path = draft_path(draft_id)
    if not path.is_file():
        raise FileNotFoundError(draft_id)
    return Draft.model_validate_json(path.read_text(encoding="utf-8"))


def save(draft: Draft) -> None:
    payload = draft.model_dump(mode="json")
    _write_json(_dir() / f"{draft.draft_id}.json", payload)


def fingerprint(raw: dict) -> str:
    """The digest `_declaration_label` prints, so drafts and batches name versions alike."""
    return hashlib.sha256(
        json.dumps(raw, sort_keys=True, ensure_ascii=False, default=str).encode()
    ).hexdigest()[:12]


def _write_json(path: Path, payload: dict) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    _write_text(path, text)


def _write_text(path: Path, text: str) -> None:
    """Atomic replace, same contract as `store._write` but for YAML/text payloads."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as handle:
        handle.write(text)
        temporary = Path(handle.name)
    temporary.replace(path)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _clean_header(name: object) -> str:
    return _HEADER_NOISE.sub("_", str(name).strip().lower()).strip("_")


def _department(label: object) -> str | None:
    """The system department an OA dictionary's label names, or None when unrecognized."""
    return _LABEL_TO_DEPARTMENT.get(str(label).strip())


# --- the OA dictionary transcription ----------------------------------------------


def parse_oa_bytes(payload: bytes, filename: str) -> tuple[list[DraftEntry], list[UnmappedRow], list[str], list[str]]:
    """Transcribe a business dictionary spreadsheet into draft entries.

    Deterministic — no model, no cost. The mapping is mechanical: a common-key String
    row declares each department's source column as an entity of the row's canonical
    name; a Number row declares its source column a measure. What the format cannot
    say mechanically (which common key is the report period; how a measure combines
    across periods) is left undecided for the person, never guessed from names.

    Returns entries, unmapped rows, review notes, and the departments covered.
    """
    try:
        workbook = openpyxl.load_workbook(io.BytesIO(payload), read_only=True, data_only=True)
    except Exception as exc:  # openpyxl raises a zoo; every flavor means "not this format"
        raise ValueError(f"Cannot parse {filename} as a dictionary workbook") from exc
    try:
        if not workbook.sheetnames:
            raise ValueError(f"{filename} has no sheets")
        sheet = workbook[workbook.sheetnames[0]]
        rows = [list(row) for row in sheet.iter_rows(values_only=True)]
    finally:
        workbook.close()
    if not rows:
        raise ValueError(f"{filename} is empty")
    header = {str(cell).strip() if cell is not None else "": index for index, cell in enumerate(rows[0])}
    missing = [name for name in _OA_HEADERS[:3] + (_OA_HEADERS[4],) if name not in header]
    if missing:
        raise ValueError(
            f"{filename} is not the OA dictionary format; missing columns: {', '.join(missing)}"
        )
    index = {name: header[name] for name in _OA_HEADERS}

    entries: list[DraftEntry] = []
    unmapped: list[UnmappedRow] = []
    covered: set[str] = set()
    for row in rows[1:]:
        def cell(name: str, row: list = row) -> str:
            position = index[name]
            return str(row[position]).strip() if position < len(row) and row[position] is not None else ""

        label, unit, dtype, meaning, sources, change = (cell(name) for name in _OA_HEADERS)
        if not label and not sources:
            continue
        if not sources:
            unmapped.append(UnmappedRow(label=label, department=unit,
                                        reason="No source column stated; nothing to declare"))
            continue
        seen: set[tuple[str, str]] = set()
        for source in sources.split("/"):
            source = source.strip()
            if not source or "." not in source:
                continue
            department_name, _, column_name = source.partition(".")
            department = _department(department_name)
            column = _clean_header(column_name)
            if department is None or not column or (department, column) in seen:
                unmapped.append(UnmappedRow(
                    label=label, department=department_name,
                    reason="unrecognized department" if department is None else "no usable column name",
                ))
                continue
            seen.add((department, column))
            evidence = " ".join(part for part in (
                f"OA dictionary row 「{label}」 ({unit}, {dtype})",
                f"sourced from {department_name}.{column_name}",
                meaning, f"变更: {change}" if change else "",
            ) if part)
            if dtype.lower().startswith("number"):
                measure = _strip_unit_prefix(label, unit, department)
                entries.append(DraftEntry(
                    entry_id=f"{department}::{column}::measure:{measure}", department=department,
                    column=column, original=str(column_name), role=f"measure:{measure}",
                    evidence=evidence, uncertainty="Rollup is not stated by the format; decide it.",
                ))
            elif "公共主键" in unit:
                kind = _clean_header(label)
                entries.append(DraftEntry(
                    entry_id=f"{department}::{column}::entity:{kind}", department=department,
                    column=column, original=str(column_name), role=f"entity:{kind}", evidence=evidence,
                ))
            else:
                unmapped.append(UnmappedRow(
                    label=label, department=unit,
                    reason="String column that is not a common key: neither a join key nor a measure",
                ))
                continue
            covered.add(department)

    notes: list[str] = []
    if entries:
        notes.append(
            "The transcription declares join keys and measures only. If one of the declared "
            "columns is the report month, modify that entry's role to 'period' before publishing."
        )
    absent = sorted(set(DEPARTMENT_LABELS) - covered)
    if absent:
        notes.append("No declaration for: " + ", ".join(absent) + ". Nothing was inferred for them.")
    return entries, unmapped, notes, sorted(covered)


def _strip_unit_prefix(label: str, unit: str, department: str) -> str:
    """The canonical name minus the department prefix the OA format sometimes carries.

    财务_期初金额 for 财务部 declares the measure 期初金额. Purely positional: only the
    unit's own label (or the department's English name) is stripped, and only when
    the name starts with it.
    """
    for prefix in (f"{unit}_", f"{DEPARTMENT_LABELS[department]}_",
                   f"{DEPARTMENT_LABELS[department].rstrip('部')}_", f"{department}_"):
        if label.startswith(prefix) and len(label) > len(prefix):
            return label[len(prefix):]
    return label


# --- model-drafted entries: host-side enforcement ----------------------------------


def admit_proposals(proposals: list[dict], departments: dict[str, list[str]]) -> tuple[list[DraftEntry], list[str]]:
    """Filter model proposals to what the host can stand behind.

    The prompt asks for evidence and honest uncertainty; these checks make it true
    regardless of what the model returned: departments must be among those uploaded,
    the column must be one that department actually carried, the role must parse, and
    an entry with no evidence is dropped and counted — not repaired.
    """
    admitted: list[DraftEntry] = []
    dropped: list[str] = []
    taken: set[tuple[str, str]] = set()
    for proposal in proposals:
        department = str(proposal.get("department", ""))
        column = _clean_header(proposal.get("column", ""))
        role = str(proposal.get("role", ""))
        evidence = str(proposal.get("evidence", "")).strip()
        where = f"{department or '?'}.{column or '?'}"
        if department not in departments or column not in departments[department]:
            dropped.append(f"{where}: not a column of this batch")
            continue
        if not (_ENTITY_ROLE.match(role) or _MEASURE_ROLE.match(role) or role in _ROLES):
            dropped.append(f"{where}: role {role!r} does not parse")
            continue
        if not evidence:
            dropped.append(f"{where}: no evidence")
            continue
        if (department, column) in taken:
            dropped.append(f"{where}: one entry per column")
            continue
        taken.add((department, column))
        admitted.append(DraftEntry(
            entry_id=f"{department}::{column}::{role}", department=department,  # type: ignore[arg-type]
            column=column, role=role, evidence=evidence,
            uncertainty=str(proposal.get("uncertainty", "")).strip(),
            source="model",
        ))
    return admitted, dropped


# --- decisions --------------------------------------------------------------------


def check_decision(draft: Draft, entry_id: str, decision: Decision, *,
                   column: str = "", role: str = "", rollup: str = "") -> DraftEntry:
    """Everything a decision must satisfy, without writing anything.

    Run before an approval is spent, so a refused decision costs the person a
    correction, not a fresh approval.
    """
    if draft.published:
        raise DictionaryPublishError("This draft is already published; draft a new one")
    entry = next((entry for entry in draft.entries if entry.entry_id == entry_id), None)
    if entry is None:
        raise KeyError(entry_id)
    if decision == "modified":
        clean_column = _clean_header(column) if column else entry.column
        new_role = role or entry.role
        if column and not clean_column:
            raise DictionaryPublishError("The replacement column name is empty after cleaning")
        if role and not (_ENTITY_ROLE.match(new_role) or _MEASURE_ROLE.match(new_role) or new_role in _ROLES):
            raise DictionaryPublishError(f"The replacement role {new_role!r} does not parse")
        if new_role.startswith("measure:") and (rollup or entry.effective_rollup) not in _ROLLUPS:
            raise DictionaryPublishError(
                "A measure needs its rollup (sum / average / period_end) before it can be decided")
    elif decision == "accepted":
        if entry.role.startswith("measure:") and (rollup or entry.rollup) not in _ROLLUPS:
            raise DictionaryPublishError(
                "A measure needs its rollup (sum / average / period_end) before it can be decided")
    return entry


def decide(draft: Draft, entry_id: str, decision: Decision, *, by: str, reason: str = "",
           column: str = "", role: str = "", rollup: str = "") -> Draft:
    """Record one person's decision on one entry. Validate with `check_decision` first."""
    entry = check_decision(draft, entry_id, decision, column=column, role=role, rollup=rollup)
    if decision == "modified":
        if column:
            entry.column_override = _clean_header(column)
        if role:
            entry.role_override = role
        if rollup:
            entry.rollup_override = rollup
    elif decision == "accepted" and rollup:
        entry.rollup_override = rollup
    entry.decision = decision
    entry.decided_by, entry.decided_at, entry.reason = by, _now(), reason
    save(draft)
    return draft


# --- publishing -------------------------------------------------------------------


def merge(current: dict, entries: list[DraftEntry]) -> dict:
    """Fold decided entries into a copy of the active dictionary.

    Only the slots the entries speak about are touched: relations, sheet layouts and
    every other paragraph the draft never mentions survive a publish untouched.
    """
    merged = copy.deepcopy(current)
    for entry in entries:
        department, column, role = entry.department, entry.effective_column, entry.effective_role
        if role.startswith("entity:"):
            merged.setdefault("columns", {}).setdefault(department, {})[column] = role.split(":", 1)[1]
        elif role.startswith("measure:"):
            merged.setdefault("measures", {}).setdefault(department, {})[column] = role.split(":", 1)[1]
            if entry.effective_rollup:
                merged.setdefault("rollups", {})[role.split(":", 1)[1]] = entry.effective_rollup
        elif role == "period":
            merged.setdefault("period_columns", {})[department] = column
        elif role == "currency":
            merged.setdefault("business_review", {}).setdefault("inputs", {}).setdefault(
                department, {}).setdefault("currency", {})["column"] = column
    return merged


def validate_merged(merged: dict) -> FieldDictionary:
    """The import side's own checks, run before a publish spends its approval.

    Same semantics as `_load_dictionary` and `UnjoinableTables`: a department the
    dictionary says anything about must also carry a joinable entity column, or the
    version would ship a guaranteed `needs_configuration`.
    """
    try:
        dictionary = FieldDictionary(merged)
        date_orders = merged.get("date_order") or {}
        if not isinstance(date_orders, dict) or not set(date_orders.values()) <= {"day_first", "month_first"}:
            raise ValueError("date_order must map departments to day_first or month_first")
    except (ValueError, TypeError, AttributeError, KeyError) as exc:
        raise DictionaryPublishError(
            "Field dictionary configuration is invalid; ask the administrator to correct it before importing"
        ) from exc
    covered = {department for department, _ in dictionary.columns} | {department for department, _ in dictionary.measures}
    joinable = {department for department, _ in dictionary.columns}
    missing = sorted(covered - joinable)
    if missing:
        raise DictionaryPublishError(str(UnjoinableTables(missing)))
    # One measure, one column per department: two columns declared as the same
    # measure make the metric side refuse rather than pick (`data/mappings/README.md`).
    # Refuse here too, before the version ships the ambiguity.
    slots: dict[tuple[str, str], list[str]] = {}
    for (department, column), measure in dictionary.measures.items():
        slots.setdefault((department, measure), []).append(column)
    doubled = sorted(f"{department}.{measure} ← {', '.join(sorted(columns))}"
                     for (department, measure), columns in slots.items() if len(columns) > 1)
    if doubled:
        raise DictionaryPublishError(
            "A measure must map to exactly one column per department: " + "; ".join(doubled))
    return dictionary


def _current_raw() -> dict:
    from bridgeflow.metrics import dictionary_path

    path = dictionary_path()
    if not path.is_file():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def check_publish(draft: Draft) -> tuple[list[DraftEntry], dict, dict]:
    """Every refusal a publish can raise, without writing anything.

    Run before an approval is spent (`dictionary_publish` is the widest grant in the
    system — it must never be burned on a draft that could not ship anyway). Returns
    the effective entries, the current dictionary and the merged successor.
    """
    if draft.published:
        raise DictionaryPublishError("This draft is already published; draft a new one")
    if draft.pending:
        raise DictionaryPublishError(
            f"{len(draft.pending)} entry(ies) still undecided; decide every entry before publishing")
    effective = draft.effective
    if not effective:
        raise DictionaryPublishError("Every entry was rejected; there is nothing to publish")
    current = _current_raw()
    if fingerprint(current) != draft.basis_fingerprint:
        raise DictionaryPublishError(
            "The dictionary changed since this draft was made; draft again from the current version")
    undecidable = [entry for entry in effective
                   if entry.effective_role.startswith("measure:") and entry.effective_rollup not in _ROLLUPS]
    if undecidable:
        raise DictionaryPublishError(
            "No rollup was decided for: "
            + ", ".join(f"{entry.department}.{entry.effective_column}" for entry in undecidable))
    merged = merge(current, effective)
    validate_merged(merged)
    return effective, current, merged


def publish(draft: Draft, *, by: str) -> dict:
    """Decide-complete drafts only; writes a new version and leaves the old ones alone.

    Raises `DictionaryPublishError` with import's semantics; the API layer maps it to
    a 409 so nothing is written on refusal.
    """
    _, _, merged = check_publish(draft)

    from bridgeflow.metrics import dictionary_path

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    version = f"{stamp}--{fingerprint(merged)}"
    versions = dictionary_path().parent / "versions"
    _write_text(versions / f"field-dictionary--{version}.yaml",
                yaml.safe_dump(merged, allow_unicode=True, sort_keys=True))
    _write_text(dictionary_path(), yaml.safe_dump(merged, allow_unicode=True, sort_keys=True))

    draft.published, draft.published_at, draft.published_version = True, _now(), version
    draft.notes.append(f"Published by {by} as version {version}")
    save(draft)
    _write_json(versions / f"dictionary-draft--{draft.draft_id}--published.json", draft.model_dump(mode="json"))
    return merged


def new_draft(*, source: Literal["import", "model"], created_by: str, basis: str = "",
              batch_id: str = "", entries: list[DraftEntry] | None = None,
              unmapped: list[UnmappedRow] | None = None, notes: list[str] | None = None,
              model_call: ModelCall | None = None) -> Draft:
    draft = Draft(
        draft_id=uuid.uuid4().hex, created_at=_now(), created_by=created_by, source=source,
        basis=basis, batch_id=batch_id, entries=entries or [], unmapped=unmapped or [],
        notes=notes or [], model_call=model_call, basis_fingerprint=fingerprint(_current_raw()),
    )
    save(draft)
    return draft
