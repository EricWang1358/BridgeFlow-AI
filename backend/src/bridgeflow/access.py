"""Who may see which departments: membership from Feishu, rules in access-control.yaml.

Membership lives in Feishu wiki spaces — each business department and the master
office maps to one space, and the space's member list decides the caller's role
(issue #204). access-control.yaml declares only the two things Feishu cannot
say: which space stands for which unit, and what each role may do.

Resolution lives in bridgeflow.access_resolver; this module stays the import
surface every caller already uses. A missing or invalid file, or an unreachable
Feishu, fails loudly ("not configured", 503), never falls back to guessing.
A user no space lists sees nothing.
"""

from __future__ import annotations

from bridgeflow.access_resolver import KNOWN_DEPARTMENTS, Resolved, access_path, resolve

__all__ = ["KNOWN_DEPARTMENTS", "Resolved", "access_path", "departments_for", "operations_for", "resolve",
           "workflow_departments_for"]


def departments_for(union_id: str) -> set[str]:
    return set(resolve(union_id).departments)


def workflow_departments_for(union_id: str) -> set[str]:
    """Exact catalogue department labels, explicitly granted; never translated or guessed."""
    return set(resolve(union_id).workflow_departments)


def operations_for(union_id: str) -> set[str]:
    return set(resolve(union_id).operations)
