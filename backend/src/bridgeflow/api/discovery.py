"""Employee-scoped discovery reads. Mutations are not exposed as browser proxies."""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from pydantic import Field, ValidationError

from bridgeflow.access import operations_for
from bridgeflow.api.workflow_tools import _require_writes
from bridgeflow.config import REPO_ROOT, settings
from bridgeflow.identity import UserIdentity, require_user
from bridgeflow.security import consume_approval
from bridgeflow.store import _root
from bridgeflow.workflow.discovery import (
    Discovery,
    DiscoveryError,
    Identifier,
    MaterialInput,
    OpportunityInput,
    Reference,
    Strict,
    Text,
)
from bridgeflow.workflow.discovery_decisions import (
    DecisionPolicy,
    DecisionProposal,
    DiscoveryDecisions,
    load_decision_policy,
)
from bridgeflow.workflow.discovery_graph import DiscoveryGraphs, FlowGraph
from bridgeflow.workflow.discovery_meetings import DiscoveryMeetings, MeetingInput
from bridgeflow.workflow.discovery_scoring import (
    DiscoveryScores,
    ScoreDraft,
    ScoringPolicy,
    load_policy,
)
from bridgeflow.workflow.material_uploads import UploadQuotaError
from bridgeflow.workflow.store import ConcurrencyError, WorkflowStore

router = APIRouter(prefix="/discovery", tags=["discovery"])
BrowserUser = Annotated[UserIdentity | None, Depends(require_user)]
Kind = Literal["material", "opportunity", "graph", "score", "meeting", "decision"]


def service() -> Discovery:
    root = _root()
    return Discovery(WorkflowStore(root / "workflow.sqlite3"), root / "discovery-blobs")


def visible(record: dict, allowed: set[str] | None) -> bool:
    scope = record.get("departments", [record.get("department")])
    return allowed is None or bool(scope) and set(scope) <= allowed


def scope(user: UserIdentity | None) -> set[str] | None:
    """Every signed-in employee sees every discovery record (2026-09-24, see workflow/visibility.py)."""
    return None


def scoring_policy(project: str, user: UserIdentity | None = None) -> ScoringPolicy:
    try:
        policy = load_policy(settings.discovery_scoring_policy_path)
    except DiscoveryError as exc:
        raise HTTPException(503, str(exc)) from exc
    if policy.project_id != project or not visible(policy.model_dump(), scope(user)):
        raise HTTPException(404, "Scoring policy not found")
    return policy


@router.post("/sample")
def load_sample(user: BrowserUser) -> dict:
    """Explicit sample project: fictional people, from a material to an approved MVP decision.

    Like the sample notebook and the sample workflow, it is a click, not a model call. It
    only runs under the sample's own policies (data/discovery_demo/); any other policy
    refuses it, and a project that already exists is returned as it is.
    """
    from bridgeflow.workflow import discovery_sample

    sample = discovery_sample.load(REPO_ROOT / "data/discovery_demo/sample-project.yaml")
    try:
        scoring = load_policy(settings.discovery_scoring_policy_path)
        decision = load_decision_policy(settings.discovery_decision_policy_path)
        return discovery_sample.seed(service(), scoring, decision, sample)
    except DiscoveryError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/{project}/scoring-policy")
def policy_view(project: str, user: BrowserUser) -> dict:
    policy = scoring_policy(project, user)
    return {**policy.model_dump(mode="json"), "fingerprint": policy.fingerprint}


def decision_policy(project: str, user: UserIdentity | None = None) -> DecisionPolicy:
    try:
        policy = load_decision_policy(settings.discovery_decision_policy_path)
    except DiscoveryError as exc:
        raise HTTPException(503, str(exc)) from exc
    if policy.project_id != project or not visible(policy.model_dump(), scope(user)):
        raise HTTPException(404, "Decision policy not found")
    return policy


@router.get("/{project}/decision-policy")
def decision_policy_view(project: str, user: BrowserUser) -> dict:
    policy = decision_policy(project, user)
    subject = user.sub if user else "dsh-authenticated-session"
    actions = [op for op, (_, role) in DECISION_OPERATIONS.items()
               if subject in getattr(policy, role) and (user is None or op in operations_for(subject))]
    return {**policy.model_dump(mode="json"), "fingerprint": policy.fingerprint,
            "viewer": {"subject": subject, "actions": actions}}


