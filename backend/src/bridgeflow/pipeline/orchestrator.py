from __future__ import annotations

import asyncio

import pandas as pd

from bridgeflow.agents import (
    DataSanitizerAgent,
    DynamicQuoteSimulator,
    EvaluationInput,
    MultiRoleEvaluatorAgent,
    QuoteInput,
    SanitizerInput,
    SemanticResolverAgent,
    SOPFlowEngine,
    SOPInput,
)
from bridgeflow.schemas import (
    CleanTable,
    Department,
    PipelineResult,
    QuoteRecommendation,
    QuoteRequest,
)


class Orchestrator:
    """Wires the four stages together: sanitize → resolve → evaluate → assemble.

    Deliberately a plain object with no framework baked in — the sequencing lives in
    one readable method so it can be lifted into whatever agent framework we settle on
    without touching the agents themselves.
    """

    def __init__(self) -> None:
        self.sanitizer = DataSanitizerAgent()
        self.resolver = SemanticResolverAgent()
        self.evaluator = MultiRoleEvaluatorAgent()
        self.sop = SOPFlowEngine()
        self.quoter = DynamicQuoteSimulator()

    async def run(
        self,
        period: str,
        frames: dict[Department, pd.DataFrame],
    ) -> PipelineResult:
        clean_tables: list[CleanTable] = list(
            await asyncio.gather(
                *(
                    self.sanitizer.run(SanitizerInput(department, period, frame))
                    for department, frame in frames.items()
                )
            )
        )

        graph = await self.resolver.run(clean_tables)

        evaluation = await self.evaluator.run(
            EvaluationInput(period=period, graph=graph, tables=clean_tables)
        )

        assembled = await self.sop.run(
            SOPInput(
                period=period,
                tables=clean_tables,
                graph=graph,
                findings=evaluation.findings,
                tensions=evaluation.tensions,
            )
        )

        return PipelineResult(
            period=period,
            clean_tables=clean_tables,
            graph=graph,
            master_table=assembled.master_table,
            risk_report=assembled.risk_report,
        )

    async def quote(self, request: QuoteRequest, result: PipelineResult) -> QuoteRecommendation:
        return await self.quoter.run(
            QuoteInput(
                request=request,
                master_table=result.master_table,
                findings=result.risk_report.findings if result.risk_report else [],
            )
        )
