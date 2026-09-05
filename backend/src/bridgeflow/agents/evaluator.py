from __future__ import annotations

import asyncio
import json

from pydantic import BaseModel

from bridgeflow import metrics
from bridgeflow.agents.base import Agent
from bridgeflow.llm import Message, get_provider
from bridgeflow.schemas import (
    CleanTable,
    Department,
    EntityGraph,
    Finding,
    Tension,
)

ROLE_BRIEFS: dict[Department, str] = {
    "production": (
        "You are the production manager. Judge order trend, capacity utilisation and "
        "remaining headroom. You care whether we can physically deliver what sales sold."
    ),
    "finance": (
        "You are the finance controller. Find loss-making projects, lengthening payment "
        "terms and bad-debt exposure. You care whether the revenue turns into cash."
    ),
    "procurement": (
        "You are the procurement lead. Track raw-material price movement and purchase "
        "cost drift against the assumptions our prices were built on."
    ),
    "marketing": (
        "You are the sales lead. Tier customers by value under the capacity constraints "
        "production reports. You care which customers deserve our limited line time."
    ),
}

_SHARED_RULES = (
    "\nRules:\n"
    "- You are given metrics that have already been computed by rule, each with the "
    "formula used and a sample of the source cells. **Do not do arithmetic.** Quote "
    "the figures as given; a number you worked out yourself cannot be audited.\n"
    "- Every claim must cite one of those metrics as evidence.\n"
    "- Metrics listed under `unavailable` could not be computed. Say so where it "
    "matters; do not reason as though a missing figure is a zero or a non-issue.\n"
    "- One sentence per claim. No hedging, no 'it may be worth considering'.\n"
    "- If the metrics do not support a finding for your role, return an empty list.\n"
    "- Do not comment on other departments' concerns; another agent covers those."
)


class _RoleFindings(BaseModel):
    findings: list[Finding]


class EvaluationInput(BaseModel):
    period: str
    graph: EntityGraph
    tables: list[CleanTable]


class EvaluationOutput(BaseModel):
    findings: list[Finding] = []
    tensions: list[Tension] = []


class MultiRoleEvaluatorAgent(Agent[EvaluationInput, EvaluationOutput]):
    """Stage 3 — four department heads read the same table and disagree productively.

    The roles run concurrently and are deliberately not reconciled: where two roles
    reach opposite conclusions about the same entity we surface a `Tension`, because
    that disagreement is the thing a human actually needs to decide.
    """

    slug = "evaluator"

    async def run(self, payload: EvaluationInput) -> EvaluationOutput:
        # Each role gets its own lane, or `gather` is theatre: a dsh provider
        # serialises every call sharing one, so four roles behind one provider ran
        # strictly one after another while looking concurrent (#51).
        results = await asyncio.gather(
            *(self._evaluate_role(role, payload) for role in ROLE_BRIEFS)
        )
        findings = [f for group in results for f in group]
        return EvaluationOutput(findings=findings, tensions=self._find_tensions(findings))

    async def _evaluate_role(self, role: Department, payload: EvaluationInput) -> list[Finding]:
        """Hand this role its metrics — never the rows they were computed from.

        The previous version serialised every cleaned row into the prompt: 5.3 KB for
        an eighteen-row sample, against a PRD that sizes one batch at 200,000. It also
        meant the figures in a finding were the model's own arithmetic, which cannot
        be reproduced or signed off. Rules compute; the model explains (#13, #58).
        """
        values, refusals = metrics.for_role(role, payload.period, payload.tables)
        llm = self._llm or get_provider(self.slug, lane=role)
        context = json.dumps(
            {
                "period": payload.period,
                "entities": [e.model_dump() for e in payload.graph.entities],
                "links": [link.model_dump() for link in payload.graph.links],
                "metrics": [v.model_dump() for v in values],
                # A role not told a metric is missing will reason as though it does
                # not matter, so the refusals travel with the figures.
                "unavailable": refusals,
            },
            ensure_ascii=False,
            default=str,
        )
        response = await llm.complete(
            system=ROLE_BRIEFS[role] + _SHARED_RULES,
            messages=[Message(role="user", content=context)],
            schema=_RoleFindings,
        )
        parsed = response.parsed
        if parsed is None:
            return []
        # The model does not get to pick which role it is speaking as.
        return [f.model_copy(update={"role": role}) for f in parsed.findings]

    def _find_tensions(self, findings: list[Finding]) -> list[Tension]:
        """Two roles pointing at the same entity with opposite urgency is a decision, not noise."""
        tensions: list[Tension] = []
        by_entity: dict[str, list[Finding]] = {}
        for finding in findings:
            for evidence in finding.evidence:
                by_entity.setdefault(evidence.entity_id, []).append(finding)

        for entity_id, group in by_entity.items():
            severe = [f for f in group if f.severity in {"warning", "critical"}]
            calm = [f for f in group if f.severity == "info"]
            for a in severe:
                for b in calm:
                    if a.role == b.role:
                        continue
                    tensions.append(
                        Tension(
                            finding_a=a,
                            finding_b=b,
                            description=(
                                f"{a.role} flags {entity_id} as {a.severity} while "
                                f"{b.role} treats it as routine — needs a human call."
                            ),
                        )
                    )
        return tensions
