"""Mark legacy informational BridgeFlow events as skippable by native readers.

Run --apply only while BridgeFlow is stopped. Originals are backed up outside
sessions; no native event, payload, sequence, timestamp or model usage is changed.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path

INFORMATIONAL = frozenset({"bridgeflow/review", "bridgeflow/approval-note"})


def repair(root: Path, *, apply: bool = False) -> dict[str, int | str]:
    files = events = 0
    backup_root: Path | None = None
    for path in root.rglob("session.jsonl"):
        before = path.stat()
        original = path.read_bytes()
        lines = original.splitlines(keepends=True)
        changed = 0
        for index, line in enumerate(lines):
            event = json.loads(line)
            if event.get("type") in INFORMATIONAL and event.get("ignorable") is not True:
                event["ignorable"] = True
                lines[index] = (json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
                changed += 1
        if not changed:
            continue
        files += 1
        events += changed
        if not apply:
            continue
        if backup_root is None:
            folder = root.parent / "session-metadata-backups"
            folder.mkdir(exist_ok=True)
            backup_root = Path(tempfile.mkdtemp(prefix="repair-", dir=folder))
        backup = backup_root / path.relative_to(root)
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_bytes(original)
        shutil.copystat(path, backup)
        # Never race an observed write; the operator must stop the service first.
        current = path.stat()
        if (before.st_mtime_ns, before.st_size) != (current.st_mtime_ns, current.st_size):
            raise RuntimeError("Session changed during repair; stop BridgeFlow before applying")
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(b"".join(lines))
            stream.flush()
            os.fsync(stream.fileno())
        try:
            temporary.chmod(before.st_mode & 0o777)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    return {"files": files, "events": events, "backup": str(backup_root or ""), "mode": "apply" if apply else "check"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--apply", action="store_true", help="Apply with backups; stop BridgeFlow first")
    args = parser.parse_args()
    if not args.root.is_dir():
        parser.error("Session root does not exist")
    print(json.dumps(repair(args.root, apply=args.apply)))


if __name__ == "__main__":
    main()
