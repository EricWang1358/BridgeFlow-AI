"""Manual retention of complete root-session families, never individual children."""
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path


def catalogue(root: Path) -> dict[str, dict]:
    sessions = {}
    for path in root.rglob('session.jsonl'):
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            continue
        with path.open(encoding='utf-8') as stream:
            try:
                header = json.loads(stream.readline())
            except (ValueError, OSError):
                continue
        if header.get('type') == 'session' and header.get('id'):
            sessions[header['id']] = {'path': path, 'header': header, 'mtime': path.stat().st_mtime_ns}
    return sessions


def families(sessions: dict) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for key in sessions:
        current, seen = key, set()
        while current not in seen:
            seen.add(current)
            parent = sessions[current]['header'].get('parentSession')
            if parent not in sessions:
                break
            current = parent
        groups.setdefault(current, []).append(key)
    return groups


def prune(root: Path, keep: int, dry_run: bool = False) -> list[str]:
    if keep < 1:
        raise ValueError('keep must be positive')
    sessions = catalogue(root)
    groups = families(sessions)
    ordered = sorted(groups, key=lambda key: max(sessions[k]['mtime'] for k in groups[key]), reverse=True)
    removed = []
    for key in ordered[keep:]:
        for member in groups[key]:
            folder = sessions[member]['path'].parent
            if folder == root or folder.is_symlink() or not folder.resolve().is_relative_to(root.resolve()):
                raise ValueError('Refusing unsafe session directory')
            # Never erase a directory containing another session's files.
            if any(p != sessions[member]['path'] for p in folder.rglob('session.jsonl')):
                raise ValueError('Nested session directory requires manual inspection')
            removed.append(member)
            if not dry_run:
                shutil.rmtree(folder)
    return removed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run manually with DSH stopped. Keep newest root sessions and all their children.')
    parser.add_argument('--root', type=Path, default=Path(os.environ.get('DSH_HOME', '../.dsh-bridgeflow')) / 'sessions')
    parser.add_argument('--keep', type=int, default=2)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    print(json.dumps({'dry_run': args.dry_run, 'removed_sessions': prune(args.root, args.keep, args.dry_run)}, ensure_ascii=False))
