"""Long-term memory: solutions worth keeping beyond one conversation (#303).

A conversation that works out how to handle a recurring problem — which column a supplier
mislabels, why one month's margin always looks low, what the business side agreed a term
means — loses that answer when it ends. A memory keeps it: the problem, the solution, where
the solution came from, and which departments it concerns.

What a memory may hold is the method and the conclusion, never the data: no spreadsheet
rows, no cell values copied in bulk. Saving and retiring are a person's decision, so both go
through approval and record the approver; the log is append-only, so a revision never
rewrites what an earlier version said, and a retired memory stays readable in the history
but is no longer found by search.
"""

from __future__ import annotations

import json
import re
import secrets
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field

from bridgeflow.access_resolver import KNOWN_DEPARTMENTS
from bridgeflow.store import _root, _write

Action = Literal["create", "revise", "retire"]

#: Lines that look like pasted table rows: several cells split by tabs or pipes.
_ROW_LIKE = re.compile(r"(?:[^\t|\n]*[\t|]){3,}")
_WORD = re.compile(r"[a-z0-9][a-z0-9_.-]*")
_CJK = re.compile(r"[\u3400-\u9fff]+")
_lock = threading.Lock()


class Content(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    problem: str = Field(min_length=1, max_length=600)
    solution: str = Field(min_length=1, max_length=2000)
    #: Where the solution came from: the conversation, meeting note or document the person named.
    source: str = Field(min_length=1, max_length=200)
    #: Empty means company-wide.
    departments: list[str] = Field(default_factory=list, max_length=8)
    tags: list[str] = Field(default_factory=list, max_length=8)


class Revision(BaseModel):
    memory_id: str
    action: Action
    version: int = Field(ge=1)
    content: Content
    note: str = ""
    by: str
    at: str


class Memory(Content):
    id: str
    version: int
    status: Literal["active", "retired"]
    retired_reason: str = ""
    created_by: str
    created_at: str
    updated_by: str
    updated_at: str


def _path() -> Path:
    return _root() / "memory" / "memories.json"


def history() -> list[Revision]:
    path = _path()
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []
    return [Revision.model_validate(item) for item in raw.get("revisions", [])]


def _fold(revisions: list[Revision]) -> dict[str, Memory]:
    memories: dict[str, Memory] = {}
    for revision in revisions:
        first = memories.get(revision.memory_id)
        memories[revision.memory_id] = Memory(
            **revision.content.model_dump(), id=revision.memory_id, version=revision.version,
            status="retired" if revision.action == "retire" else "active",
            retired_reason=revision.note if revision.action == "retire" else "",
            created_by=first.created_by if first else revision.by,
            created_at=first.created_at if first else revision.at,
            updated_by=revision.by, updated_at=revision.at)
    return memories


def current(*, include_retired: bool = False) -> list[Memory]:
    """Every memory at its latest version, most recently changed first."""
    items = [m for m in _fold(history()).values() if include_retired or m.status == "active"]
    return sorted(items, key=lambda m: m.updated_at, reverse=True)


def _checked(content: Content) -> Content:
    unknown = sorted(set(content.departments) - KNOWN_DEPARTMENTS)
    if unknown:
        raise HTTPException(422, f"Unknown departments: {', '.join(unknown)}")
    for name in ("problem", "solution"):
        rows = [line for line in getattr(content, name).splitlines() if _ROW_LIKE.search(line)]
        if len(rows) >= 3:
            raise HTTPException(422, f"The {name} looks like pasted spreadsheet rows; a memory keeps the method "
                                     "and the conclusion, never the data")
    tags = [tag.strip() for tag in content.tags if tag.strip()]
    if any(len(tag) > 24 for tag in tags):
        raise HTTPException(422, "A tag is at most 24 characters")
    return content.model_copy(update={
        "title": content.title.strip(), "problem": content.problem.strip(), "solution": content.solution.strip(),
        "source": content.source.strip(), "departments": sorted(set(content.departments)),
        "tags": list(dict.fromkeys(tags))})


def _append(revision: Revision, revisions: list[Revision]) -> Memory:
    # Append-only: a later version never rewrites an earlier one, so the history stays readable.
    _write(_path(), {"revisions": [r.model_dump(mode="json") for r in [*revisions, revision]]})
    return _fold([*revisions, revision])[revision.memory_id]


def save(content: Content, *, actor: str, memory_id: str | None = None,
         expected_version: int | None = None, note: str = "") -> Memory:
    """Create a memory, or revise one at the version the caller last read."""
    content = _checked(content)
    with _lock:
        revisions = history()
        now = datetime.now(UTC).isoformat()
        if memory_id is None:
            return _append(Revision(memory_id=f"mem-{secrets.token_hex(4)}", action="create", version=1,
                                    content=content, note=note, by=actor, at=now), revisions)
        existing = _fold(revisions).get(memory_id)
        if existing is None:
            raise HTTPException(404, "No such memory")
        if existing.status == "retired":
            raise HTTPException(409, "This memory is retired; save a new one instead")
        if expected_version is None or expected_version != existing.version:
            raise HTTPException(409, f"This memory is at version {existing.version}; re-read it before revising")
        return _append(Revision(memory_id=memory_id, action="revise", version=existing.version + 1,
                                content=content, note=note, by=actor, at=now), revisions)


def retire(memory_id: str, *, reason: str, expected_version: int | None, actor: str) -> Memory:
    """Stop a memory from being found, keeping it and its history readable."""
    if not reason.strip():
        raise HTTPException(422, "Retiring a memory needs the reason it no longer holds")
    with _lock:
        revisions = history()
        existing = _fold(revisions).get(memory_id)
        if existing is None:
            raise HTTPException(404, "No such memory")
        if existing.status == "retired":
            raise HTTPException(409, "This memory is already retired")
        if expected_version is not None and expected_version != existing.version:
            raise HTTPException(409, f"This memory is at version {existing.version}; re-read it before retiring")
        content = Content(**existing.model_dump(include=set(Content.model_fields)))
        return _append(Revision(memory_id=memory_id, action="retire", version=existing.version + 1,
                                content=content, note=reason.strip(), by=actor,
                                at=datetime.now(UTC).isoformat()), revisions)


def terms(text: str) -> set[str]:
    """Words for Latin text, and character pairs for Chinese, which has no spaces to split on."""
    lowered = text.lower()
    found = set(_WORD.findall(lowered))
    for run in _CJK.findall(lowered):
        found |= {run} if len(run) == 1 else {run[i:i + 2] for i in range(len(run) - 1)}
    return found


#: A match in the title or tags says more about what a memory is for than one in its body.
_WEIGHTS = (("title", 3.0), ("tags", 3.0), ("problem", 2.0), ("solution", 1.0))


def search(query: str, *, department: str | None = None, limit: int = 5) -> list[tuple[Memory, float]]:
    """Active memories sharing terms with the query, best match first."""
    wanted = terms(query)
    if not wanted:
        return []
    scored = []
    for memory in current():
        if department and memory.departments and department not in memory.departments:
            continue
        score = 0.0
        for field, weight in _WEIGHTS:
            value = getattr(memory, field)
            score += weight * len(wanted & terms(" ".join(value) if isinstance(value, list) else value))
        if score:
            scored.append((memory, round(score / len(wanted), 3)))
    # current() is newest first and sorted() is stable, so equal scores keep the newer memory first.
    return sorted(scored, key=lambda pair: -pair[1])[:limit]
