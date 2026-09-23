"""Which approved MVP decision the workflow runs under (E01-UC06 → E02-UC01).

Discovery (Agent 1) ends in a decision whose `agent2_handoff` names the approved candidates,
scope and exclusions. Accepting it is a person's act, through approval, and it is checked
at the moment it happens and every time it is read afterwards:

- the decision must be approved *now*, at the version the person was shown;
- every approved candidate must be a scenario this catalogue declares it can run;
- a decision revised or withdrawn later makes the accepted scope stale, and new records are
  refused until the current decision is accepted. A decision read once is never a standing
  licence — the HANDOFF rule for this seam.

Acceptance is an append-only receipt in the workflow's own store (`scope:mvp`); nothing is
copied out of discovery that discovery could later change underneath.
"""
from __future__ import annotations

from typing import Any

from bridgeflow.workflow.discovery import Discovery, DiscoveryError
from bridgeflow.workflow.discovery_decisions import DecisionPolicy, DiscoveryDecisions
from bridgeflow.workflow.lifecycle import Event
from bridgeflow.workflow.service import WorkflowService

STREAM = "scope:mvp"


class ScopeError(Exception):
    """An acceptance the current decision or catalogue does not allow."""


def _decision(domain: Discovery, policy: DecisionPolicy, project: str, identifier: str) -> dict[str, Any]:
    try:
        return DiscoveryDecisions(domain, policy).read(project, identifier)
    except DiscoveryError as exc:
        raise ScopeError(str(exc)) from exc


def accept(service: WorkflowService, domain: Discovery, policy: DecisionPolicy, *, project: str,
           decision_id: str, expected_decision_seq: int, by: str) -> dict[str, Any]:
    decision = _decision(domain, policy, project, decision_id)
    handoff = decision.get("agent2_handoff")
    if handoff is None:
        raise ScopeError(f"Decision {decision_id} is {decision['status']}, not approved; nothing can be accepted")
    if handoff["decision_seq"] != expected_decision_seq:
        raise ScopeError(f"Decision {decision_id} is at version {handoff['decision_seq']}, "
                         f"the request was based on {expected_decision_seq}; read it again")
    runnable = set(service.catalogue.mvp.candidates)
    unknown = [c["id"] for c in handoff["candidates"] if c["id"] not in runnable]
    if unknown:
        raise ScopeError(f"The approved candidates {', '.join(unknown)} are not scenarios this workflow "
                         f"catalogue declares ({', '.join(sorted(runnable)) or 'none'})")
    current = service.store.read(STREAM)
    service._append(STREAM, current[-1].seq if current else 0, [Event("scope_accepted", {**handoff, "by": by})])
    return view(service, domain, policy)


def view(service: WorkflowService, domain: Discovery | None, policy: DecisionPolicy | None) -> dict[str, Any]:
    """The accepted scope, re-checked against the decision as it stands now."""
    events = service.store.read(STREAM)
    runnable = list(service.catalogue.mvp.candidates)
    if not events:
        return {"accepted": None, "current": False, "stale_reasons": [], "runnable_candidates": runnable}
    last = events[-1]
    accepted = {**dict(last.data), "accepted_at": last.at}
    reasons: list[str] = []
    if domain is None or policy is None or policy.project_id != accepted["project_id"]:
        reasons.append("decision_unreadable")
    else:
        try:
            now = DiscoveryDecisions(domain, policy).read(accepted["project_id"], accepted["decision_id"])
        except DiscoveryError:
            now = None
        if now is None:
            reasons.append("decision_missing")
        elif now.get("agent2_handoff") is None:
            reasons.append(f"decision_{now['status']}")
        elif now["agent2_handoff"]["decision_seq"] != accepted["decision_seq"]:
            reasons.append("decision_revised")
    return {"accepted": accepted, "current": not reasons, "stale_reasons": reasons, "runnable_candidates": runnable}


def pending(domain: Discovery, policy: DecisionPolicy, service: WorkflowService) -> list[dict[str, Any]]:
    """Approved decisions in the policy's project that name a scenario this catalogue runs."""
    runnable = set(service.catalogue.mvp.candidates)
    found = []
    for stream in domain.store.streams(Discovery.stream("decision", policy.project_id, "x")[:-1]):
        identifier = stream.rsplit(":", 1)[-1]
        try:
            decision = DiscoveryDecisions(domain, policy).read(policy.project_id, identifier)
        except DiscoveryError:
            continue
        handoff = decision.get("agent2_handoff")
        if handoff and any(c["id"] in runnable for c in handoff["candidates"]):
            found.append({"project_id": policy.project_id, "decision_id": identifier,
                          "decision_seq": handoff["decision_seq"], "scope": handoff["scope"],
                          "candidates": [c["id"] for c in handoff["candidates"]]})
    return found


def require_current(service: WorkflowService, domain: Discovery | None, policy: DecisionPolicy | None) -> None:
    """New records are refused while the accepted scope's decision has changed underneath."""
    state = view(service, domain, policy)
    if state["accepted"] is not None and not state["current"]:
        raise ScopeError("The MVP decision this workflow runs under has changed "
                         f"({', '.join(state['stale_reasons'])}); accept the current decision before new records")
