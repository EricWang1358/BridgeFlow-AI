from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel

from bridgeflow.agents.base import Agent
from bridgeflow.schemas import (
    ApprovalCard,
    CleanTable,
    EntityGraph,
    Finding,
    MasterTable,
    RiskReport,
    Tension,
)

_SEVERITY_ORDER = {"critical": 0, "warning": 1, "watch": 2, "info": 3}


class SOPInput(BaseModel):
    period: str
    tables: list[CleanTable]
    graph: EntityGraph
    findings: list[Finding] = []
    tensions: list[Tension] = []


class SOPOutput(BaseModel):
    master_table: MasterTable
    risk_report: RiskReport


class SOPFlowEngine(Agent[SOPInput, SOPOutput]):
    """Stage 4 — assemble the one table everybody argues over, and the decisions it implies.

    Deterministic on purpose: no LLM call. A number on the Master Table must be
    traceable to a source row, or a judge (and later an auditor) will not trust it.
    """

    slug = "sop"

    async def run(self, payload: SOPInput) -> SOPOutput:
        master = self._build_master_table(payload)
        report = RiskReport(
            period=payload.period,
            findings=sorted(payload.findings, key=lambda f: _SEVERITY_ORDER[f.severity]),
            tensions=payload.tensions,
            cards=self._approval_cards(payload.findings),
        )
        return SOPOutput(master_table=master, risk_report=report)

    def _build_master_table(self, payload: SOPInput) -> MasterTable:
        """One wide row per entity per period, with each department's columns prefixed."""
        merged: dict[tuple[str, str], dict[str, Any]] = defaultdict(dict)

        for table in payload.tables:
            key_column = _primary_key_column(table)
            for row in table.rows:
                entity = str(row.get(key_column, "")) if key_column else ""
                bucket = merged[(table.period, entity)]
                bucket.setdefault("period", table.period)
                bucket.setdefault("entity", entity)
                for column, value in row.items():
                    if column == key_column:
                        continue
                    bucket[f"{table.department}.{column}"] = value

        rows = [row for row in merged.values() if row.get("entity")]
        periods = sorted({str(r["period"]) for r in rows})
        return MasterTable(grain="month", periods=periods, rows=rows)

    def _approval_cards(self, findings: list[Finding]) -> list[ApprovalCard]:
        """One card per department that raised something needing a decision."""
        by_role: dict[str, list[Finding]] = defaultdict(list)
        for finding in findings:
            if finding.severity in {"warning", "critical"}:
                by_role[finding.role].append(finding)

        due = (datetime.now(UTC) + timedelta(days=7)).date()
        return [
            ApprovalCard(
                title=f"{role.title()}: {len(group)} item(s) need a decision",
                owner=group[0].role,
                due=due,
                findings=group,
                options=["Accept risk", "Act on recommendation", "Request more data"],
            )
            for role, group in by_role.items()
        ]


def _primary_key_column(table: CleanTable) -> str | None:
    """The column we join this department's rows on. SKU first, customer as fallback."""
    names = [c.name for c in table.columns]
    for hint in ("sku", "product", "item", "customer", "client"):
        match = next((n for n in names if hint in n.lower()), None)
        if match:
            return match
    return names[0] if names else None
