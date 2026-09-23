"""The decision journal: what the system was asked, what it answered, and why.

Every refusal in this product is already an `HTTPException` carrying the sentence a person
should read — "This file reports 2024-06, not 2024-07", "A decision needs a source", "no base
period". That is the whole observability problem solved once, in the wrong shape: those
sentences reach one caller and then vanish.

So the journal is written in **one** place, as middleware, rather than as logging calls
sprinkled through forty modules. One seam means whole-system coverage that cannot drift out
of date when somebody adds an endpoint, and it means a refusal is recorded in its own words
rather than in a paraphrase somebody wrote at the call site.

Three bounds, the same ones the tools live under:

- **No rows, no cell values.** An entry holds ids, counts, versions and the refusal's own
  sentence. What is being decided about is named by reference, never copied.
- **No identity beyond what an operator needs.** The actor is recorded as a kind plus a short
  digest of the subject; the approval ledger is where a real identity is kept and audited.
- **Bounded.** One file per day, an entry capped in size, reads capped in count. A trace that
  can grow without limit is a trace nobody keeps.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from bridgeflow.store import _root

#: Paths carrying an id or a name are folded back to their route shape, so the journal groups
#: by decision ("read a batch") rather than by instance ("read this batch").
_SHAPES = (
    (re.compile(r"/[a-f0-9]{32}\b"), "/{id}"),
    (re.compile(r"/\d{4}-\d{2}\b"), "/{period}"),
)
MAX_REASON = 300
#: What a request may add to its own entry. Anything else is dropped: the journal is a record
#: of decisions, not a place to smuggle data past the tool contract.
FACT_KEYS = ("batch_id", "period", "report_id", "declaration", "counts", "outcome_detail",
             # The agent's own identifiers, sent by the tool layer: the call, the model-requested
             # call that owns the whole tree (one "run"), which agent asked, and which tool.
             "call_id", "run", "agent", "tool",
             # The model step that issued the call and what it cost, as input/output/total.
             "step", "tokens")


def _folder():
    return _root() / "journal"


def _path(day: str):
    return _folder() / f"{day}.jsonl"


def new_trace() -> str:
    return uuid.uuid4().hex[:16]


def actor_of(subject: str | None, *, host: bool) -> str:
    """Who asked, at the resolution an operator needs: a kind, plus a stable short digest."""
    if subject:
        return f"user:{hashlib.sha256(subject.encode()).hexdigest()[:8]}"
    return "host" if host else "anonymous"


def shape(path: str) -> str:
    for pattern, replacement in _SHAPES:
        path = pattern.sub(replacement, path)
    return path


#: The headers the tool layer sends, mapped to the facts they become. Read here rather than
#: parsed out of bodies: a header costs nothing and cannot smuggle a data row.
TRACE_HEADERS = {"x-bridgeflow-call": "call_id", "x-bridgeflow-root": "run",
                 "x-bridgeflow-agent": "agent", "x-bridgeflow-tool": "tool",
                 # A tool's subject lives in its body, which this seam never reads; the tool
                 # layer therefore states it, and only these two keys are accepted.
                 "x-bridgeflow-batch": "batch_id", "x-bridgeflow-period": "period",
                 "x-bridgeflow-step": "step", "x-bridgeflow-tokens": "tokens"}

#: Token usage is three counts and nothing else; any other shape is dropped.
TOKENS = re.compile(r"^\d{1,9}/\d{1,9}/\d{1,9}$")


def trace_facts(headers) -> dict[str, str]:
    found = {}
    for header, key in TRACE_HEADERS.items():
        value = headers.get(header)
        if value:
            found[key] = str(value)[:120]
    if "tokens" in found and not TOKENS.match(found["tokens"]):
        del found["tokens"]
    return found


def _tokens(steps: list[dict[str, Any]]) -> dict[str, int]:
    """Sum each model step once: several calls from one message share its usage."""
    seen: dict[tuple[str, str], str] = {}
    for s in steps:
        facts = s.get("facts") or {}
        if facts.get("tokens"):
            seen[(facts.get("agent", ""), facts.get("step") or facts.get("call_id", ""))] = facts["tokens"]
    total = {"input": 0, "output": 0, "total": 0, "model_steps": len(seen)}
    for value in seen.values():
        i, o, t = (int(x) for x in value.split("/"))
        total["input"] += i
        total["output"] += o
        total["total"] += t
    return total


def subject_of(path: str) -> dict[str, str]:
    """What the decision was about, read from the path the way the shaping reads it.

    An operator asks "what happened to this batch", and a batch id is in the path far more
    often than in the query string; taking it here means no handler has to remember to.
    """
    found: dict[str, str] = {}
    batch = re.search(r"/([a-f0-9]{32})\b", path)
    if batch:
        found["batch_id"] = batch.group(1)
    period = re.search(r"/(\d{4}-\d{2})\b", path)
    if period:
        found["period"] = period.group(1)
    return found


def record(entry: dict[str, Any]) -> None:
    """Append one decision. Never raises: a journal that can break a request is not a journal."""
    try:
        line = json.dumps(entry, ensure_ascii=False, default=str)
        if len(line) > 4096:  # a pathological entry is truncated, never dropped silently
            entry = {**entry, "reason": str(entry.get("reason", ""))[:MAX_REASON], "facts": {"truncated": True}}
            line = json.dumps(entry, ensure_ascii=False, default=str)
        folder = _folder()
        folder.mkdir(parents=True, exist_ok=True)
        with (folder / f"{entry['at'][:10]}.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except (OSError, UnicodeError, TypeError, ValueError):
        return


def entry(*, trace: str, surface: str, method: str, status: int, started: float,
          actor: str, reason: str = "", facts: dict[str, Any] | None = None) -> dict[str, Any]:
    """One decision, in the shape the studio reads back."""
    outcome = ("refused" if status >= 400 else
               "wrote" if method in ("POST", "PUT", "PATCH", "DELETE") else "served")
    kept = {k: v for k, v in (facts or {}).items() if k in FACT_KEYS}
    return {"trace": trace, "at": datetime.now(UTC).isoformat(), "surface": surface, "method": method,
            "status": status, "outcome": outcome, "ms": round((time.perf_counter() - started) * 1000, 1),
            "actor": actor, "reason": str(reason)[:MAX_REASON], "facts": kept}


def read(*, day: str = "", limit: int = 200, outcome: str = "", surface: str = "",
         batch_id: str = "") -> dict[str, Any]:
    """The newest entries first, with the counts the studio shows above them."""
    day = day or datetime.now(UTC).strftime("%Y-%m-%d")
    path = _path(day)
    entries: list[dict[str, Any]] = []
    if path.is_file():
        try:
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except (OSError, UnicodeError):
            entries = []
    entries.reverse()
    by_outcome: dict[str, int] = {}
    for item in entries:
        by_outcome[item.get("outcome", "?")] = by_outcome.get(item.get("outcome", "?"), 0) + 1
    shown = [item for item in entries
             if (not outcome or item.get("outcome") == outcome)
             and (not surface or surface in item.get("surface", ""))
             and (not batch_id or (item.get("facts") or {}).get("batch_id") == batch_id)]
    durations = sorted(item.get("ms", 0) for item in entries)
    return {"day": day, "total": len(entries), "by_outcome": by_outcome,
            "slowest_ms": durations[-1] if durations else 0,
            "median_ms": durations[len(durations) // 2] if durations else 0,
            "refusal_reasons": _top_reasons(entries),
            "entries": shown[:limit], "days": _days()}


def _top_reasons(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Which refusals happen, and how often. The product's honesty, counted."""
    counts: dict[str, int] = {}
    for item in entries:
        if item.get("outcome") == "refused" and item.get("reason"):
            counts[item["reason"]] = counts.get(item["reason"], 0) + 1
    ranked = sorted(counts.items(), key=lambda pair: -pair[1])[:8]
    return [{"reason": reason, "count": count} for reason, count in ranked]


