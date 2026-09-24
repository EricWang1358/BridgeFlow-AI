"""The discovery sample project: a department's material through to an approved MVP decision.

Written for the demo, the way the workflow's sample submissions are: every step goes through
the real domain services with their validation, so the sample cannot hold a state the
product would refuse. The people are fictional (`data/discovery_demo/`), and the votes and
the approval are sample data — the pages say so, and no real person's decision is implied.

The approved candidate is the scenario the workflow catalogue can run; accepting it on the
filling-and-handoff page is what links discovery (Agent 1) to the workflow (Agent 2).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from bridgeflow.workflow.discovery import Discovery, DiscoveryError, MaterialInput, OpportunityInput
from bridgeflow.workflow.discovery_decisions import (
    DecisionPolicy,
    DecisionProposal,
    DiscoveryDecisions,
)
from bridgeflow.workflow.discovery_graph import DiscoveryGraphs, FlowGraph
from bridgeflow.workflow.discovery_meetings import DiscoveryMeetings, MeetingInput
from bridgeflow.workflow.discovery_scoring import DiscoveryScores, ScoreDraft, ScoringPolicy


def load(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def seed(domain: Discovery, scoring: ScoringPolicy, decision: DecisionPolicy, sample: dict[str, Any]) -> dict:
    """Create the sample project once and return its decision. Refuses a mismatched policy."""
    project = sample["project_id"]
    if scoring.project_id != project or decision.project_id != project:
        raise DiscoveryError(f"The sample project {project} needs its own sample policies; "
                             f"this deployment's policies are for {decision.project_id}")
    decisions = DiscoveryDecisions(domain, decision)
    m = sample["material"]
    ref = [{"material_id": m["id"], "version": 1, "locator": {"kind": "header", "sheet": "csv"}}]
    try:
        existing = decisions.read(project, sample["decision"]["id"])
    except DiscoveryError:
        existing = None  # not seeded yet
    if existing is not None:
        _graph(domain, project, sample)  # projects seeded before the graph existed gain it
        return existing
    domain.register(MaterialInput.model_validate({
        "id": m["id"], "project_id": project, "department": m["department"], "period": m["period"],
        "filename": m["filename"], "declared_kind": m["declared_kind"],
        "source_description": m["source_description"], "expected_seq": 0}), m["content"].encode("utf-8"), m["by"])
    o = sample["opportunity"]
    domain.propose(OpportunityInput.model_validate({
        "id": o["id"], "project_id": project, "title": o["title"], "departments": o["departments"],
        "expected_seq": 0, "open_questions": o["open_questions"],
        "claims": [{**claim, "references": ref} for claim in o["claims"]]}), o["by"])
    _graph(domain, project, sample)
    s = sample["score"]
    DiscoveryScores(domain, scoring).save(ScoreDraft.model_validate({
        "id": s["id"], "project_id": project, "opportunity_id": o["id"], "opportunity_version": 1,
        "policy_fingerprint": scoring.fingerprint, "expected_seq": 0,
        "effort": {**s["effort"], "references": ref}, "value": {**s["value"], "references": ref}}), s["by"])
    g = sample["meeting"]
    sourced = lambda items: [{**item, "references": ref} if item.get("basis") == "reported" else item for item in items]
    DiscoveryMeetings(domain).save(MeetingInput.model_validate({
        "id": g["id"], "project_id": project, "title": g["title"], "candidates": [{"id": o["id"], "version": 1}],
        "scope": sourced(g["scope"]), "exclusions": g["exclusions"], "risks": sourced(g["risks"]),
        "resources": sourced(g["resources"]), "stages": g["stages"],
        "discussion_questions": g["discussion_questions"], "expected_seq": 0,
        "change_reason": "示例项目", "phase": "minutes", "participants": g["participants"],
        "minutes": sourced(g["minutes"])}), g["by"])
    d = sample["decision"]
    decisions.propose(DecisionProposal.model_validate({
        "id": d["id"], "project_id": project, "meeting_id": g["id"], "meeting_version": 1,
        "selected_candidates": [o["id"]], "scope": d["scope"], "exclusions": d["exclusions"],
        "rationale": d["rationale"], "expected_seq": 0, "policy_fingerprint": decision.fingerprint}), d["proposer"])
    seq = 1
    for vote in d["votes"]:
        state = decisions.vote(project, d["id"], seq, 1, vote["voter"], vote["choice"], vote["reason"])
        seq = state["seq"]
    return decisions.decide(project, d["id"], seq, 1, d["approver"], "approve", d["approval_reason"])


def _graph(domain: Discovery, project: str, sample: dict[str, Any]) -> None:
    """The candidate's information and file flow, saved once through the real graph service."""
    g, m, o = sample["graph"], sample["material"], sample["opportunity"]
    graphs = DiscoveryGraphs(domain)
    try:
        graphs.read(project, g["id"])
        return
    except DiscoveryError:
        pass
    locators = {"header": {"kind": "header", "sheet": "csv"}, "rows": {"kind": "rows", "sheet": "csv", "start": 2, "end": 3}}
    cite = lambda item: [{"material_id": m["id"], "version": 1, "locator": locators[item["locator"]]}] if item.get("locator") else []
    strip = lambda item: {k: v for k, v in item.items() if k != "locator"}
    graphs.save(FlowGraph.model_validate({
        "id": g["id"], "project_id": project, "opportunity_id": o["id"], "opportunity_version": 1,
        "title": g["title"], "departments": o["departments"], "expected_seq": 0,
        "nodes": [{**strip(node), "references": cite(node)} for node in g["nodes"]],
        "edges": [{**strip(edge), "references": cite(edge)} for edge in g["edges"]]}), g["by"])
