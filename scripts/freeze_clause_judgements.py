"""Freeze the contract-clause conclusions shown in the built-in quotation samples (#302).

The demo runs on the mock provider, which cannot read a contract, so the model's reading of
each sample contract is taken once here and written to `clause-judgements.yaml`. The page
re-admits that file on every load (`quote_compliance.admit_judgements`): a citation that is
not in the contract, or a conclusion made against another legal version or contract text,
shows as undetermined rather than as the model said.

Re-run after changing a sample contract or the legal requirements:

    cd backend && LLM_PROVIDER=anthropic .venv/bin/python ../scripts/freeze_clause_judgements.py

`LLM_PROVIDER_CONTRACT_COMPLIANCE` overrides the provider for this agent only. The mock
provider is refused: its output is not a reading of anything.
"""
from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

from bridgeflow.agents.contract_compliance import ClausePacket, ContractComplianceAgent
from bridgeflow.config import REPO_ROOT, settings
from bridgeflow.quote_compliance import Bundle, admit_judgements

HEADER = """\
# Frozen clause conclusions for the built-in quotation samples (#302 demo cut).
# Written by scripts/freeze_clause_judgements.py. Re-checked on every load: a citation not in the contract,
# a compliant answer without a citation, digits in the explanation, or another legal version or contract text
# shows that line as undetermined. A reference only; it does not replace legal review.
"""


async def main() -> int:
    provider = settings.provider_for(ContractComplianceAgent.slug)
    if provider == "mock":
        print("Refusing to freeze mock output; set LLM_PROVIDER or LLM_PROVIDER_CONTRACT_COMPLIANCE.", file=sys.stderr)
        return 2
    bundle = Bundle(REPO_ROOT / settings.quotation_cases_path)
    agent = ContractComplianceAgent()
    quotes = {}
    for quote in bundle.spec.quotes:
        answer = await agent.run(ClausePacket.model_validate(bundle.clause_packet(quote)))
        clauses, sha = bundle.contract(quote)
        quotes[quote.id] = {"legal_version": bundle.legal.version, "contract_sha256": sha,
                            "judgements": [j.model_dump() for j in answer.judgements]}
        model_reqs = [r for r in bundle.legal.requirements if r.decided_by == "model"]
        for line in admit_judgements(model_reqs, clauses, quote.contract.complete, quotes[quote.id]["judgements"]):
            print(f"{quote.id} {line['requirement_id']}: {line['status']} ({line['reason_code']})")
    frozen = {"generated_by": f"{provider} via scripts/freeze_clause_judgements.py",
              "generated_at": datetime.now(UTC).strftime("%Y-%m-%d"), "quotes": quotes}
    target: Path = bundle.base / bundle.spec.judgements
    target.write_text(HEADER + yaml.safe_dump(frozen, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
    print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
