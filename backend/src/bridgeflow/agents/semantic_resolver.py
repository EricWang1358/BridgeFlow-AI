from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel
from rapidfuzz import fuzz

from bridgeflow.agents.base import Agent
from bridgeflow.config import settings
from bridgeflow.llm import Message
from bridgeflow.schemas import CleanTable, Entity, EntityGraph, EntityKind, Link, Relation

_TOKEN = re.compile(r"[^0-9a-z]+")

# Fallback column hints, used only until the OA field dictionary is available.
# The dictionary replaces these — see data/mappings/README.md.
_COLUMN_HINTS: dict[EntityKind, tuple[str, ...]] = {
    "sku": ("sku", "product", "item", "part_no"),
    "raw_material": ("material", "raw_material", "rm_code"),
    "gl_account": ("account", "gl", "gl_account", "cost_centre"),
    "capacity_unit": ("line", "machine", "workcentre", "work_center"),
    "customer": ("customer", "client", "account_name", "buyer"),
}

_RELATIONS: tuple[tuple[EntityKind, EntityKind, Relation], ...] = (
    ("sku", "raw_material", "consumes"),
    ("sku", "gl_account", "books_to"),
    ("sku", "capacity_unit", "produced_on"),
    ("sku", "customer", "ordered_by"),
)

# An alias pair must look this alike before we treat two labels as the same thing.
# This is the ONLY place string similarity is used — see the class docstring.
_ALIAS_SIMILARITY = 88


class _Adjudication(BaseModel):
    confidence: float
    justification: str


class SemanticResolverAgent(Agent[list[CleanTable], EntityGraph]):
    """Stage 2 — decide what is the same thing across four departments.

    Links come from three sources, in descending order of trust. Nothing is
    guessed from how identifiers are spelled:

    1. **Declared** — the field dictionary exported from OA states that this SKU
       consumes that material. Confidence 1.0, no model call. This is where the
       real mappings come from; everything below is for what the dictionary does
       not yet cover.
    2. **Co-occurrence** — two identifiers appear in the same row of the same
       department's sheet, so that sheet is asserting a relationship between
       them. Confidence scales with how many rows support it.
    3. **Adjudicated** — the model is asked about the residue, and only about
       pairs that co-occurrence already put on the table.

    String similarity is used for one thing only: merging aliases of the *same*
    entity (`SKU-A1` / `sku-a1` / `SKU A1`). It is never used to propose a link
    between different entities, because cross-department identifiers have no
    reason to resemble each other — `SKU-A1` and `RM-Alu-6061` are a product and
    the material it consumes, and they share no characters. Discovering that
    relationship from spelling is not possible, and attempting it produced zero
    links against real sample data.
    """

    slug = "resolver"
    system_prompt = (
        "You decide whether two identifiers from different departments of one small "
        "manufacturer refer to related things. You are shown the two labels, their "
        "departments, the relation being proposed, and how many rows of source data "
        "put them together. Answer with a confidence between 0 and 1 and a "
        "one-sentence justification. Be conservative: a wrong join silently corrupts "
        "every downstream number."
    )

    async def run(self, payload: list[CleanTable]) -> EntityGraph:
        dictionary = load_field_dictionary()
        entities = self._extract_entities(payload, dictionary)
        self._merge_aliases(entities)

        links: list[Link] = []
        unresolved: list[Link] = []

        declared = self._declared_links(entities, dictionary)
        links.extend(declared)
        already = {(link.source, link.target, link.relation) for link in declared}

        for candidate in self._co_occurrence_links(payload, entities, dictionary):
            key = (candidate.source, candidate.target, candidate.relation)
            if key in already:
                continue  # the dictionary already settled this one
            already.add(key)

            resolved = await self._adjudicate(candidate, entities)
            bucket = (
                links
                if resolved.confidence >= settings.resolver_confidence_threshold
                else unresolved
            )
            bucket.append(resolved)

        return EntityGraph(
            entities=list(entities.values()), links=links, unresolved=unresolved
        )

    # -- entities ------------------------------------------------------------

    def _extract_entities(
        self, tables: list[CleanTable], dictionary: FieldDictionary
    ) -> dict[str, Entity]:
        found: dict[str, Entity] = {}
        for table in tables:
            for column in table.columns:
                kind = dictionary.kind_for(table.department, column.name)
                if kind is None:
                    continue
                for row in table.rows:
                    raw = row.get(column.name)
                    if raw in (None, ""):
                        continue
                    label = str(raw).strip()
                    entity_id = f"{kind}:{_slug(label)}"
                    existing = found.get(entity_id)
                    if existing is None:
                        found[entity_id] = Entity(
                            id=entity_id, kind=kind, label=label, aliases=[label]
                        )
                    elif label not in existing.aliases:
                        existing.aliases.append(label)
        return found

    def _merge_aliases(self, entities: dict[str, Entity]) -> None:
        """Fold near-identical labels of the same kind into one entity.

        `SKU-A1` and `SKU A1` survive slugging as separate ids only when the
        difference is more than punctuation, so this catches the rest.
        """
        by_kind: dict[EntityKind, list[Entity]] = defaultdict(list)
        for entity in entities.values():
            by_kind[entity.kind].append(entity)

        for group in by_kind.values():
            for i, keeper in enumerate(group):
                for other in group[i + 1 :]:
                    if other.id not in entities:
                        continue
                    score = max(
                        fuzz.token_set_ratio(a, b)
                        for a in keeper.aliases
                        for b in other.aliases
                    )
                    if score >= _ALIAS_SIMILARITY:
                        keeper.aliases.extend(
                            a for a in other.aliases if a not in keeper.aliases
                        )
                        entities.pop(other.id, None)

    # -- links ---------------------------------------------------------------

    def _declared_links(
        self, entities: dict[str, Entity], dictionary: FieldDictionary
    ) -> list[Link]:
        """Relationships the OA field dictionary states outright. No model call."""
        links: list[Link] = []
        for source, target, relation, note in dictionary.relations:
            if source in entities and target in entities:
                links.append(
                    Link(
                        source=source,
                        target=target,
                        relation=relation,
                        confidence=1.0,
                        justification=note or "declared in the OA field dictionary",
                    )
                )
        return links

    def _co_occurrence_links(
        self,
        tables: list[CleanTable],
        entities: dict[str, Entity],
        dictionary: FieldDictionary,
    ) -> list[Link]:
        """Two identifiers in the same row means that sheet asserts they go together.

        This is the signal the data actually carries. A marketing row naming both
        `Acme Pte Ltd` and `SKU-A1` is that department stating who ordered what —
        no inference from spelling required.
        """
        support: dict[tuple[str, str, Relation], int] = defaultdict(int)
        alias_to_id = {
            alias: entity.id for entity in entities.values() for alias in entity.aliases
        }

        for table in tables:
            kinds = {
                column.name: dictionary.kind_for(table.department, column.name)
                for column in table.columns
            }
            for row in table.rows:
                present: dict[EntityKind, str] = {}
                for column_name, kind in kinds.items():
                    if kind is None:
                        continue
                    raw = row.get(column_name)
                    if raw in (None, ""):
                        continue
                    entity_id = alias_to_id.get(str(raw).strip())
                    if entity_id:
                        present[kind] = entity_id

                for source_kind, target_kind, relation in _RELATIONS:
                    source, target = present.get(source_kind), present.get(target_kind)
                    if source and target:
                        support[(source, target, relation)] += 1

        return [
            Link(
                source=source,
                target=target,
                relation=relation,
                confidence=min(0.5 + 0.1 * rows, 0.9),
                justification=f"appears together in {rows} row(s) of source data",
            )
            for (source, target, relation), rows in support.items()
        ]

    async def _adjudicate(self, link: Link, entities: dict[str, Entity]) -> Link:
        source, target = entities[link.source], entities[link.target]
        prompt = json.dumps(
            {
                "relation": link.relation,
                "source": {"kind": source.kind, "labels": source.aliases},
                "target": {"kind": target.kind, "labels": target.aliases},
                "row_support": link.justification,
            },
            ensure_ascii=False,
        )
        response = await self.llm.complete(
            system=self.system_prompt,
            messages=[Message(role="user", content=prompt)],
            schema=_Adjudication,
        )
        verdict: _Adjudication | Any = response.parsed
        if verdict is None:
            return link
        return link.model_copy(
            update={
                "confidence": verdict.confidence,
                "justification": verdict.justification,
            }
        )


