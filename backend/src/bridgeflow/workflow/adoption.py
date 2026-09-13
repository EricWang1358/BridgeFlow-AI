"""Where a flow is getting stuck, from what actually happened — Agent 3's substrate (#145).

Each rule reads the event-derived snapshots and returns findings. A finding separates
the observed facts (with the artifact, handoff or notification they came from) from
the hypothesis, names the kind of problem, and says whose decision the next step is.
It never produces advice on its own authority and never scores a person: every scope
is a stage or a department.

The categories matter because they need different fixes (#145): a failing write is a
technical fault and training will not solve it; repeated questions on the same field
are a template or interaction problem for Agent 2; work returned upstream is a flow
question for Agent 1; an idle handoff past an agreed time is a resource or ownership
question only the company can answer.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from bridgeflow.workflow.lifecycle import HandoffState, NotificationState
from bridgeflow.workflow.service import ArtifactSnapshot, HandoffSnapshot, WorkflowService
from bridgeflow.workflow.store import Notification

Category = Literal["technical", "template", "flow", "resource"]
Route = Literal["operations", "agent_2_template", "agent_1_workflow", "business_owner"]


class Finding(BaseModel):
    rule: str
    category: Category
    scope: dict[str, str]
    facts: list[str]
    evidence: list[str] = Field(default_factory=list)
    hypothesis: str
    route_to: Route
    #: Nothing here is acted on automatically; somebody in this role decides.
    decided_by: str


@dataclass(frozen=True)
class Evidence:
    artifacts: list[ArtifactSnapshot]
    handoffs: list[HandoffSnapshot]
    notifications: list[Notification]
    now: datetime


class Rule(Protocol):
    name: str

    def evaluate(self, service: WorkflowService, evidence: Evidence) -> list[Finding]: ...


class SubmissionFailures:
    name = "submission_failures"

    def evaluate(self, service: WorkflowService, evidence: Evidence) -> list[Finding]:
        failing = [a for a in evidence.artifacts if a.view.failures]
        if not failing:
            return []
        by_department = Counter(a.spec.department for a in failing)
        return [Finding(
            rule=self.name, category="technical", scope={"department": department},
            facts=[f"{count} standard record(s) failed to reach the target system at least once"],
            evidence=[f"artifact:{a.id}" for a in failing if a.spec.department == department],
            hypothesis="The integration or its configuration is failing; this is not a training problem",
            route_to="operations", decided_by="system support")
            for department, count in by_department.items()]


class RepeatedQuestions:
    name = "repeated_questions"

    def evaluate(self, service: WorkflowService, evidence: Evidence) -> list[Finding]:
        limit = service.catalogue.adoption.max_question_rounds
        findings: list[Finding] = []
        for template, group in _group(evidence.artifacts).items():
            heavy = [a for a in group if a.view.question_rounds > limit]
            if not heavy:
                continue
            spec = service.catalogue.templates[template]
            findings.append(Finding(
                rule=self.name, category="template", scope={"template": template, "department": spec.department},
                facts=[f"{len(heavy)} of {len(group)} submission(s) needed more than {limit} rounds of answers"],
                evidence=[f"artifact:{a.id}" for a in heavy],
                hypothesis="Fields may be unavailable when the template expects them, or the wording may be unclear; "
                           "confirm with the people filling it in before changing the template",
                route_to="agent_2_template", decided_by=f"{spec.department} template owner"))
        return findings


class UnmappedLabels:
    name = "unmapped_labels"

    def evaluate(self, service: WorkflowService, evidence: Evidence) -> list[Finding]:
        findings: list[Finding] = []
        for template, group in _group(evidence.artifacts).items():
            names = [i.message for a in group for i in a.draft.issues if i.kind == "unmapped"]
            if not names:
                continue
            spec = service.catalogue.templates[template]
            findings.append(Finding(
                rule=self.name, category="template", scope={"template": template, "department": spec.department},
                facts=[f"{len(names)} supplied label(s) matched no declared field or alias"],
                evidence=[f"artifact:{a.id}" for a in group if any(i.kind == "unmapped" for i in a.draft.issues)],
                hypothesis="People may use wording the template does not declare; an alias needs approval before use",
                route_to="agent_2_template", decided_by=f"{spec.department} template owner"))
        return findings


class ReturnedWork:
    name = "returned_work"

    def evaluate(self, service: WorkflowService, evidence: Evidence) -> list[Finding]:
        returned = [h for h in evidence.handoffs if any(e.type == "handoff_returned" for e in h.events)]
        findings: list[Finding] = []
        for stage in sorted({h.stage for h in returned}):
            spec = service.catalogue.stages[stage]
            group = [h for h in returned if h.stage == stage]
            findings.append(Finding(
                rule=self.name, category="flow", scope={"stage": stage, "department": spec.department},
                facts=[f"{len(group)} handoff(s) into this stage were returned upstream"],
                evidence=[f"handoff:{h.id}" for h in group],
                hypothesis="What this stage needs may differ from what the upstream template produces",
                route_to="agent_1_workflow", decided_by="workflow owner"))
        return findings


class IdleHandoffs:
    name = "idle_handoffs"

    def evaluate(self, service: WorkflowService, evidence: Evidence) -> list[Finding]:
        findings: list[Finding] = []
        for handoff in evidence.handoffs:
            spec = service.catalogue.stages[handoff.stage]
            if spec.sla_hours is None or handoff.view.state is not HandoffState.WAITING:
                continue
            waited = (evidence.now - datetime.fromisoformat(handoff.updated_at)).total_seconds() / 3600
            if waited <= spec.sla_hours:
                continue
            findings.append(Finding(
                rule=self.name, category="resource", scope={"stage": handoff.stage, "department": spec.department},
                facts=[f"Waiting {waited:.0f}h against an agreed {spec.sla_hours:g}h"],
                evidence=[f"handoff:{handoff.id}"],
                hypothesis="Ownership, capacity or visibility of the handoff may be unclear; "
                           "check the notification reached the role before assuming anything else",
                route_to="business_owner", decided_by=spec.owner_role))
        return findings


class FailedNotifications:
    name = "failed_notifications"

    def evaluate(self, service: WorkflowService, evidence: Evidence) -> list[Finding]:
        failed = [n for n in evidence.notifications
                  if n.state in (NotificationState.FAILED, NotificationState.ABANDONED)]
        if not failed:
            return []
        return [Finding(
            rule=self.name, category="technical", scope={"channel": service.notifier.name},
            facts=[f"{len(failed)} notification(s) not delivered", *{n.last_error for n in failed if n.last_error}],
            evidence=[n.stream for n in failed],
            hypothesis="Downstream may not know data is ready; the data itself is unaffected",
            route_to="operations", decided_by="system support")]


RULES: tuple[Rule, ...] = (SubmissionFailures(), FailedNotifications(), RepeatedQuestions(),
                           UnmappedLabels(), ReturnedWork(), IdleHandoffs())


def _group(artifacts: list[ArtifactSnapshot]) -> dict[str, list[ArtifactSnapshot]]:
    groups: dict[str, list[ArtifactSnapshot]] = {}
    for artifact in artifacts:
        groups.setdefault(artifact.template, []).append(artifact)
    return groups


def assess(service: WorkflowService, rules: tuple[Rule, ...] = RULES) -> list[Finding]:
    evidence = Evidence(artifacts=service.artifacts(), handoffs=service.handoffs(),
                        notifications=service.store.notifications(), now=service.clock())
    return [finding for rule in rules for finding in rule.evaluate(service, evidence)]
