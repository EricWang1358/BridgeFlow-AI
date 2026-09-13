"""Confirmed mappings, remembered across months.

The promise in `docs/01` is that month two costs a fraction of month one. That only
holds if a human confirmation survives the run it was made in — otherwise every month
asks the same questions and the human learns that confirming is pointless.

A confirmation is not a cache. It is a decision somebody made and can be held to, so
it records who, when, and against what evidence, and it is versioned: `docs/07` FR 11
forbids a mapping change from silently recomputing an already-published batch, and
that requires knowing which version a batch was computed under.
"""

from __future__ import annotations

import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from bridgeflow.config import REPO_ROOT, settings
from bridgeflow.schemas import Link


class ConfirmedMapping(BaseModel):
    """One link a person accepted or rejected, and the trail behind it."""

    source: str
    target: str
    relation: str
    #: True when accepted. A rejection is worth remembering too: re-asking a question
    #: somebody already said no to is how a review queue loses its reader.
    accepted: bool
    confirmed_by: str
    confirmed_at: str
    #: What was shown at the time. If the evidence changes, the decision is stale and
    #: should be asked again rather than silently reused.
    evidence: str = ""
    #: The period the confirmation was made in, so its age is visible.
    period: str = ""
    #: The person who allowed the call that wrote this, joined from the approval log
    #: by tool-call id. `confirmed_by` is the agent that ran; this is the human who
    #: let it. Empty when the record predates the console (#30) or the join failed —
    #: which is itself worth seeing, rather than filling in a plausible name.
    authorised_by: str = ""
    #: The facts the decision rested on, normalised (see `evidence_facts`). Stored so an
    #: auditor can see exactly what "the same evidence" was compared against.
    evidence_facts: list[str] = Field(default_factory=list)

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.source, self.target, self.relation)


_FACT = re.compile(r"[a-z0-9][a-z0-9_.:/-]*")
#: Connective wording that may change without changing what the evidence says.
_WORDING = frozenset({"row", "rows", "in", "on", "at", "of", "the", "and", "from", "per", "sheet", "see", "for", "a", "an"})


def evidence_facts(text: str) -> list[str]:
    """What evidence asserts, independent of how the sentence is phrased (#82).

    The rule is deliberately simple enough to audit: identifiers, periods, row numbers
    and department names are facts; connective words and word order are wording. The
    same facts in another sentence still match; any fact added, removed or changed —
    another period, another row, another department — makes the decision stale.
    """
    tokens = {t.strip(".:/-") for t in _FACT.findall(text.casefold())}
    return sorted(t for t in tokens if t and t not in _WORDING)


class MappingMemory(BaseModel):
    version: str = ""
    confirmations: list[ConfirmedMapping] = Field(default_factory=list)

    def find(self, link: Link) -> ConfirmedMapping | None:
        wanted = (link.source, link.target, link.relation)
        return next((c for c in self.confirmations if c.key == wanted), None)


def _path() -> Path:
    configured = Path(settings.mapping_memory_path)
    return configured if configured.is_absolute() else REPO_ROOT / configured


def load() -> MappingMemory:
    path = _path()
    if not path.is_file():
        return MappingMemory()
    return MappingMemory.model_validate_json(path.read_text(encoding="utf-8"))


def confirm(
    link: Link, *, by: str, accepted: bool, period: str = "", authorised_by: str = ""
) -> MappingMemory:
    """Record a decision, replacing any earlier one for the same link.

    Replacing rather than appending because the current answer is what matters to the
    next run; the history lives in the versioned files, which is where an auditor
    would look anyway.
    """
    memory = load()
    entry = ConfirmedMapping(
        source=link.source,
        target=link.target,
        relation=link.relation,
        accepted=accepted,
        confirmed_by=by,
        confirmed_at=datetime.now(UTC).isoformat(),
        evidence=link.justification,
        period=period,
        authorised_by=authorised_by,
        evidence_facts=evidence_facts(link.justification),
    )
    memory.confirmations = [c for c in memory.confirmations if c.key != entry.key] + [entry]
    memory.version = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    _save(memory)
    return memory


def apply(links: list[Link], memory: MappingMemory | None = None) -> tuple[list[Link], list[Link]]:
    """Split candidates into those a person has already settled and those still open.

    A confirmation whose evidence no longer matches is treated as open again. The
    decision was made about something specific, and quietly reusing it against
    different evidence is how a stale mapping outlives the reason for it.
    """
    memory = memory or load()
    settled: list[Link] = []
    open_questions: list[Link] = []

    for link in links:
        confirmation = memory.find(link)
        if confirmation is None:
            open_questions.append(link)
            continue
        recorded = confirmation.evidence_facts or evidence_facts(confirmation.evidence)
        if confirmation.evidence and recorded != evidence_facts(link.justification):
            open_questions.append(
                link.model_copy(
                    update={
                        "justification": (
                            f"{link.justification} — previously confirmed by "
                            f"{confirmation.confirmed_by} against different evidence, "
                            "so it is being asked again"
                        )
                    }
                )
            )
            continue
        if not confirmation.accepted:
            continue  # somebody said no; do not resurrect it
        settled.append(
            link.model_copy(
                update={
                    "confidence": 1.0,
                    "status": "declared",
                    "justification": (
                        f"confirmed by {confirmation.confirmed_by} "
                        f"on {confirmation.confirmed_at[:10]}"
                    ),
                }
            )
        )
    return settled, open_questions


def _save(memory: MappingMemory) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = memory.model_dump_json(indent=2)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
    ) as handle:
        handle.write(payload)
        temporary = Path(handle.name)
    temporary.replace(path)
    # A version alongside, for the same reason results are versioned: a batch
    # computed under an older set of mappings must remain reproducible.
    versions = path.parent / "versions"
    versions.mkdir(exist_ok=True)
    (versions / f"mappings--{memory.version}.json").write_text(payload, encoding="utf-8")