# --- field dictionary --------------------------------------------------------


class FieldDictionary:
    """The mapping declarations exported from OA.

    Until that export exists the dictionary is empty and `kind_for` falls back to
    column-name hints. Both paths are deliberate: the fallback keeps the pipeline
    runnable on sample data, and the declarations take precedence the moment they
    land. See `data/mappings/README.md` for the file format.
    """

    def __init__(self, raw: dict[str, Any] | None = None) -> None:
        raw = raw or {}
        # {(department, column): kind}
        self.columns: dict[tuple[str, str], EntityKind] = {}
        for department, columns in (raw.get("columns") or {}).items():
            for column, kind in columns.items():
                self.columns[(department, column)] = kind

        # (source_id, target_id, relation, note)
        self.relations: list[tuple[str, str, Relation, str]] = [
            (r["source"], r["target"], r["relation"], r.get("note", ""))
            for r in (raw.get("relations") or [])
        ]

    @property
    def is_empty(self) -> bool:
        return not self.columns and not self.relations

    def kind_for(self, department: str, column: str) -> EntityKind | None:
        declared = self.columns.get((department, column))
        if declared is not None:
            return declared
        if self.columns:
            # A dictionary exists and does not claim this column: respect that
            # rather than second-guessing it with hints.
            return None
        return _kind_from_hint(column)


def load_field_dictionary(path: Path | None = None) -> FieldDictionary:
    target = path or Path(settings.field_dictionary_path or "")
    if not target or not target.is_file():
        return FieldDictionary()
    with target.open(encoding="utf-8") as handle:
        return FieldDictionary(yaml.safe_load(handle) or {})


def _kind_from_hint(column: str) -> EntityKind | None:
    lowered = column.lower()
    for kind, hints in _COLUMN_HINTS.items():
        if any(hint in lowered for hint in hints):
            return kind
    return None


def _slug(label: str) -> str:
    return _TOKEN.sub("-", label.lower()).strip("-")
