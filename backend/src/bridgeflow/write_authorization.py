"""Employee authorization supplements, but never replaces, native DSH approval."""
from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import time
from typing import Any

from fastapi import HTTPException

from bridgeflow.access import KNOWN_DEPARTMENTS, Resolved, resolve
from bridgeflow.identity import UserIdentity
from bridgeflow.store import _root

OPERATIONS = frozenset({"confirm_mapping", "confirm_column_match", "quarantine_decide",
                       "quarantine_apply", "convention_decide", "risk_disposition", "workflow_record", "workflow_approve_submit", "workflow_accept_scope",
                       "workflow_handoff", "feishu_import", "feishu_upload_report", "discovery_propose", "discovery_register", "discovery_graph_save", "discovery_score_save", "discovery_meeting_save", "discovery_decision_propose", "discovery_decision_vote",
                       "discovery_decision_resolve", "discovery_decision_finalize", "dictionary_draft", "dictionary_publish"})
SCHEMA = """
CREATE TABLE IF NOT EXISTS employee_permits (
 token TEXT PRIMARY KEY, subject TEXT NOT NULL, operation TEXT NOT NULL,
 digest TEXT NOT NULL, expires REAL NOT NULL, used INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS employee_authorizations (
 nonce TEXT PRIMARY KEY, subject TEXT NOT NULL, operation TEXT NOT NULL,
 digest TEXT NOT NULL, call_id TEXT, consumed_at REAL NOT NULL);
"""


