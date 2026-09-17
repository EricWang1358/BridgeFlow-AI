"""Versioned discovery evidence. Draft claims never publish business standards.

Raw uploads stay in content-addressed host storage, outside model projections.
Transport code must authenticate the actor and enforce departmental access before
calling this domain service, just as for the existing workflow domain.
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from bridgeflow.workflow.lifecycle import Event
from bridgeflow.workflow.materials import MaterialError, inspect
from bridgeflow.workflow.store import ConcurrencyError, Pending, WorkflowStore

Identifier = Annotated[str, Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}$")]
Label = Annotated[str, Field(min_length=1, max_length=200)]
Text = Annotated[str, Field(min_length=1, max_length=1200)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class MaterialInput(Strict):
    id: Identifier
    project_id: Identifier
    department: Label
    period: Label
    filename: Label
    declared_kind: Literal["template", "records", "narrative", "meeting", "rule"]
    source_description: Text
    expected_seq: int = Field(ge=0)


class Locator(Strict):
    kind: Literal["header", "rows", "lines"]
    sheet: Label | None = None
    start: int | None = Field(None, ge=1)
    end: int | None = Field(None, ge=1)

    @model_validator(mode="after")
    def valid_range(self) -> Locator:
        if self.kind == "header":
            if self.sheet is None or self.start is not None or self.end is not None:
                raise ValueError("Header references require only a sheet name")
        else:
            if self.start is None or self.end is None or self.end < self.start:
                raise ValueError("A valid inclusive source range is required")
            if (self.kind == "rows") != (self.sheet is not None):
                raise ValueError("Only workbook references require a sheet name")
        return self


class Reference(Strict):
    material_id: Identifier
    version: int = Field(ge=1)
    locator: Locator


class Claim(Strict):
    kind: Literal["problem", "input", "output", "human_checkpoint", "rule_dependency", "value_hypothesis"]
    text: Text
    basis: Literal["reported", "inferred"]
    references: list[Reference] = Field(min_length=1, max_length=10)


class OpportunityInput(Strict):
    id: Identifier
    project_id: Identifier
    title: Label
    departments: list[Label] = Field(min_length=1, max_length=20)
    claims: list[Claim] = Field(min_length=1, max_length=30)
    open_questions: list[Text] = Field(default_factory=list, max_length=30)
    expected_seq: int = Field(ge=0)


class DiscoveryError(ValueError):
    pass


class Discovery:
    def __init__(self, store: WorkflowStore, blobs: Path):
        self.store, self.blobs = store, blobs

    @staticmethod
    def stream(kind: str, project: str, identifier: str) -> str:
        # All identifiers are validated even on read paths; separators cannot alias streams.
        from pydantic import TypeAdapter
        adapter = TypeAdapter(Identifier)
        return f"discovery:{kind}:{adapter.validate_python(project)}:{adapter.validate_python(identifier)}"

    def read(self, kind: Literal["material", "opportunity", "graph", "score", "meeting", "decision"], project: str, identifier: str,
             version: int | None = None) -> dict:
        events = self.store.read(self.stream(kind, project, identifier))
        if not events or version is not None and not 1 <= version <= len(events):
            raise DiscoveryError("Discovery object/version not found")
        event = events[-1] if version is None else events[version - 1]
        return {**event.data, "seq": event.seq, "version": event.seq, "created_at": event.at}

    def _append(self, kind: str, item: MaterialInput | OpportunityInput, data: dict,
                actor: str, guards: list[Pending] | None = None) -> dict:
        if not actor.strip():
            raise DiscoveryError("A verified actor is required")
        stream = self.stream(kind, item.project_id, item.id)
        events = self.store.read(stream)
        if len(events) != item.expected_seq:
            raise ConcurrencyError("Discovery revision changed; reload before saving")
        if events:
            old = events[-1].data
            # Moving evidence across scopes could expose history to new readers.
            scope = "department" if kind == "material" else "departments"
            if old[scope] != data[scope]:
                raise DiscoveryError("Scope is immutable; create a new object for another department")
        now = datetime.now(UTC).isoformat()
        data = {**data, "actor": actor}
        self.store.commit([*(guards or []), Pending(stream, item.expected_seq,
                          [Event(type=f"{kind}_revision", data=data)])], at=now)
        return {**data, "seq": item.expected_seq + 1, "version": item.expected_seq + 1, "created_at": now}

    def register(self, item: MaterialInput, payload: bytes, actor: str) -> dict:
        if not payload or len(payload) > 20 * 1024 * 1024:
            raise DiscoveryError("Material must contain 1 byte to 20 MiB")
        if Path(item.filename).name != item.filename or "\\" in item.filename:
            raise DiscoveryError("A filename, not a filesystem path, is required")
        digest = hashlib.sha256(payload).hexdigest()
        data = item.model_dump(exclude={"expected_seq"})
        data.update(digest=digest, size=len(payload), parser_status="unsupported", shape=None,
                    parser_error="No parser configured for this format", detected_kind="unknown")
        if item.filename.lower().endswith((".csv", ".xlsx")):
            try:
                shape = inspect(item.filename, payload)
                data.update(parser_status="parsed", shape=shape.model_dump(), parser_error="",
                            detected_kind="template" if shape.header_only else "records"
                            if any(s.data_rows for s in shape.sheets) else "unknown")
            except MaterialError as exc:
                data.update(parser_status="failed", parser_error=str(exc))
        elif item.filename.lower().endswith((".txt", ".md")):
            try:
                text = payload.decode("utf-8-sig")
                data.update(parser_status="parsed", parser_error="", detected_kind="text",
                            shape={"characters": len(text), "lines": len(text.splitlines())})
            except UnicodeError:
                data.update(parser_status="failed", parser_error="Text must use UTF-8")
        # Content is never interpolated into a path, nor returned in a projection.
        self.blobs.mkdir(parents=True, exist_ok=True)
        blob = self.blobs / digest
        if not blob.exists():
            import os
            import tempfile
            fd, temporary = tempfile.mkstemp(dir=self.blobs)
            try:
                with os.fdopen(fd, "wb") as output:
                    output.write(payload)
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(temporary, blob)
            finally:
                Path(temporary).unlink(missing_ok=True)
        return self._append("material", item, data, actor)

    def propose(self, item: OpportunityInput, actor: str) -> dict:
        guards = {}
        for claim in item.claims:
            for ref in claim.references:
                material = self.read("material", item.project_id, ref.material_id, ref.version)
                if material["department"] not in item.departments:
                    raise DiscoveryError("Candidate scope must include every source department")
                if material["parser_status"] != "parsed":
                    raise DiscoveryError("Unparsed material cannot support a claim")
                self.validate_locator(material, ref.locator)
                latest = self.read("material", item.project_id, ref.material_id)
                if latest["version"] != ref.version:
                    raise DiscoveryError("Source was revised; inspect its current version")
                stream = self.stream("material", item.project_id, ref.material_id)
                guards[stream] = Pending(stream, ref.version, [])
        data = item.model_dump(exclude={"expected_seq"})
        data["departments"] = sorted(set(item.departments))
        data["status"] = "proposed"
        return self._append("opportunity", item, data, actor, list(guards.values()))

    @staticmethod
    def validate_locator(material: dict, locator: Locator) -> None:
        """Validate location existence, never semantic support for a claim."""
        shape = material.get("shape") or {}
        if locator.kind == "lines":
            if "lines" not in shape or locator.end > shape["lines"]:
                raise DiscoveryError("Text line range is outside the source")
            return
        sheet = next((s for s in shape.get("sheets", []) if s["name"] == locator.sheet), None)
        if sheet is None:
            raise DiscoveryError("Sheet is absent from the inspected source")
        if locator.kind == "header":
            if sheet.get("header_row") is None:
                raise DiscoveryError("Source has no detected header")
        elif locator.end > sheet.get("physical_rows", 0):
            raise DiscoveryError("Row range is outside the inspected source")

    def opportunity(self, project: str, identifier: str, version: int | None = None) -> dict:
        result = self.read("opportunity", project, identifier, version)
        stale = set()
        for claim in result["claims"]:
            for ref in claim["references"]:
                latest = self.read("material", project, ref["material_id"])
                if latest["version"] != ref["version"]:
                    stale.add(ref["material_id"])
        return {**result, "stale_sources": sorted(stale), "approval": "not_decided"}
