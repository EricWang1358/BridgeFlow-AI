"""Who may see which departments: human-preset in access-control.yaml.

Same rule as the field dictionary — the mapping is declared by people, never
inferred. A user the file does not list sees nothing; a missing or invalid file
fails loudly ("not configured"), never falls back to guessing.
"""

from __future__ import annotations

from pathlib import Path
from typing import get_args

import yaml
from fastapi import HTTPException

from bridgeflow.config import REPO_ROOT, settings
from bridgeflow.schemas import Department

KNOWN_DEPARTMENTS = set(get_args(Department))


def access_path() -> Path:
    path = Path(settings.access_control_path)
    return path if path.is_absolute() else REPO_ROOT / path


def _entry_for(union_id: str) -> dict:
    """Validate the access file and return one declared user entry; missing means no grants."""
    try:
        raw = yaml.safe_load(access_path().read_text(encoding="utf-8")) or {}
        users = raw.get("users") or {}
        if not isinstance(users, dict):
            raise TypeError("'users' must map union_id to an entry")
        for uid, entry in users.items():
            if not isinstance(entry, dict):
                raise TypeError(f"user {uid!r} must be a mapping with departments")
            for field in ("departments", "workflow_departments", "operations"):
                value = entry.get(field, [])
                if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
                    raise TypeError(f"user {uid!r} {field} must be a list of nonempty names")
            unknown = set(entry.get("departments") or []) - KNOWN_DEPARTMENTS
            if unknown:
                raise ValueError(f"user {uid!r} lists unknown departments: {sorted(unknown)}")
    except FileNotFoundError as exc:
        raise HTTPException(503, "Access control is not configured: "
                                 f"declare users in {settings.access_control_path}") from exc
    except (OSError, yaml.YAMLError, TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(503, f"Access control configuration is invalid: {exc}") from exc
    return users.get(union_id) or {}


def departments_for(union_id: str) -> set[str]:
    return set(_entry_for(union_id).get("departments", []))


def workflow_departments_for(union_id: str) -> set[str]:
    """Exact catalogue department labels, explicitly granted; never translated or guessed."""
    return set(_entry_for(union_id).get("workflow_departments", []))


def operations_for(union_id: str) -> set[str]:
    return set(_entry_for(union_id).get("operations", []))
