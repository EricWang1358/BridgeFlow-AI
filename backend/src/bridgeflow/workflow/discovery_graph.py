"""Versioned discovery diagrams, not executable workflows or inferred schedules."""
from datetime import UTC, datetime
from typing import Literal

from pydantic import Field, model_validator

from bridgeflow.workflow.discovery import (
    Discovery,
    DiscoveryError,
    Identifier,
    Label,
    Reference,
    Strict,
    Text,
)
from bridgeflow.workflow.lifecycle import Event
from bridgeflow.workflow.store import ConcurrencyError, Pending


class FlowNode(Strict):
    id: Identifier
    title: Label
    department: Label
    role: Label
    trigger: Text
    inputs: list[Label] = Field(default_factory=list, max_length=20)
    outputs: list[Label] = Field(default_factory=list, max_length=20)
    references: list[Reference] = Field(min_length=1, max_length=10)


class FlowEdge(Strict):
    id: Identifier
    source: Identifier
    target: Identifier
    kind: Literal["information", "document"]
    status: Literal["confirmed", "inferred", "missing", "conflict"]
    rationale: Text
    condition: Text | None = None
    rework: bool = False
    references: list[Reference] = Field(default_factory=list, max_length=10)
    confirmation: Text | None = None

    @model_validator(mode="after")
    def evidence_for_status(self):
        if self.status != "missing" and not self.references:
            raise ValueError("An asserted edge requires source references")
        if self.status == "confirmed" and not self.confirmation:
            raise ValueError("Confirmed edges require an explicit human confirmation")
        if self.status != "confirmed" and self.confirmation is not None:
            raise ValueError("Only confirmed edges may contain confirmation")
        if self.status == "conflict" and len({r.model_dump_json() for r in self.references}) < 2:
            raise ValueError("A conflict requires at least two distinct source references")
        return self


class FlowGraph(Strict):
    id: Identifier
    project_id: Identifier
    opportunity_id: Identifier
    opportunity_version: int = Field(ge=1)
    title: Label
    departments: list[Label] = Field(min_length=1, max_length=20)
    nodes: list[FlowNode] = Field(min_length=1, max_length=50)
    edges: list[FlowEdge] = Field(default_factory=list, max_length=100)
    expected_seq: int = Field(ge=0)

    @model_validator(mode="after")
    def topology(self):
        ids = {node.id for node in self.nodes}
        if len(ids) != len(self.nodes) or len({edge.id for edge in self.edges}) != len(self.edges):
            raise ValueError("Node and edge identifiers must be unique")
        if any(edge.source not in ids or edge.target not in ids for edge in self.edges):
            raise ValueError("Every edge endpoint must exist")
        if any(node.department not in self.departments for node in self.nodes):
            raise ValueError("Every node department must be in graph scope")
        # Cycles, branches and disconnected unknowns are intentional draft topology.
        return self


class DiscoveryGraphs:
    def __init__(self, discovery: Discovery):
        self.discovery = discovery
        self.store = discovery.store

    def read(self, project: str, identifier: str, version: int | None = None) -> dict:
        events = self.store.read(self.discovery.stream("graph", project, identifier))
        if not events or version is not None and not 1 <= version <= len(events):
            raise DiscoveryError("Graph version not found")
        event = events[-1] if version is None else events[version - 1]
        data = dict(event.data)
        stale_sources = set()
        for item in [*data["nodes"], *data["edges"]]:
            for ref in item["references"]:
                current = self.discovery.read("material", project, ref["material_id"])
                if current["version"] != ref["version"]:
                    stale_sources.add(ref["material_id"])
        opportunity = self.discovery.opportunity(project, data["opportunity_id"])
        return {**data, "version": event.seq, "seq": event.seq, "created_at": event.at,
                "stale_sources": sorted(stale_sources),
                "opportunity_stale": opportunity["version"] != data["opportunity_version"]
                or bool(opportunity["stale_sources"])}

    def save(self, graph: FlowGraph, actor: str) -> dict:
        if not actor.strip():
            raise DiscoveryError("A verified actor is required")
        opportunity = self.discovery.opportunity(graph.project_id, graph.opportunity_id)
        if opportunity["version"] != graph.opportunity_version or opportunity["stale_sources"]:
            raise DiscoveryError("Opportunity or its evidence was revised; review before diagramming")
        if set(graph.departments) != set(opportunity["departments"]):
            raise DiscoveryError("Graph scope must match the opportunity")
        guards = {}
        source_stream = self.discovery.stream("opportunity", graph.project_id, graph.opportunity_id)
        guards[source_stream] = Pending(source_stream, graph.opportunity_version, [])
        # Guard every candidate source too, including sources absent from this diagram.
        refs = [ref for claim in opportunity["claims"] for ref in claim["references"]]
        refs += [ref.model_dump() for item in [*graph.nodes, *graph.edges] for ref in item.references]
        for raw in refs:
            ref = Reference.model_validate(raw)
            material = self.discovery.read("material", graph.project_id, ref.material_id)
            if material["version"] != ref.version:
                raise DiscoveryError("Source was revised; inspect the current version")
            if material["department"] not in graph.departments or material["parser_status"] != "parsed":
                raise DiscoveryError("Graph source is outside scope or unparsed")
            self.discovery.validate_locator(material, ref.locator)
            stream = self.discovery.stream("material", graph.project_id, ref.material_id)
            guards[stream] = Pending(stream, ref.version, [])
        stream = self.discovery.stream("graph", graph.project_id, graph.id)
        events = self.store.read(stream)
        if len(events) != graph.expected_seq:
            raise ConcurrencyError("Graph changed; reload before saving")
        if events:
            old = events[-1].data
            if set(old["departments"]) != set(graph.departments) or old["opportunity_id"] != graph.opportunity_id:
                raise DiscoveryError("Graph scope and opportunity cannot change on revision")
        now = datetime.now(UTC).isoformat()
        data = {**graph.model_dump(exclude={"expected_seq"}), "actor": actor, "status": "draft"}
        self.store.commit([*guards.values(), Pending(stream, graph.expected_seq,
                           [Event(type="graph_revision", data=data)])], at=now)
        return self.read(graph.project_id, graph.id, graph.expected_seq + 1)