@router.get("/{project}/{kind}")
def inventory(project: str, kind: Kind, user: BrowserUser,
              offset: Annotated[int, Query(ge=0)] = 0,
              limit: Annotated[int, Query(ge=1, le=50)] = 20) -> dict:
    domain, allowed = service(), scope(user)
    try:
        prefix = domain.stream(kind, project, "placeholder").rsplit(":", 1)[0] + ":"
    except ValidationError as exc:
        raise HTTPException(422, "Invalid discovery project") from exc
    total, items = 0, []
    for stream in domain.store.streams(prefix):
        identifier = stream.rsplit(":", 1)[1]
        record = domain.read(kind, project, identifier)
        if not visible(record, allowed):
            continue
        if offset <= total < offset + limit:
            if kind == "score":
                record = DiscoveryScores(domain, scoring_policy(project, user)).read(project, identifier)
                # The chart needs the linked candidate's name on every score page.
                # Looking up only the first candidate page leaves later ratings as opaque IDs.
                record["opportunity_title"] = domain.read(
                    "opportunity", project, record["opportunity_id"])["title"]
            elif kind == "decision":
                record = DiscoveryDecisions(domain, decision_policy(project, user)).read(project, identifier)
            elif kind == "meeting":
                record = DiscoveryMeetings(domain).read(project, identifier)
            # Claims belong in an explicit detail view, not an unbounded list.
            items.append({key: record[key] for key in (
                "id", "project_id", "version", "created_at", "department", "departments",
                "title", "filename", "parser_status", "detected_kind", "status", "opportunity_id", "opportunity_title",
                "coordinates", "not_plotted_reasons", "policy_fingerprint", "phase", "stale_candidates", "stale_sources", "proposal_version",
                "recorded_status", "stale_reasons", "tally", "pending_conditions") if key in record})
        total += 1
    return {"items": items, "total": total, "offset": offset, "limit": limit,
            "has_more": offset + len(items) < total}


@router.get("/{project}/{kind}/{identifier}")
def detail(project: str, kind: Kind, identifier: str, user: BrowserUser,
           version: Annotated[int | None, Query(ge=1)] = None) -> dict:
    domain, allowed = service(), scope(user)
    try:
        # Authorize current scope before exposing historical versions or their existence.
        current = domain.read(kind, project, identifier)
        if not visible(current, allowed):
            raise HTTPException(404, "Discovery object not found")
        record = (DiscoveryScores(domain, scoring_policy(project, user)).read(project, identifier, version) if kind == "score"
                  else DiscoveryGraphs(domain).read(project, identifier, version) if kind == "graph"
                  else DiscoveryMeetings(domain).read(project, identifier, version) if kind == "meeting"
                  else DiscoveryDecisions(domain, decision_policy(project, user)).read(project, identifier, version) if kind == "decision"
                  else domain.opportunity(project, identifier, version) if kind == "opportunity"
                  else domain.read(kind, project, identifier, version))
        if not visible(record, allowed):
            raise HTTPException(404, "Discovery object not found")
        return record
    except DiscoveryError as exc:
        raise HTTPException(404, "Discovery object not found") from exc
    except ValidationError as exc:
        raise HTTPException(422, "Invalid discovery identifier") from exc


# Writes are host-only tools; the browser proxy never forwards this router.
tools_router = APIRouter(prefix="/tools", tags=["discovery-tools"])


class MaterialQuery(Strict):
    project_id: Identifier
    material_id: Identifier | None = None
    sheet_offset: int = Field(0, ge=0)
    offset: int = Field(0, ge=0)
    limit: int = Field(5, ge=1, le=10)


