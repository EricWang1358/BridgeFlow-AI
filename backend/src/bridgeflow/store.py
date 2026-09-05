"""Where a pipeline result lives after the request that produced it.

It used to live in a module-level dict, which is wrong in two ways that both bite
during a demo: it is lost on restart, and with more than one worker the `/quote`
call lands on a process that never saw the analysis and 404s unpredictably.

A JSON file per period under `data/outputs/` is enough for the hackathon. What it
buys beyond survival is the thing #12 was really about: a result that exists on disk
can be read back, compared against last month's, and cited — which is what cross-month
memory and an audit trail both need (#29).
"""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from bridgeflow.config import REPO_ROOT, settings
from bridgeflow.schemas import PipelineResult


def _root() -> Path:
    configured = Path(settings.result_store_path)
    return configured if configured.is_absolute() else REPO_ROOT / configured


def _path(period: str) -> Path:
    # Periods come from a form field, so they are not trusted as a path segment.
    safe = "".join(ch for ch in period if ch.isalnum() or ch in "-_")
    if not safe:
        raise ValueError(f"unusable period {period!r}")
    return _root() / f"{safe}.json"


def save(result: PipelineResult) -> Path:
    """Write one period's result, atomically.

    Atomically because a half-written file read by the next request is worse than a
    missing one: it fails somewhere downstream with a schema error rather than an
    honest "not analysed yet".
    """
    path = _path(result.period)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = result.model_dump(mode="json")
    payload["_saved_at"] = datetime.now(UTC).isoformat()

    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        temporary = Path(handle.name)
    temporary.replace(path)
    return path


def load(period: str) -> PipelineResult | None:
    """Read one period's result, or None if it was never analysed."""
    path = _path(period)
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.pop("_saved_at", None)
    return PipelineResult.model_validate(payload)


def periods() -> list[str]:
    """Every period that has been analysed, oldest first.

    Cross-month work starts here: knowing what came before is the difference between
    "no change" and "no comparison".
    """
    root = _root()
    if not root.is_dir():
        return []
    return sorted(path.stem for path in root.glob("*.json"))


def previous(period: str) -> PipelineResult | None:
    """The most recent analysed period before `period`."""
    earlier = [p for p in periods() if p < period]
    return load(earlier[-1]) if earlier else None
