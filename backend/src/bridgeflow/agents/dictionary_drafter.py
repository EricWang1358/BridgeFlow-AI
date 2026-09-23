"""The dictionary drafting agent (#205, E05-UC07).

Its input is a batch's column statistics and nothing else — no cell value, no
header-text reasoning it was not given. Its output is a *proposal*: the host-side
filter in `dictionary_draft.admit_proposals` drops anything without evidence, any
column the batch does not carry, and any role that does not parse, so a bad model
answer degrades to a shorter draft, never to an unevidenced declaration.

The mock provider returns an empty proposal; that is honest — mock output is not
evidence of drafting quality (E05-UC07 AC-4), and the OA-dictionary transcription
path is the reliable road when the business has its spreadsheet.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from bridgeflow.agents.base import Agent
from bridgeflow.llm.base import Message
from bridgeflow.profiling import BatchProfile


class ProposedEntry(BaseModel):
    department: str
    column: str
    #: `entity:<kind>` / `measure:<name>` / `period` / `currency`.
    role: str
    #: The statistics the proposal rests on, in the proposer's own words.
    evidence: str
    uncertainty: str = ""


class DraftProposal(BaseModel):
    entries: list[ProposedEntry] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class DictionaryDraftAgent(Agent[BatchProfile, DraftProposal]):
    slug = "dictionary_drafter"

    system_prompt = (
        "You draft field-dictionary declarations for cross-department spreadsheets. "
        "You are given column statistics only: types, fill rates, uniqueness, and how "
        "much of one column's distinct values another department's column also has. "
        "No cell contents exist in your input, and you must not invent any. "
        "Propose declarations of the form department + column + role, where role is "
        "entity:<kind> for a join key (string columns whose values overlap heavily "
        "across departments are the strongest candidates), measure:<name> for a "
        "numeric column that can be aggregated, period for the report month, or "
        "currency. Every entry must cite the statistics it rests on in `evidence`; "
        "an entry you cannot support with the given statistics must not be proposed. "
        "When a judgement is uncertain, say so in `uncertainty` rather than lowering "
        "the evidence. Do not propose cross-department relations. Propose at most one "
        "role per column."
    )

    async def run(self, payload: BatchProfile) -> DraftProposal:
        response = await self.llm.complete(
            system=self.system_prompt,
            messages=[Message(role="user", content=payload.model_dump_json())],
            schema=DraftProposal,
        )
        if isinstance(response.parsed, DraftProposal):
            return response.parsed
        return DraftProposal.model_validate_json(response.text)