@tools_router.post("/discovery-materials")
def material_summaries(query: MaterialQuery) -> dict:
    """Trusted-host model view; no raw cells, text, labels or inferred semantics."""
    domain = service()
    if query.sheet_offset and not query.material_id:
        raise HTTPException(422, "Specify a material for sheet pagination")
    prefix = domain.stream("material", query.project_id, "placeholder").rsplit(":", 1)[0] + ":"
    streams = domain.store.streams(prefix)
    if query.material_id:
        selected = domain.stream("material", query.project_id, query.material_id)
        if selected not in streams:
            raise HTTPException(404, "Discovery material not found")
        streams = [selected]
    items = []
    for stream in streams[query.offset:query.offset + query.limit]:
        record = domain.read("material", query.project_id, stream.rsplit(":", 1)[1])
        shape = record.get("shape") or {}
        sheets = shape.get("sheets", [])
        summary = {key: record[key] for key in (
            "id", "project_id", "department", "period", "filename", "version", "seq",
            "digest", "declared_kind", "detected_kind", "parser_status")}
        summary.update(sheets=[{key: sheet[key] for key in (
            "name", "header_row", "physical_rows", "data_rows") if key in sheet}
            for sheet in sheets[query.sheet_offset:query.sheet_offset + 5]],
            sheet_count=shape.get("sheet_count", len(sheets)),
            sheet_offset=query.sheet_offset,
            sheets_has_more=query.sheet_offset + 5 < len(sheets),
            inspection_truncated=bool(shape.get("truncated")),
            sheets_truncated=bool(shape.get("truncated")) or query.sheet_offset > 0 or len(sheets) > 5)
        if "lines" in shape:
            summary["text_lines"] = shape["lines"]
        items.append(summary)
    return {"items": items, "total": len(streams), "offset": query.offset,
            "has_more": query.offset + len(items) < len(streams),
            "boundary": "Structure and locations only. Ask the person for meaning; do not infer business facts from shapes."}


class ProposalWrite(Strict):
    proposal: OpportunityInput
    call_id: str | None = Field(None, max_length=200)


@tools_router.post("/discovery-propose")
async def propose(request: ProposalWrite, http: Request) -> dict:
    _require_writes()
    actor = consume_approval(http.headers.get("x-bridgeflow-approval", ""), await http.body(),
                             "discovery_propose")
    try:
        saved = service().propose(request.proposal, actor)
    except ConcurrencyError as exc:
        raise HTTPException(409, str(exc)) from exc
    except DiscoveryError as exc:
        raise HTTPException(422, str(exc)) from exc
    # Bounded acknowledgement, not a second copy of the complete draft.
    return {key: saved[key] for key in ("id", "project_id", "version", "seq", "status", "actor")}


def uploads():
    from bridgeflow.workflow.material_uploads import MaterialUploads
    return MaterialUploads(_root() / "discovery-uploads.sqlite3",
                           owner_count=settings.discovery_upload_owner_count,
                           owner_bytes=settings.discovery_upload_owner_bytes,
                           total_bytes=settings.discovery_upload_total_bytes)


class MaterialRegistration(Strict):
    upload_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    material: MaterialInput
    call_id: str | None = Field(None, max_length=200)


@router.post("/uploads")
async def upload_material(user: BrowserUser, metadata: Annotated[str, Form()],
                          file: Annotated[UploadFile, File()]) -> dict:
    _require_writes()
    try:
        item = MaterialInput.model_validate_json(metadata)
    except ValidationError as exc:
        raise HTTPException(422, "Invalid material registration metadata") from exc
    if user is not None and "discovery_upload" not in operations_for(user.sub):
        raise HTTPException(403, "Material upload is not authorized")
    if file.filename != item.filename:
        raise HTTPException(422, "Uploaded filename must match registration metadata")
    from bridgeflow.workflow.material_uploads import MAX_BYTES
    try:
        payload = await file.read(MAX_BYTES + 1)
        return uploads().stage(item, payload, user.sub if user else "dsh-authenticated-session")
    except UploadQuotaError as exc:
        raise HTTPException(429, str(exc)) from exc
    except DiscoveryError as exc:
        raise HTTPException(422, str(exc)) from exc
    finally:
        await file.close()