def _ensure_roles_column(connection: sqlite3.Connection) -> None:
    """Ledgers from before issue #204 lack the role snapshot; add it once, in place."""
    try:
        connection.execute("ALTER TABLE employee_authorizations ADD COLUMN roles TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError as exc:
        # Only "already migrated" is expected; lock, read-only and schema
        # failures must surface, not be swallowed.
        if "duplicate column" not in str(exc).lower():
            raise


def authorize(user: UserIdentity, operation: str, body: dict[str, Any]) -> Resolved:
    """Recheck both operation grant and current data scope immediately before mutation.

    The caller's policy is resolved once here; every check below reads that single
    snapshot, and consume() records its roles into the ledger — the audited roles
    are exactly the ones that justified the grant.
    """
    resolved = resolve(user.sub)
    if operation not in OPERATIONS or operation not in resolved.operations:
        raise HTTPException(403, "This employee is not authorized for this operation")
    from bridgeflow.api.batches import _visible, load_batch

    if operation in {"confirm_column_match", "quarantine_decide", "quarantine_apply",
                     "convention_decide", "risk_disposition"}:
        _visible(load_batch(str(body.get("batch_id", ""))), user)
    elif operation == "feishu_upload_report":
        # Crossing into Feishu is where department scope still applies (2026-09-24).
        batch = _visible(load_batch(str(body.get("batch_id", ""))), user)
        denied = {table.department for table in batch.clean_tables} - resolved.departments
        if denied:
            raise HTTPException(403, f"Uploading to Feishu needs every department in the batch; missing: {sorted(denied)}")
    elif operation == "dictionary_draft":
        # Drafting reads a batch's column statistics; the drafter must be able to see
        # the batch they draft from (D32: the master-table owner sees every department).
        batch_id = str(body.get("batch_id", ""))
        if batch_id:
            _visible(load_batch(batch_id), user)
    elif operation in {"discovery_decision_propose", "discovery_decision_vote",
                       "discovery_decision_resolve", "discovery_decision_finalize"}:
        from bridgeflow.api.discovery import authorize_decision
        authorize_decision(user, operation, body)
    elif operation == "discovery_meeting_save":
        from pydantic import ValidationError

        from bridgeflow.api.discovery import MeetingWrite, service
        from bridgeflow.workflow.discovery import DiscoveryError

        try:
            meeting = MeetingWrite.model_validate(body).meeting
        except ValidationError as exc:
            raise HTTPException(422, "Invalid discovery meeting") from exc
        domain = service()
        try:
            refs = [ref.model_dump() for statement in meeting.statements() for ref in statement.references]
            for binding in meeting.candidates:
                # Both current and referenced scopes must be visible; approval is
                # not a way to resurrect access to an old candidate snapshot.
                for version in (None, binding.version):
                    candidate = domain.read("opportunity", meeting.project_id, binding.id, version)
                    refs.extend(ref for claim in candidate["claims"] for ref in claim["references"])
            for ref in refs:
                domain.read("material", meeting.project_id, ref["material_id"], ref["version"])
        except DiscoveryError as exc:
            raise HTTPException(404, "Meeting candidate or source not found") from exc
    elif operation == "discovery_score_save":
        from pydantic import ValidationError

        from bridgeflow.api.discovery import ScoreWrite, scoring_policy, service
        from bridgeflow.workflow.discovery import DiscoveryError

        try:
            score = ScoreWrite.model_validate(body).score
        except ValidationError as exc:
            raise HTTPException(422, "Invalid discovery score") from exc
        policy = scoring_policy(score.project_id, user)
        if score.policy_fingerprint != policy.fingerprint:
            raise HTTPException(409, "Scoring policy changed; read it again")
        domain = service()
        try:
            candidate = domain.read("opportunity", score.project_id, score.opportunity_id)
            refs = [ref for claim in candidate["claims"] for ref in claim["references"]]
            refs += [ref.model_dump() for rating in [score.effort, score.value] if rating for ref in rating.references]
            for ref in refs:
                domain.read("material", score.project_id, ref["material_id"], ref["version"])
        except DiscoveryError as exc:
            raise HTTPException(404, "Score candidate or source not found") from exc
    elif operation == "discovery_graph_save":
        from pydantic import ValidationError

        from bridgeflow.api.discovery import GraphWrite, service
        from bridgeflow.workflow.discovery import DiscoveryError

        try:
            graph = GraphWrite.model_validate(body).graph
        except ValidationError as exc:
            raise HTTPException(422, "Invalid discovery graph") from exc
        domain = service()
        try:
            candidate = domain.read("opportunity", graph.project_id, graph.opportunity_id)
            refs = [ref for claim in candidate["claims"] for ref in claim["references"]]
            refs += [ref.model_dump() for item in [*graph.nodes, *graph.edges] for ref in item.references]
            for ref in refs:
                domain.read("material", graph.project_id, ref["material_id"], ref["version"])
        except DiscoveryError as exc:
            raise HTTPException(404, "Graph opportunity or source not found") from exc
    elif operation == "discovery_register":
        from pydantic import ValidationError

        from bridgeflow.api.discovery import MaterialRegistration, service, uploads
        from bridgeflow.workflow.discovery import DiscoveryError

        try:
            registration = MaterialRegistration.model_validate(body)
        except ValidationError as exc:
            raise HTTPException(422, "Invalid material registration") from exc
        try:
            uploads().checked(registration.upload_id, registration.material, registration.digest)
        except DiscoveryError as exc:
            raise HTTPException(404, "Matching staged upload not found") from exc
    elif operation == "discovery_propose":
        from pydantic import ValidationError

        from bridgeflow.api.discovery import ProposalWrite, service
        from bridgeflow.workflow.discovery import DiscoveryError

        try:
            proposal = ProposalWrite.model_validate(body).proposal
        except ValidationError as exc:
            raise HTTPException(422, "Invalid discovery proposal") from exc
        domain = service()
        try:
            for claim in proposal.claims:
                for ref in claim.references:
                    domain.read("material", proposal.project_id, ref.material_id, ref.version)
        except DiscoveryError as exc:
            raise HTTPException(404, "Discovery source or object not found") from exc
    elif operation == "confirm_mapping":
        if not KNOWN_DEPARTMENTS <= resolved.departments:
            raise HTTPException(403, "Global mapping decisions require all department scopes")
    elif operation == "feishu_import":
        files = body.get("files")
        if not isinstance(files, list) or not files or any(
            not isinstance(f, dict) or not isinstance(f.get("department"), str)
            or not f["department"].strip() for f in files
        ):
            raise HTTPException(422, "Declared import files are required")
        if not {f.get("department") for f in files} <= resolved.departments:
            raise HTTPException(403, "Imported departments are outside this employee's scope")
    else:
        from bridgeflow.api.workflow import _domain_errors, service
        from bridgeflow.workflow.visibility import Visibility

        workflow = service()
        visible = Visibility(workflow.catalogue, user)
        with _domain_errors():
            if operation == "workflow_handoff":
                permitted = visible.stage(workflow.handoff(str(body.get("handoff_id", ""))).stage)
            elif body.get("artifact_id"):
                permitted = visible.template(workflow.artifact(str(body["artifact_id"])).template)
            else:
                permitted = visible.template(str(body.get("template", "")))
        if not permitted:
            # One answer for both cases, so a refusal never confirms the object exists — but
            # worded so the person knows what to do about it.
            raise HTTPException(404, "Not found, or outside the departments your account may fill "
                                     "(workflow access is granted per department; ask an administrator "
                                     "if this should be yours)")
    return resolved


def issue(user: UserIdentity, operation: str, raw_body: str) -> str:
    try:
        body = json.loads(raw_body)
        if not isinstance(body, dict):
            raise TypeError("Object required")
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, "Invalid operation body") from exc
    authorize(user, operation, body)
    token = secrets.token_hex(32)
    path = _root() / "approval-receipts.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.executescript(SCHEMA)
        connection.execute("DELETE FROM employee_permits WHERE expires < ?", (time.time(),))
        connection.execute("INSERT INTO employee_permits VALUES (?, ?, ?, ?, ?, 0)",
                           (token, user.sub, operation, hashlib.sha256(raw_body.encode()).hexdigest(),
                            time.time() + 60))
    return token


def consume(connection: sqlite3.Connection, token: str, operation: str | None,
            body: bytes, nonce: str) -> str:
    connection.executescript(SCHEMA)
    _ensure_roles_column(connection)
    row = connection.execute("SELECT subject, operation, digest, expires, used FROM employee_permits WHERE token = ?",
                             (token,)).fetchone()
    digest = hashlib.sha256(body).hexdigest()
    if not row or row[1] != operation or row[2] != digest or row[3] < time.time() or row[4]:
        raise HTTPException(403, "A current employee authorization for this exact operation is required")
    parsed = json.loads(body)
    granted = authorize(UserIdentity(sub=row[0], name="", email=""), row[1], parsed)
    changed = connection.execute("UPDATE employee_permits SET used = 1 WHERE token = ? AND used = 0", (token,))
    if changed.rowcount != 1:
        raise HTTPException(403, "Employee authorization already consumed")
    # The ledger records which roles justified the grant at consumption time;
    # a later Feishu-side change never rewrites this snapshot.
    roles = ",".join(sorted(granted.roles))
    connection.execute("INSERT INTO employee_authorizations VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (nonce, row[0], operation, digest, parsed.get("call_id"), time.time(), roles))
    return row[0]
