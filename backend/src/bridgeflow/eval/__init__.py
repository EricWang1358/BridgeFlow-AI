"""The acceptance runner.

`data/acceptance/` holds three industries, each with a held-out month and a
`expected.yaml` stating what should happen. Until something runs them they are
files, not evidence — and `docs/12` already promises a green eval suite as a
delivery metric.

This runner is deliberately blunt: it reports what passed, what failed, and which
issue owns each failure. It is expected to be red on arrival. The defects it names
are real and open (shifted columns and duplicate rows are #16), and the correct
response to a red row is to fix the defect or to argue the expectation, never to
delete the expectation so the suite goes green.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field

import pandas as pd
import yaml

from bridgeflow import metrics
from bridgeflow.agents import DataSanitizerAgent, SanitizerInput
from bridgeflow.agents.semantic_resolver import FieldDictionary
from bridgeflow.config import REPO_ROOT
from bridgeflow.schemas import CleanTable

DATA = REPO_ROOT / "data"
DEPARTMENTS = ("production", "procurement", "finance", "marketing")
INDUSTRIES = ("manufacturing", "food", "electronics")

#: Which open issue owns each expectation we know we do not meet yet. Naming the
#: issue in the output is what stops a red row turning into a deleted expectation.
KNOWN_GAPS = {
    "shifted_columns": "#16",
    "duplicate_row": "#16",
    "currency_prefix": "#17 (currency is stripped but not recorded)",
}


@dataclass
class Check:
    industry: str
    name: str
    passed: bool
    detail: str = ""
    owner: str = ""


@dataclass
class Report:
    checks: list[Check] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def total(self) -> int:
        return len(self.checks)

    def render(self) -> str:
        lines = [f"acceptance: {self.passed}/{self.total} passed", ""]
        for check in self.checks:
            mark = "PASS" if check.passed else "FAIL"
            owner = f"  [{check.owner}]" if check.owner else ""
            lines.append(f"  {mark}  {check.industry:<14} {check.name}{owner}")
            if check.detail and not check.passed:
                lines.append(f"        {check.detail}")
        return "\n".join(lines)


def guard_patterns() -> list[re.Pattern[str]]:
    """The guard's patterns, read out of the TypeScript that enforces them.

    Duplicating them in Python would let the two copies drift, and the copy that
    matters is the one running at tool dispatch.
    """
    source = (REPO_ROOT / "plugins" / "src" / "guards" / "untrusted-input.ts").read_text("utf-8")
    block = source[source.index("INSTRUCTION_SHAPES") : source.index("/** Where an offending")]
    return [
        re.compile(raw, re.IGNORECASE if "i" in flags else 0)
        for raw, flags in re.findall(r"^\s*/(.+)/([a-z]*),\s*$", block, re.MULTILINE)
    ]


def dictionary_for(industry: str) -> FieldDictionary:
    name = (
        "field-dictionary.example.yaml"
        if industry == "manufacturing"
        else f"field-dictionary.{industry}.example.yaml"
    )
    return FieldDictionary(yaml.safe_load((DATA / "mappings" / name).read_text("utf-8")))


async def _clean(industry: str, period: str) -> list[CleanTable]:
    agent = DataSanitizerAgent()
    folder = DATA / "acceptance" / industry
    tables = []
    for department in DEPARTMENTS:
        path = folder / f"{department}_{period}.csv"
        if path.is_file():
            tables.append(await agent.run(SanitizerInput(department, period, pd.read_csv(path))))
    return tables


def _detects(tables: list[CleanTable], rule_fragment: str) -> bool:
    return any(
        rule_fragment in correction.rule for table in tables for correction in table.corrections
    )


#: Which correction rule proves each declared defect was noticed. A defect with no
#: rule behind it is one nothing detects — which is the point of listing it.
_DEFECT_RULES = {
    "mixed_date_formats": "date_parse",
    "currency_prefix": "number_normalise",
    "shifted_columns": "shift",
    "duplicate_row": "duplicate",
}


def _detected(kind: str, tables: list[CleanTable]) -> bool:
    if kind == "blank_measurement":
        # Absence is the evidence here: a blank must survive as a blank rather than
        # being filled in, so finding one is the pass condition.
        return any(v in (None, "") for t in tables for r in t.rows for v in r.values())
    rule = _DEFECT_RULES.get(kind)
    return bool(rule) and _detects(tables, rule)


async def run(industries: tuple[str, ...] = INDUSTRIES) -> Report:
    report = Report()
    for industry in industries:
        expected = yaml.safe_load((DATA / "acceptance" / industry / "expected.yaml").read_text("utf-8"))
        period = expected["period"]
        tables = await _clean(industry, period)
        dictionary = dictionary_for(industry)

        report.checks.append(
            Check(industry, "the held-out month loads", bool(tables), "no tables were read")
        )

        # A metric must compute on the held-out month with no industry-specific code.
        try:
            value = metrics.compute("total_output", period, tables, dictionary=dictionary)
            ok, detail = value.value > 0 and bool(value.sources), ""
        except metrics.MetricRefused as refused:
            ok, detail = False, str(refused)
        report.checks.append(Check(industry, "total_output computes with evidence", ok, detail))

        # Quality defects the dataset deliberately contains.
        for defect in expected["quality_defects"]:
            kind = defect["kind"]
            detected = _detected(kind, tables)
            report.checks.append(
                Check(
                    industry,
                    f"detects {kind}",
                    detected,
                    defect["expect"],
                    KNOWN_GAPS.get(kind, ""),
                )
            )

        # The planted injection must be recognised by the guard's own patterns.
        poisoned = list((DATA / "acceptance" / industry / "poisoned").glob("*.csv"))
        text = poisoned[0].read_text("utf-8") if poisoned else ""
        report.checks.append(
            Check(
                industry,
                "the planted instruction is recognised",
                any(p.search(text) for p in guard_patterns()),
                expected["refusals"][0]["expect"],
            )
        )
    return report


def main() -> int:
    report = asyncio.run(run())
    print(report.render())
    return 0 if report.passed == report.total else 1
