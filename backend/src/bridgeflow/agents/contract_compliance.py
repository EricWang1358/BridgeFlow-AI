"""Reads a quotation's contract for the clauses the legal requirements demand (#302).

Its input is the clause-type requirements (topic and guidance) and the contract split into
numbered clauses — no prices, no other quotation. Its output is a *proposal*: the host-side
check in `quote_compliance.admit_judgements` re-reads every citation against the contract and
degrades a line it cannot verify to undetermined, so a bad answer never becomes "compliant".

The demo does not call this live (the mock provider cannot read a contract); its conclusions
are frozen by `scripts/freeze_clause_judgements.py` and re-admitted on every load.
"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from bridgeflow.agents.base import Agent
from bridgeflow.llm.base import Message
from bridgeflow.quote_compliance import ClauseJudgement


class ClausePacket(BaseModel):
    requirements: list[dict]
    clauses: list[dict]
    complete: bool


class ClauseJudgements(BaseModel):
    judgements: list[ClauseJudgement] = Field(default_factory=list)


class ContractComplianceAgent(Agent[ClausePacket, ClauseJudgements]):
    slug = "contract_compliance"

    system_prompt = (
        "You check a supply contract against company legal requirements. Each requirement names "
        "a topic and guidance saying what counts. The contract is given as numbered clauses. "
        "Answer every requirement exactly once with requirement_id, status, citations and explanation. "
        "status is compliant when a clause satisfies the guidance, non_compliant when the clause is "
        "absent (only if `complete` is true) or present but fails the guidance, and undetermined when "
        "the text does not let you decide. Never guess compliance. "
        "Every citation is a clause id and an excerpt copied character for character from that clause; "
        "a compliant answer must cite at least one clause. "
        "Write the explanation in the contract's language, at most one or two sentences, and do not write "
        "any digits in it: refer to clauses in words (the second clause of Article Five), put exact wording "
        "in citations."
    )

    async def run(self, payload: ClausePacket) -> ClauseJudgements:
        response = await self.llm.complete(
            system=self.system_prompt,
            messages=[Message(role="user", content=json.dumps(payload.model_dump(), ensure_ascii=False))],
            schema=ClauseJudgements,
        )
        if isinstance(response.parsed, ClauseJudgements):
            return response.parsed
        return ClauseJudgements.model_validate_json(response.text)
