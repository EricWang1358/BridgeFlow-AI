from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel
from rapidfuzz import fuzz

from bridgeflow.agents.base import Agent
from bridgeflow.config import settings
from bridgeflow.llm import Message
from bridgeflow.schemas import CleanTable, Entity, EntityGraph, EntityKind, Link, Relation

# Which column, in which department, holds which kind of entity.
_ENTITY_COLUMNS: dict[str, tuple[EntityKind, tuple[str, ...]]] = {
    "sku": ("sku", ("sku", "product", "item", "part_no")),
    "raw_material": ("raw_material", ("material", "raw_material", "rm_code")),
    "gl_account": ("gl_account", ("account", "gl", "gl_account", "cost_centre")),
    "capacity_unit": ("capacity_unit", ("line", "machine", "workcentre", "work_center")),
    "customer": ("customer", ("customer", "client", "account_name", "buyer")),
}

_TOKEN = re.compile(r"[^0-9a-z]+")


class _Adjudication(BaseModel):
    """What we ask the model for, one candidate pair at a time."""

    confidence: float
    justification: str


class SemanticResolverAgent(Agent[list[CleanTable], EntityGraph]):
    """Stage 2 — decide what is the same thing across four departments.

    Candidates come from cheap fuzzy matching; the model only adjudicates the ones
    that are genuinely ambiguous. Anything below the confidence threshold is returned
    as `unresolved` for a human to confirm once — that confirmation then becomes a
    persisted rule, so month two is much cheaper than month one.
    """

    slug = "resolver"
    system_prompt = (
        "You decide whether two identifiers from different departments of one small "
        "manufacturer refer to the same real-world thing. You are shown the two labels, "
        "their source departments, and surrounding column names. Answer with a "
        "confidence between 0 and 1 and a one-sentence justification. "
        "Be conservative: a wrong join silently corrupts every downstream number."
    )

    async def run(self, payload: list[CleanTable]) -> EntityGraph:
        entities = self._extract_entities(payload)
        candidates = self._candidate_links(entities)

        links: list[Link] = []
        unresolved: list[Link] = []
        for link in candidates:
            adjudicated = await self._adjudicate(link, entities)
            target = links if adjudicated.confidence >= settings.resolver_confidence_threshold else unresolved
            target.append(adjudicated)

        return EntityGraph(entities=list(entities.values()), links=links, unresolved=unresolved)

    # -- extraction ----------------------------------------------------------

    def _extract_entities(self, tables: list[CleanTable]) -> dict[str, Entity]:
        found: dict[str, Entity] = {}
        for table in tables:
            for column in table.columns:
                kind = _kind_for_column(column.name)
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
                        found[entity_id] = Entity(id=entity_id, kind=kind, label=label, aliases=[label])
                    elif label not in existing.aliases:
                        existing.aliases.append(label)
        return found

    def _candidate_links(self, entities: dict[str, Entity]) -> list[Link]:
        """Block by relation type, then keep pairs that fuzzy-match well enough to be worth asking about."""
        candidates: list[Link] = []
        by_kind: dict[EntityKind, list[Entity]] = {}
        for entity in entities.values():
            by_kind.setdefault(entity.kind, []).append(entity)

        for source_kind, target_kind, relation in _RELATIONS:
            for source in by_kind.get(source_kind, []):
                for target in by_kind.get(target_kind, []):
                    score = max(
                        fuzz.token_set_ratio(a, b)
                        for a in source.aliases
                        for b in target.aliases
                    )
                    if score < 55:  # nothing in common — not worth a model call
                        continue
                    candidates.append(
                        Link(
                            source=source.id,
                            target=target.id,
                            relation=relation,
                            confidence=score / 100,
                            justification="fuzzy candidate",
                        )
                    )
        return candidates

    async def _adjudicate(self, link: Link, entities: dict[str, Entity]) -> Link:
        source = entities[link.source]
        target = entities[link.target]
        prompt = json.dumps(
            {
                "relation": link.relation,
                "source": {"kind": source.kind, "labels": source.aliases},
                "target": {"kind": target.kind, "labels": target.aliases},
                "fuzzy_score": link.confidence,
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
            update={"confidence": verdict.confidence, "justification": verdict.justification}
        )


_RELATIONS: tuple[tuple[EntityKind, EntityKind, Relation], ...] = (
    ("sku", "raw_material", "consumes"),
    ("sku", "gl_account", "books_to"),
    ("sku", "capacity_unit", "produced_on"),
    ("sku", "customer", "ordered_by"),
)


def _kind_for_column(name: str) -> EntityKind | None:
    lowered = name.lower()
    for kind, hints in _ENTITY_COLUMNS.values():
        if any(hint in lowered for hint in hints):
            return kind
    return None


def _slug(label: str) -> str:
    return _TOKEN.sub("-", label.lower()).strip("-")
