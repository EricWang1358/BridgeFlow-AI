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

#: The operation a role must be granted to reach the agent console at all (issue #229).
#: It is an operation like any other, so the console gate is declared in the same file,
#: by the same people, as upload and approval rights — and omitting it grants nothing.
CONSOLE_OPERATION = "console_access"

__all__ = ["CONSOLE_OPERATION", "KNOWN_DEPARTMENTS", "Resolved", "access_path", "console_access_for",
           "departments_for", "operations_for", "resolve", "workflow_departments_for"]


def departments_for(union_id: str) -> set[str]:
    return set(resolve(union_id).departments)


def workflow_departments_for(union_id: str) -> set[str]:
    """Exact catalogue department labels, explicitly granted; never translated or guessed."""
    return set(resolve(union_id).workflow_departments)


def operations_for(union_id: str) -> set[str]:
    return set(resolve(union_id).operations)


def console_access_for(union_id: str) -> bool:
    """May this person reach the agent console? Only a declared grant says yes.

    Resolution failures raise (503) rather than answering False: "we cannot tell"
    and "we checked, the answer is no" are different facts, and the caller words
    them differently.
    """
    return CONSOLE_OPERATION in resolve(union_id).operations
