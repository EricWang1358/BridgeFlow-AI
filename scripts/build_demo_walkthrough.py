"""Build a local, credential-free entry point over the retained demo evidence."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build() -> None:
    folder = ROOT / 'demo-walkthrough'
    folder.mkdir(exist_ok=True)
    # One physical copy of each run; retention applies to every linked screenshot.
    for name, target in {'data': '../data/business_demo', 'evidence': '../docs/evidence/business-mvp'}.items():
        path = folder / name
        if not path.is_symlink():
            path.symlink_to(target, target_is_directory=True)
    files = []
    for scenario in ['risk', 'balanced']:
        for role in ['production', 'procurement', 'finance', 'marketing']:
            files.append({'path': f'data/{scenario}/{role}.csv', 'purpose': f'Upload to {role}; month 2025-11', 'model_input': False})
    files.extend([
        {'path': 'data/dictionary.yaml', 'purpose': 'Frozen business rules; inspect before presenting', 'model_input': 'bounded context only'},
        {'path': 'data/expected.json', 'purpose': 'Independent answer key; NEVER upload or feed to a model', 'model_input': False},
    ])
    for scenario in ['risk', 'balanced', 'step-limit', 'approval']:
        root = ROOT / 'docs/evidence/business-mvp' / scenario
        if root.exists():
            for path in sorted(root.iterdir()):
                if path.is_file() and path.suffix in {'.json', '.png'}:
                    files.append({'path': f'evidence/{scenario}/{path.name}', 'purpose': 'Retained measured evidence; not a live state', 'model_input': False})
    (folder / 'files.json').write_text(json.dumps({'month': '2025-11', 'retention': '2 complete runs per scenario; aliases point to latest', 'files': files}, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    build()
