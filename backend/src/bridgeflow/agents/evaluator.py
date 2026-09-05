from __future__ import annotations

import asyncio
import json

from pydantic import BaseModel

from bridgeflow.agents.base import Agent
from bridgeflow.llm import Message
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
    "- Every claim must cite concrete evidence rows from the data you are given.\n"
    "- One sentence per claim. No hedging, no 'it may be worth considering'.\n"
    "- If the data does not support a finding for your role, return an empty list.\n"
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
        results = await asyncio.gather(
            *(self._evaluate_role(role, payload) for role in ROLE_BRIEFS)
        )
        findings = [f for group in results for f in group]
        return EvaluationOutput(findings=findings, tensions=self._find_tensions(findings))

    async def _evaluate_role(self, role: Department, payload: EvaluationInput) -> list[Finding]:
        context = json.dumps(
            {
                "period": payload.period,
                "entities": [e.model_dump() for e in payload.graph.entities],
                "links": [link.model_dump() for link in payload.graph.links],
                "tables": [
                    {"department": t.department, "columns": [c.name for c in t.columns], "rows": t.rows}
                    for t in payload.tables
                ],
            },
            ensure_ascii=False,
            default=str,
        )
        response = await self.llm.complete(
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