@tools_router.post("/discovery-register")
async def register_material(request: MaterialRegistration, http: Request) -> dict:
    _require_writes()
    actor = consume_approval(http.headers.get("x-bridgeflow-approval", ""), await http.body(),
                             "discovery_register")
    staging = uploads()
    try:
        payload = staging.checked(request.upload_id, request.material, request.digest)
        record = service().register(request.material, payload, actor)
        staging.discard(request.upload_id)
    except DiscoveryError as exc:
        raise HTTPException(422, str(exc)) from exc
    except ConcurrencyError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {key: record[key] for key in ("id", "project_id", "version", "seq", "digest",
                                        "parser_status", "detected_kind", "actor")}


@router.get("/{project}/material/{identifier}/original")
def original(project: str, identifier: str, user: BrowserUser,
             version: Annotated[int | None, Query(ge=1)] = None) -> dict:
    import base64
    import hashlib

    record = detail(project, "material", identifier, user, version)
    try:
        payload = (service().blobs / record["digest"]).read_bytes()
    except OSError as exc:
        raise HTTPException(503, "Original material is unavailable") from exc
    if hashlib.sha256(payload).hexdigest() != record["digest"]:
        raise HTTPException(409, "Original material failed integrity verification")
    return {"filename": record["filename"], "version": record["version"], "digest": record["digest"],
            "base64": base64.b64encode(payload).decode("ascii")}


class GraphWrite(Strict):
    graph: FlowGraph
    call_id: str | None = Field(None, max_length=200)


@tools_router.post("/discovery-graph-save")
async def save_graph(request: GraphWrite, http: Request) -> dict:
    _require_writes()
    actor = consume_approval(http.headers.get("x-bridgeflow-approval", ""), await http.body(),
                             "discovery_graph_save")
    try:
        saved = DiscoveryGraphs(service()).save(request.graph, actor)
    except ConcurrencyError as exc:
        raise HTTPException(409, str(exc)) from exc
    except DiscoveryError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {key: saved[key] for key in ("id", "project_id", "version", "seq", "status", "actor",
                                        "stale_sources", "opportunity_stale")}


class ScoreWrite(Strict):
    score: ScoreDraft
    call_id: str | None = Field(None, max_length=200)


@tools_router.post("/discovery-score-save")
async def save_score(request: ScoreWrite, http: Request) -> dict:
    _require_writes()
    actor = consume_approval(http.headers.get("x-bridgeflow-approval", ""), await http.body(),
                             "discovery_score_save")
    try:
        saved = DiscoveryScores(service(), scoring_policy(request.score.project_id)).save(request.score, actor)
    except ConcurrencyError as exc:
        raise HTTPException(409, str(exc)) from exc
    except DiscoveryError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {key: saved[key] for key in ("id", "project_id", "version", "seq", "status", "actor",
                                        "coordinates", "not_plotted_reasons", "approval")}


class MeetingWrite(Strict):
    meeting: MeetingInput
    call_id: str | None = Field(None, max_length=200)


@tools_router.post("/discovery-meeting-save")
async def save_meeting(request: MeetingWrite, http: Request) -> dict:
    _require_writes()
    actor = consume_approval(http.headers.get("x-bridgeflow-approval", ""), await http.body(),
                             "discovery_meeting_save")
    try:
        saved = DiscoveryMeetings(service()).save(request.meeting, actor)
    except ConcurrencyError as exc:
        raise HTTPException(409, str(exc)) from exc
    except DiscoveryError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {key: saved[key] for key in ("id", "project_id", "version", "seq", "status", "actor",
                                        "phase", "stale_candidates", "stale_sources", "approval")}


class DecisionWrite(Strict):
    proposal: DecisionProposal
    call_id: str | None = Field(None, max_length=200)


class DecisionAction(Strict):
    project_id: Identifier
    id: Identifier
    expected_seq: int = Field(ge=1)
    proposal_version: int = Field(ge=1)
    rationale: Text
    call_id: str | None = Field(None, max_length=200)


class DecisionVote(DecisionAction):
    choice: Literal["yes", "no", "abstain"]


class DecisionResolve(DecisionAction):
    condition_id: Identifier
    references: list[Reference] = Field(min_length=1, max_length=10)


class DecisionFinalize(DecisionAction):
    outcome: Literal["approve", "reject"]


