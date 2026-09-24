"""Which batch is a period's, without parsing every batch file (E13-UC02).

A batch file holds its cleaned rows, so a batch can be tens of megabytes; finding "the
2024-06 batch" by reading them all would cost the same as re-importing. Import therefore
writes a small index entry per batch, and lookup reads only the index.

The index is a cache, not a source of truth: if it is missing or has fewer entries than
there are batches (older data, a restored directory), it is rebuilt once from the batch
files and written back. Rebuilding is the expensive path and says so in the log.
"""

from __future__ import annotations

import json
from typing import Any

from bridgeflow.store import _root, _write

INDEX = "index.json"


def _folder():
    return _root() / "batches"


def _index_path():
    return _folder() / INDEX


def entry(batch_id: str, snapshot: Any) -> dict:
    """Small lookup record for a batch's period, visibility and data series."""
    return {"batch_id": batch_id, "period": snapshot.period,
            "owner": getattr(snapshot, "owner", "") or "",
            "departments": sorted({t.department for t in snapshot.clean_tables}),
            "derived_from": getattr(snapshot, "derived_from", None),
            "demo_case": getattr(snapshot, "demo_case", None)}


def record(batch_id: str, snapshot: Any) -> None:
    """Add one batch to the index. Called by import; never by a read path."""
    index = _read()
    index[batch_id] = entry(batch_id, snapshot)
    _write(_index_path(), index)


def _read() -> dict[str, dict]:
    path = _index_path()
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _rebuild() -> dict[str, dict]:
    from bridgeflow.api.batches import BatchSnapshot  # local: batches imports this module

    index = {}
    for path in sorted(_folder().glob("*.json")):
        if path.name == INDEX:
            continue
        try:
            snapshot = BatchSnapshot.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError):
            continue
        index[path.stem] = entry(path.stem, snapshot)
    _write(_index_path(), index)
    return index


def _current() -> dict[str, dict]:
    folder = _folder()
    if not folder.is_dir():
        return {}
    index = _read()
    batches = {p.stem for p in folder.glob("*.json") if p.name != INDEX}
    if not batches <= set(index):
        index = _rebuild()
    return index


def successors(batch_id: str) -> list[str]:
    """Batches derived from this one (E14-UC04).

    Read forwards from the index rather than written back into the frozen batch: a corrected
    batch must not change the file it corrects, not even its lineage field.
    """
    return sorted(entry["batch_id"] for entry in _current().values() if entry.get("derived_from") == batch_id)


def batches_for(period: str) -> list[dict]:
    """Every indexed batch of that period, newest import first."""
    found = [e for e in _current().values() if e.get("period") == period]
    folder = _folder()

    def imported_at(item: dict) -> int:
        path = folder / f"{item['batch_id']}.json"
        return path.stat().st_mtime_ns if path.is_file() else 0

    return sorted(found, key=imported_at, reverse=True)


def demo_case(item: dict) -> str:
    """The indexed sample marker, with a fallback for indexes written before it existed."""
    if "demo_case" in item:
        return str(item["demo_case"] or "")
    from bridgeflow.api.batches import load_batch  # local: batches imports this module
    return str(load_batch(item["batch_id"]).demo_case or "")


def same_series(item: dict, current_demo_case: str | None, period: str) -> bool:
    """Keep synthetic supplier history apart from uploaded business months."""
    candidate = demo_case(item)
    return candidate == f"demo-history-{period}" if current_demo_case else not candidate


def latest_for(period: str, visible) -> dict | None:
    """The newest batch of that period this caller may see.

    Several batches for one month are corrections of each other (a re-import, a
    single-department replacement), so the newest visible one in the caller's series is
    the base; earlier ones stay addressable by id. Recorded in docs/requirements/13 D1.
    """
    for item in batches_for(period):
        if visible(item):
            return item
    return None
