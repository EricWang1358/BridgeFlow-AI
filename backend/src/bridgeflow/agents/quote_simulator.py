from __future__ import annotations

import json

from pydantic import BaseModel

from bridgeflow.agents.base import Agent
from bridgeflow.llm import Message
from bridgeflow.schemas import (
    Finding,
    MasterTable,
    QuoteRecommendation,
    QuoteRequest,
)


class QuoteInput(BaseModel):
    request: QuoteRequest
    master_table: MasterTable
    findings: list[Finding] = []


class DynamicQuoteSimulator(Agent[QuoteInput, QuoteRecommendation]):
    """Sub-feature — what should we actually charge this customer, this month?

    Triggered from the evaluator's output rather than run on every pipeline pass: it
    only makes sense once we know current material cost, capacity headroom and the
    customer's payment history.
    """

    slug = "quote"
    system_prompt = (
        "You price a manufacturing enquiry for a Singaporean SME.\n"
        "You are given the aligned master table and the current risk findings.\n"
        "Return a floor price (below which the job loses money at current material "
        "cost), a target price, and a stretch price, plus recommended payment terms in "
        "days and whether capacity allows the requested delivery.\n"
        "Shorten payment terms when the customer's receivables are already ageing. "
        "Every number in `rationale` must trace to a row you were given."
    )

    async def run(self, payload: QuoteInput) -> QuoteRecommendation:
        context = json.dumps(
            {
                "enquiry": payload.request.model_dump(mode="json"),
                "master_table": payload.master_table.model_dump(mode="json"),
                "findings": [f.model_dump(mode="json") for f in payload.findings],
            },
            ensure_ascii=False,
        )
        response = await self.llm.complete(
            system=self.system_prompt,
            messages=[Message(role="user", content=context)],
            schema=QuoteRecommendation,
        )
        if response.parsed is None:
            raise RuntimeError("quote simulator returned no structured recommendation")
        return response.parsed