DECISION_OPERATIONS = {
    "discovery_decision_propose": (DecisionWrite, "proposers"),
    "discovery_decision_vote": (DecisionVote, "voters"),
    "discovery_decision_resolve": (DecisionResolve, "condition_confirmers"),
    "discovery_decision_finalize": (DecisionFinalize, "approvers"),
}


def authorize_decision(user: UserIdentity, operation: str, body: dict):
    model, role = DECISION_OPERATIONS[operation]
    try:
        request = model.model_validate(body)
    except ValidationError as exc:
        raise HTTPException(422, "Invalid decision request") from exc
    item = request.proposal if isinstance(request, DecisionWrite) else request
    policy = decision_policy(item.project_id, user)
    if user.sub not in getattr(policy, role):
        raise HTTPException(403, "Employee is not in the declared decision role")
    domain, allowed = service(), scope(user)
    try:
        if isinstance(request, DecisionWrite):
            if item.policy_fingerprint != policy.fingerprint:
                raise HTTPException(409, "Decision policy changed")
            meeting = domain.read("meeting", item.project_id, item.meeting_id, item.meeting_version)
            if not visible(meeting, allowed):
                raise HTTPException(404, "Decision meeting not found")
            # Include every meeting input, not just the selected candidates.
            source_versions = list(meeting["source_versions"])
            for candidate in meeting["candidates"]:
                if not visible(domain.read("opportunity", item.project_id, candidate["id"]), allowed):
                    raise HTTPException(404, "Decision candidate not found")
            try:
                old = domain.read("decision", item.project_id, item.id)
            except DiscoveryError:
                old = None
        else:
            old = domain.read("decision", item.project_id, item.id)
            source_versions = list(old["source_versions"])
        if old is not None and not visible(old, allowed):
            raise HTTPException(404, "Decision not found")
        if old is not None and not isinstance(request, DecisionWrite) and old["policy_fingerprint"] != policy.fingerprint:
            raise HTTPException(409, "Decision policy changed; revise the proposal")
        if isinstance(request, DecisionResolve):
            source_versions.extend((r.material_id, r.version) for r in request.references)
        for identifier, version in source_versions:
            if not visible(domain.read("material", item.project_id, identifier, version), allowed):
                raise HTTPException(404, "Decision source not found")
    except DiscoveryError as exc:
        raise HTTPException(404, "Decision input not found") from exc


async def execute_decision(operation: str, request, http: Request) -> dict:
    _require_writes()
    actor = consume_approval(http.headers.get("x-bridgeflow-approval", ""), await http.body(), operation)
    item = request.proposal if isinstance(request, DecisionWrite) else request
    decisions = DiscoveryDecisions(service(), decision_policy(item.project_id))
    try:
        if isinstance(request, DecisionWrite):
            saved = decisions.propose(item, actor)
        else:
            args = (item.project_id, item.id, item.expected_seq, item.proposal_version, actor)
            if isinstance(request, DecisionVote):
                saved = decisions.vote(*args, item.choice, item.rationale)
            elif isinstance(request, DecisionResolve):
                saved = decisions.resolve(*args, item.condition_id, item.rationale, item.references)
            else:
                saved = decisions.decide(*args, item.outcome, item.rationale)
    except ConcurrencyError as exc:
        raise HTTPException(409, str(exc)) from exc
    except DiscoveryError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {key: saved[key] for key in ("id", "project_id", "version", "seq", "proposal_version", "status",
                                       "recorded_status", "last_actor", "tally", "pending_conditions", "stale_reasons")}


@tools_router.post("/discovery-decision-propose")
async def propose_decision(request: DecisionWrite, http: Request) -> dict:
    return await execute_decision("discovery_decision_propose", request, http)


@tools_router.post("/discovery-decision-vote")
async def vote_decision(request: DecisionVote, http: Request) -> dict:
    return await execute_decision("discovery_decision_vote", request, http)


@tools_router.post("/discovery-decision-resolve")
async def resolve_decision(request: DecisionResolve, http: Request) -> dict:
    return await execute_decision("discovery_decision_resolve", request, http)


@tools_router.post("/discovery-decision-finalize")
async def finalize_decision(request: DecisionFinalize, http: Request) -> dict:
    return await execute_decision("discovery_decision_finalize", request, http)
