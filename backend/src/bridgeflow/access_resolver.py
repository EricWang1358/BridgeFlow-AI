"""Who someone is, resolved live from Feishu wiki spaces (docs/27, issue #204).

Membership has exactly one source of truth — Feishu. access-control.yaml keeps
only what Feishu cannot say: which wiki space stands for which unit, and what
each role may do. A caller's union_id (plus the open_id the portal observed for
it, since the wiki API answers with open_ids) is matched against each space's
member list; the roles found there union into the caller's grants.

Fail closed throughout, same rule as the field dictionary: a missing or invalid
mapping file, missing credentials, or an unreachable Feishu answers 503 —
never a guessed, partial, or stale permission set. Only successful member
lists are cached, for MEMBERSHIP_TTL_SECONDS. The mapping file itself is
re-read on every call so a role-policy edit takes effect immediately.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import get_args

import httpx
import yaml
from fastapi import HTTPException

from bridgeflow import identity
from bridgeflow.config import REPO_ROOT, settings
from bridgeflow.feishu import _RATE_LIMIT_CODES, FeishuError
from bridgeflow.schemas import Department

KNOWN_DEPARTMENTS = set(get_args(Department))
MEMBERSHIP_TTL_SECONDS = 300
_MAX_ATTEMPTS = 3
#: Member types that stand for groups rather than people. They are ignored, not
#: expanded (expansion needs contact scopes): access is granted by adding the
#: person to the space directly.
_NON_PERSON_TYPES = {"openchat", "opendepartment", "chat", "department", "group"}


def access_path() -> Path:
    path = Path(settings.access_control_path)
    return path if path.is_absolute() else REPO_ROOT / path


@dataclass(frozen=True)
class Resolved:
    """The roles a caller holds and the grants they union into."""

    roles: frozenset[str]
    departments: frozenset[str]
    workflow_departments: frozenset[str]
    operations: frozenset[str]


def structure() -> dict:
    """The declared spaces and roles, re-read and re-validated on every call."""
    try:
        raw = yaml.safe_load(access_path().read_text(encoding="utf-8")) or {}
        spaces = raw.get("spaces") or {}
        roles = raw.get("roles") or {}
        if not isinstance(spaces, dict) or not isinstance(roles, dict):
            raise TypeError("'spaces' and 'roles' must be mappings")
        departments = spaces.get("departments") or {}
        if not isinstance(departments, dict) or set(departments) != KNOWN_DEPARTMENTS:
            raise ValueError(f"spaces.departments must declare exactly {sorted(KNOWN_DEPARTMENTS)}")
        entries = []
        for unit, entry in [*departments.items(), ("master_office", spaces.get("master_office"))]:
            if not isinstance(entry, dict):
                raise TypeError(f"space {unit!r} must be a mapping with space_id, member and admin")
            if not isinstance(entry.get("space_id"), str) or not entry["space_id"].strip():
                raise TypeError(f"space {unit!r} needs a nonempty space_id")
            for seat in ("member", "admin"):
                if entry.get(seat) not in roles:
                    raise ValueError(f"space {unit!r} {seat} references undeclared role {entry.get(seat)!r}")
            entries.append(entry)
        if len({entry["space_id"] for entry in entries}) != len(entries):
            raise ValueError("space_id values must be unique")
        for name, role in roles.items():
            if not isinstance(role, dict):
                raise TypeError(f"role {name!r} must be a mapping")
            for field in ("departments", "workflow_departments", "operations"):
                value = role.get(field, [])
                if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
                    raise TypeError(f"role {name!r} {field} must be a list of nonempty names")
            unknown = set(role.get("departments") or []) - KNOWN_DEPARTMENTS
            if unknown:
                raise ValueError(f"role {name!r} lists unknown departments: {sorted(unknown)}")
            if "confirm_mapping" in (role.get("operations") or []) \
                    and not KNOWN_DEPARTMENTS <= set(role.get("departments") or []):
                raise ValueError(f"role {name!r} grants confirm_mapping without all departments")
    except FileNotFoundError as exc:
        raise HTTPException(503, "Access control is not configured: "
                                 f"declare spaces and roles in {settings.access_control_path}") from exc
    except (OSError, yaml.YAMLError, TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(503, f"Access control configuration is invalid: {exc}") from exc
    return {"spaces": spaces, "roles": roles}


def space_departments() -> dict[str, str]:
    """space_id -> department, as a human declared in spaces.departments.

    Pure structure: never consults Feishu, never guesses. A missing or invalid
    file raises 503 like every other structure() consumer.
    """
    return {entry["space_id"]: unit for unit, entry in structure()["spaces"]["departments"].items()}


def department_for_space(space_id: str) -> str | None:
    """The department a wiki space stands for, or None when it declares none."""
    return space_departments().get(space_id)


# --- Feishu side: tenant-token wiki member reads, sync because access.py is sync --------

_token: tuple[str, float] | None = None


def _tenant_token(client: httpx.Client) -> str:
    global _token
    if _token and _token[1] > time.monotonic() + 60:
        return _token[0]
    try:
        response = client.post("/open-apis/auth/v3/tenant_access_token/internal",
                               json={"app_id": settings.feishu_app_id, "app_secret": settings.feishu_app_secret})
        body = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise FeishuError(f"Feishu could not be reached: {exc}") from exc
    if response.status_code >= 400 or body.get("code", 0) != 0:
        raise FeishuError(f"Feishu refused (code {body.get('code')}): {body.get('msg', 'no message')}")
    _token = (str(body["tenant_access_token"]), time.monotonic() + float(body.get("expire", 0)))
    return _token[0]


def _get_json(client: httpx.Client, path: str, params: dict[str, str], headers: dict[str, str]) -> dict:
    """GET with bounded backoff on frequency control; every other refusal surfaces as-is."""
    delay = 0.5
    for attempt in range(_MAX_ATTEMPTS):
        try:
            response = client.get(path, params=params, headers=headers)
        except httpx.HTTPError as exc:
            raise FeishuError(f"Feishu could not be reached: {exc}") from exc
        try:
            body = response.json()
        except ValueError as exc:
            raise FeishuError(f"Feishu returned HTTP {response.status_code} without a JSON body") from exc
        code = body.get("code", 0)
        if response.status_code < 400 and code == 0:
            return body
        retryable = response.status_code == 429 or code in _RATE_LIMIT_CODES
        if not retryable or attempt == _MAX_ATTEMPTS - 1:
            raise FeishuError(f"Feishu refused (code {code}): {body.get('msg', 'no message')}")
        time.sleep(delay)
        delay *= 2
    raise FeishuError("unreachable")  # pragma: no cover


def client_factory() -> httpx.Client:
    """The sync client membership lookups run on; tests substitute their own transport."""
    if not (settings.feishu_app_id and settings.feishu_app_secret):
        raise FeishuError("Feishu is not configured: export FEISHU_APP_ID and FEISHU_APP_SECRET")
    return httpx.Client(base_url=settings.feishu_base_url, timeout=10)


def fetch_space_members(space_id: str) -> dict[str, str]:
    """member id -> member_role for one wiki space, person-type members only.

    The API answers with open_ids; resolve() bridges them to union_ids through
    the identity pairs the portal already signs into every login token.
    """
    with client_factory() as client:
        headers = {"authorization": f"Bearer {_tenant_token(client)}"}
        members: dict[str, str] = {}
        page_token = ""
        seen_tokens: set[str] = set()
        while True:
            params = {"page_size": "50"}  # the members endpoint rejects >50 with 131002
            if page_token:
                params["page_token"] = page_token
            body = _get_json(client, f"/open-apis/wiki/v2/spaces/{space_id}/members", params, headers)
            data = body.get("data") or {}
            entries = data.get("members")
            if entries is None:
                entries = data.get("items")  # envelope name confirmed against a real tenant
            for item in entries or []:
                if str(item.get("member_type") or "openid") in _NON_PERSON_TYPES:
                    continue
                member_id, role = str(item.get("member_id") or ""), str(item.get("member_role") or "")
                if member_id and role in ("admin", "member"):
                    members[member_id] = role
            if not data.get("has_more"):
                return members
            # A continuation token must be fresh: an empty or repeated one would
            # re-request the same page forever, so refuse instead of looping.
            next_token = str(data.get("page_token") or "")
            if not next_token or next_token in seen_tokens:
                raise FeishuError(f"Feishu membership pagination did not advance (space {space_id})")
            seen_tokens.add(next_token)
            page_token = next_token


# --- Resolution -------------------------------------------------------------------------

_members_cache: dict[str, tuple[float, dict[str, str]]] = {}


def reset_cache() -> None:
    """Tests and credential rotation both need to drop cached memberships and the token."""
    global _token
    _members_cache.clear()
    _token = None


def _members_of(space_id: str) -> dict[str, str]:
    cached = _members_cache.get(space_id)
    if cached and time.monotonic() - cached[0] < MEMBERSHIP_TTL_SECONDS:
        return cached[1]
    try:
        members = fetch_space_members(space_id)
    except FeishuError as exc:
        raise HTTPException(503, f"Access control could not reach Feishu: {exc}") from exc
    _members_cache[space_id] = (time.monotonic(), members)
    return members


def resolve(union_id: str) -> Resolved:
    """The caller's roles from Feishu membership, unioned into grants.

    A user no space lists resolves to empty sets — the same "unlisted means
    nothing" rule as the old roster. Only configuration and availability
    failures raise, and they raise before any per-user question is answered.
    """
    declared = structure()
    candidates = {union_id, identity.open_id_for(union_id)} - {""}
    found: set[str] = set()
    entries = [*declared["spaces"]["departments"].values(), declared["spaces"]["master_office"]]
    for entry in entries:
        members = _members_of(entry["space_id"])
        seat = next((members[key] for key in candidates if key in members), "")
        if seat in ("member", "admin"):
            found.add(entry[seat])
    roles = declared["roles"]
    return Resolved(
        roles=frozenset(found),
        departments=frozenset(d for name in found for d in roles[name].get("departments", [])),
        workflow_departments=frozenset(d for name in found for d in roles[name].get("workflow_departments", [])),
        operations=frozenset(o for name in found for o in roles[name].get("operations", [])),
    )
