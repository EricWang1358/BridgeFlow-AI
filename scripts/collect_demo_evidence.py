"""Copy synthetic demo evidence without credentials, prompts or reasoning traces."""
from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from session_retention import catalogue, families


def collect(source: Path, destination: Path, keep: int = 2) -> None:
    if keep < 1:
        raise ValueError('keep must be positive')
    index = catalogue(source / 'dsh/sessions')
    report_path = source / 'report.json'
    if report_path.exists():
        report = json.loads(report_path.read_text())
        chosen = [report['parent_session_id'], *[r['session_id'] for r in report['roles'] if r.get('session_id')]]
    else:
        groups = families(index)
        parent = max(groups, key=lambda k: max(index[s]['mtime'] for s in groups[k]))
        chosen = [parent]
    if len(set(chosen)) != len(chosen) or any(key not in index for key in chosen):
        raise ValueError('Report session identities do not match evidence corpus')
    if any(index[key]['header'].get('parentSession') != chosen[0] for key in chosen[1:]):
        raise ValueError('Child belongs to a different captain')
    sessions = []
    for key in chosen:
        path = index[key]['path']
        events = [json.loads(line) for line in path.read_text().splitlines()]
        audit = []
        for event in events:
            kind, data = event["type"], event.get("data", {})
            selected = None
            if kind == "request/header":
                selected = {"tools": [tool["name"] for tool in data["header"].get("tools", [])]}
            elif kind == "assistant/message":
                message = data["message"]
                selected = {"turn": data.get("turn"), "step": data.get("step"), "usage": data.get("usage"),
                    "source": message.get("source"), "text": [b["text"] for b in message["content"] if b["type"] == "text"]}
            elif kind == "tool/call":
                selected = {key: data[key] for key in ("turn", "step", "name", "callId") if key in data}
            elif kind == "tool/result":
                selected = {"error": any(block.get("isError", False) for block in data.get("message", {}).get("content", [])), "source": data.get("message", {}).get("source")}
            elif kind in ("turn/end", "approval/asked", "approval/decided", "bridgeflow/approval-note"):
                selected = data
            if selected is not None:
                audit.append({"type": kind, "time": event["time"], "data": selected})
        # The first JSONL record is the official immutable session header.
        header = events[0]
        sessions.append({"session_directory": path.parent.name,
            "header": {key: header[key] for key in ("id", "origin", "parentSession", "label", "createdAt") if key in header},
            "events": audit})
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / 'runs'
    archive.mkdir(exist_ok=True)
    legacy = [p for p in destination.iterdir() if p.is_file() and not p.is_symlink() and p.name != 'manifest.json']
    if legacy:
        old = archive / 'legacy'
        old.mkdir(exist_ok=True)
        stamp = max(p.stat().st_mtime for p in legacy)
        for path in legacy:
            shutil.move(path, old / path.name)
        import os
        os.utime(old, (stamp, stamp))
    run = archive / str(time.time_ns())
    run.mkdir()
    latest = destination
    destination = run
    for name in ("measurement.json", "acceptance.json", "chain-audit.json", "report.json", "approval-events.json", "business-review.png", "business-upload.png", "rejection-note.png", "native-approval.png", "business-state.png", "business-state-dark.png", "business-state-en.png", "department-files.png", "native-spawn.png"):
        path = source / name
        if path.is_file():
            shutil.copyfile(path, destination / name)
    (destination / "session-audit.json").write_text(json.dumps(sessions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    retained = sorted(archive.iterdir(), key=lambda p: p.stat().st_mtime_ns, reverse=True)
    for old in retained[keep:]:
        shutil.rmtree(old)
    for path in latest.iterdir():
        if path.is_symlink():
            path.unlink()
    for path in destination.iterdir():
        (latest / path.name).symlink_to(path.relative_to(latest))
    (latest / 'manifest.json').write_text(json.dumps({'keep': keep, 'runs': [p.name for p in retained[:keep]], 'latest': destination.name}, indent=2) + '\n')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--keep", type=int, default=2)
    args = parser.parse_args()
    collect(args.source, args.destination, args.keep)
