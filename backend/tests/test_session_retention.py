"""Retention must never mix captains or lose surviving child audit trails."""
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / 'scripts'

def module(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f'{name}.py')
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value

retention = module('session_retention')
evidence = module('collect_demo_evidence')


def session(root, name, parent=None, mtime=1, malformed_tail=False):
    path = root / 'workspace' / name / 'session.jsonl'
    path.parent.mkdir(parents=True)
    header = {'type': 'session', 'id': name, **({'parentSession': parent, 'origin': 'subagent'} if parent else {})}
    path.write_text(json.dumps(header) + '\n' + ('not-json\n' if malformed_tail else ''))
    os.utime(path, (mtime, mtime))
    return path


def test_prune_preserves_whole_families_and_dry_run(tmp_path):
    for i in range(3):
        session(tmp_path, f'parent-{i}', mtime=i + 1)
        for j in range(4):
            session(tmp_path, f'child-{i}-{j}', f'parent-{i}', i + 1)
    expected = {'parent-0', *[f'child-0-{j}' for j in range(4)]}
    assert set(retention.prune(tmp_path, 2, dry_run=True)) == expected
    assert len(retention.catalogue(tmp_path)) == 15
    assert set(retention.prune(tmp_path, 2)) == expected
    assert len(retention.catalogue(tmp_path)) == 10
    assert all(len(group) == 5 for group in retention.families(retention.catalogue(tmp_path)).values())


def test_active_child_mtime_keeps_older_parent(tmp_path):
    session(tmp_path, 'old', mtime=1)
    session(tmp_path, 'old-child', 'old', 99)
    session(tmp_path, 'new', mtime=3)
    assert retention.prune(tmp_path, 1) == ['new']


def test_collect_reads_only_report_family_and_keeps_two_runs(tmp_path):
    source, target = tmp_path / 'source', tmp_path / 'target'
    root = source / 'dsh/sessions'
    session(root, 'captain')
    for i in range(4):
        session(root, f'child-{i}', 'captain')
    # Discovery reads only a header; unrelated malformed/private bodies are not consumed.
    session(root, 'unrelated', mtime=999, malformed_tail=True)
    (source / 'report.json').write_text(json.dumps({'parent_session_id': 'captain', 'roles': [{'session_id': f'child-{i}'} for i in range(4)]}))
    (source / 'acceptance.json').write_text(json.dumps({'passed': False}))
    (source / 'business-state.png').write_bytes(b'synthetic test screenshot')
    for _ in range(3):
        evidence.collect(source, target, keep=2)
    assert len(list((target / 'runs').iterdir())) == 2
    audit = json.loads((target / 'session-audit.json').read_text())
    assert len(audit) == 5
    assert {x['header']['id'] for x in audit} == {'captain', *[f'child-{i}' for i in range(4)]}
    assert json.loads((target / 'acceptance.json').read_text()) == {'passed': False}
    assert (target / 'business-state.png').is_symlink()
    assert len(list((target / 'runs').rglob('business-state.png'))) == 2
    assert json.loads((target / 'manifest.json').read_text())['keep'] == 2


def test_collect_rejects_cross_parent_before_touching_destination(tmp_path):
    source, target = tmp_path / 'source', tmp_path / 'target'
    session(source / 'dsh/sessions', 'captain')
    session(source / 'dsh/sessions', 'child', 'other')
    (source / 'report.json').write_text(json.dumps({'parent_session_id': 'captain', 'roles': [{'session_id': 'child'}]}))
    with pytest.raises(ValueError, match='different captain'):
        evidence.collect(source, target)
    assert not target.exists()


def test_prune_rejects_zero_and_does_not_follow_symlinks(tmp_path):
    outside = tmp_path / 'outside'
    path = session(outside, 'outside')
    root = tmp_path / 'sessions'
    root.mkdir()
    (root / 'external').symlink_to(path.parent, target_is_directory=True)
    with pytest.raises(ValueError):
        retention.prune(root, 0)
    assert retention.prune(root, 2) == []
    assert path.exists()