def _days() -> list[str]:
    folder = _folder()
    if not folder.is_dir():
        return []
    return sorted((p.stem for p in folder.glob("*.jsonl")), reverse=True)[:14]


def runs(*, day: str = "", limit: int = 20) -> dict[str, Any]:
    """The journal grouped into agent runs.

    A run is one model-requested call and everything underneath it: the captain's step and
    every department subagent's tool call carry the same root, so grouping by it is what a
    person means by "one run". Requests with no run id are the browser's own reads and are
    left out — this view answers "what did the agent do", not "what did somebody look at".
    """
    day = day or datetime.now(UTC).strftime("%Y-%m-%d")
    read_back = read(day=day, limit=10_000)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in read_back["entries"]:
        run = (item.get("facts") or {}).get("run")
        if run:
            grouped.setdefault(run, []).append(item)
    found = []
    for run, steps in grouped.items():
        ordered = sorted(steps, key=lambda s: s.get("at", ""))
        agents = list(dict.fromkeys(s.get("facts", {}).get("agent", "") for s in ordered if s.get("facts", {}).get("agent")))
        refusals = [s for s in ordered if s.get("outcome") == "refused"]
        found.append({
            "run": run, "started_at": ordered[0].get("at", ""), "ended_at": ordered[-1].get("at", ""),
            "steps": len(ordered), "agents": agents, "refused": len(refusals),
            "ms": round(sum(s.get("ms", 0) for s in ordered), 1),
            "tokens": _tokens(ordered),
            "batch_id": next((s.get("facts", {}).get("batch_id", "") for s in ordered
                              if s.get("facts", {}).get("batch_id")), ""),
            "tools": list(dict.fromkeys(s.get("facts", {}).get("tool", "") or s.get("surface", "") for s in ordered)),
            "timeline": [{"at": s.get("at", ""), "agent": s.get("facts", {}).get("agent", ""),
                          "tool": s.get("facts", {}).get("tool", "") or s.get("surface", ""),
                          "outcome": s.get("outcome", ""), "ms": s.get("ms", 0),
                          "reason": s.get("reason", ""), "trace": s.get("trace", ""),
                          "tokens": s.get("facts", {}).get("tokens", "")} for s in ordered],
        })
    found.sort(key=lambda r: r["started_at"], reverse=True)
    return {"day": day, "total": len(found), "runs": found[:limit], "days": read_back["days"]}


def prune(keep_days: int = 14) -> int:
    """Keep the journal bounded. Returns how many files were removed."""
    folder = _folder()
    if not folder.is_dir():
        return 0
    files = sorted(folder.glob("*.jsonl"), reverse=True)
    removed = 0
    for path in files[keep_days:]:
        try:
            os.remove(path)
            removed += 1
        except OSError:
            continue
    return removed
