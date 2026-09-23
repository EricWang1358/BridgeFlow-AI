"""The workflow foundation (#143–#145), walked through the #147 story and its failure modes.

Every test uses the synthetic catalogue in `data/workflow_demo/` or a variant built from
it, so no business name is written here that the catalogue does not declare.
"""
import ast
import copy
import io
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml
from conftest import receipt
from fastapi.testclient import TestClient

from bridgeflow.api.main import app
from bridgeflow.config import REPO_ROOT, settings
from bridgeflow.workflow import adoption, board, catalogue, intake, materials
from bridgeflow.workflow.catalogue import Catalogue, CatalogueError
from bridgeflow.workflow.lifecycle import (
    ArtifactState,
    HandoffState,
    NotificationState,
    TransitionError,
)
from bridgeflow.workflow.ports import (
    LocalOutboxNotifier,
    LocalSqliteSink,
    SinkError,
    UnconfiguredSink,
)
from bridgeflow.workflow.service import StaleRead, WorkflowService
from bridgeflow.workflow.store import WorkflowStore

DEMO = REPO_ROOT / "data/workflow_demo/catalogue.yaml"
RAW = yaml.safe_load(DEMO.read_text(encoding="utf-8"))
FIELDS = RAW["templates"]["production_record"]["fields"]


def label(key: str) -> str:
    return FIELDS[key]["label"]


def alias(key: str) -> str:
    return FIELDS[key]["aliases"][0]


def obs(name: str, value, ref: str = "sheet!A2", kind: str = "file", evidence: str = "") -> intake.Observation:
    return intake.Observation(label=name, value=value, source={"kind": kind, "ref": ref}, evidence=evidence)


def employee_submission() -> list[intake.Observation]:
    """#147: non-standard names, units written out, actual quantity not given."""
    return [
        obs(alias("report_month"), "2026年9月"), obs(alias("plant"), "演示厂站"), obs(alias("year"), "2026"),
        obs(alias("date"), "2026/09/01"), obs(alias("customer"), "演示客户"), obs(alias("project"), "演示项目A"),
        obs(alias("product"), "演示货品"), obs(alias("output_qty"), "100 方"), obs(alias("shipped_qty"), "98 m³"),
    ]


def actual_answer(value="97.5 方", evidence="DEMO-CONFIRM-001"):
    return [obs(label("actual_qty"), value, ref="reply-1", kind="reply", evidence=evidence)]


class Clock:
    def __init__(self):
        self.now = datetime(2026, 9, 13, 9, 0, tzinfo=UTC)

    def __call__(self):
        return self.now


def build(tmp_path, raw=None, sink=None, notifier=None, clock=None) -> WorkflowService:
    declared = Catalogue.model_validate(raw or RAW)
    return WorkflowService(declared, WorkflowStore(tmp_path / "wf.sqlite3"),
                           sink or LocalSqliteSink(tmp_path / "platform.sqlite3"),
                           notifier or LocalOutboxNotifier(tmp_path / "deliveries.sqlite3"),
                           clock=clock or Clock())


def ready(service: WorkflowService) -> str:
    artifact = service.receive("production_record", employee_submission())
    artifact = service.answer(artifact.id, actual_answer(), artifact.seq)
    artifact = service.review(artifact.id, artifact.draft.digest, "reviewer", artifact.seq)
    return service.submit(artifact.id).id


def record_output(service: WorkflowService, project: str = "演示项目A") -> str:
    """What the marketing stage produces: its settlement basis for the same project and month."""
    out = RAW["templates"]["settlement_basis"]["fields"]
    artifact = service.receive("settlement_basis", [
        obs(out["project"]["aliases"][0], project), obs(out["period"]["aliases"][0], "2026年9月"),
        obs(out["settled_qty"]["label"], "97.5 方", evidence="DEMO-SETTLE-001")])
    artifact = service.review(artifact.id, artifact.draft.digest, "reviewer", artifact.seq)
    return service.submit(artifact.id).id


# --- declarations ------------------------------------------------------------------


def test_the_demo_catalogue_loads_and_a_draft_template_never_runs():
    declared = catalogue.load(DEMO)
    assert declared.runnable("production_record").status == "approved"
    assert declared.runnable("settlement_basis").status == "approved"  # the demo's second hop
    # The guarantee itself: the same template, declared as a draft, never runs.
    raw = copy.deepcopy(RAW)
    raw["templates"]["settlement_basis"]["status"] = "draft"
    with pytest.raises(CatalogueError, match="draft"):
        Catalogue.model_validate(raw).runnable("settlement_basis")


@pytest.mark.parametrize("breakage, message", [
    (lambda r: r["stages"]["market_review"].update(inputs=["nowhere"]), "unknown template"),
    (lambda r: r["lineage"][0].update(target="settlement_basis.invented"), "not a declared field"),
    (lambda r: r["templates"]["production_record"]["fields"]["plant"].update(aliases=[alias("customer")]), "two fields"),
    (lambda r: r["templates"]["production_record"].update(business_key=["invented"]), "undeclared fields"),
])
def test_an_inconsistent_catalogue_is_refused_at_load(breakage, message):
    raw = copy.deepcopy(RAW)
    breakage(raw)
    with pytest.raises(ValueError, match=message):
        Catalogue.model_validate(raw)


def test_lineage_is_traced_in_both_directions():
    declared = Catalogue.model_validate(RAW)
    trace = declared.lineage_of("production_record", "actual_qty")
    assert [e.target for e in trace["downstream"]] == ["settlement_basis.settled_qty"]
    assert trace["downstream"][0].status == "inferred"
    assert declared.lineage_of("settlement_basis", "settled_qty")["upstream"][0].source == "production_record.actual_qty"


# --- intake ------------------------------------------------------------------------


def spec():
    return Catalogue.model_validate(RAW).templates["production_record"]


def test_the_employee_submission_is_mapped_and_the_missing_quantity_is_asked():
    draft = intake.evaluate("production_record", spec(), employee_submission())
    assert draft.values["output_qty"].value == "100" and "m3" in draft.values["output_qty"].note
    assert draft.values["report_month"].value == "2026-09"
    assert draft.values["date"].value == "2026-09-01"
    missing = [i for i in draft.issues if i.blocking]
    assert [(i.kind, i.field) for i in missing] == [("missing", "actual_qty")]
    assert missing[0].question == FIELDS["actual_qty"]["question"]
    assert not draft.complete and draft.checks == []  # nothing estimated from an absent input


def test_a_quantity_without_its_own_evidence_is_not_accepted():
    draft = intake.evaluate("production_record", spec(), employee_submission() + actual_answer(evidence=""))
    assert [(i.kind, i.field) for i in draft.issues if i.blocking] == [("needs_evidence", "actual_qty")]


@pytest.mark.parametrize("raw, kind", [("97.5", "ambiguous"), ("97,5 方", "invalid"), ("-1 方", "invalid"), ("97.5 吨", "invalid")])
def test_values_that_would_need_a_guess_become_questions(raw, kind):
    draft = intake.evaluate("production_record", spec(), employee_submission() + actual_answer(raw))
    assert [(i.kind, i.field) for i in draft.issues if i.blocking] == [(kind, "actual_qty")]
    assert "actual_qty" not in draft.values


def test_rival_values_are_a_conflict_until_a_person_corrects_one():
    rivals = employee_submission() + [obs(label("shipped_qty"), "99 方", ref="other.xlsx!H2")]
    draft = intake.evaluate("production_record", spec(), rivals + actual_answer())
    conflict = next(i for i in draft.issues if i.kind == "conflict")
    assert {c.value for c in conflict.candidates} == {"98", "99"} and "shipped_qty" not in draft.values
    corrected = rivals + actual_answer() + [obs(label("shipped_qty"), "98 方", kind="reply", ref="reply-2")]
    corrected[-1] = corrected[-1].model_copy(update={"correction": True})
    assert intake.evaluate("production_record", spec(), corrected).complete


def test_an_undeclared_label_is_shown_but_does_not_block():
    draft = intake.evaluate("production_record", spec(), employee_submission() + actual_answer()
                            + [obs("undeclared wording", "x")])
    assert draft.complete
    assert [i.kind for i in draft.issues] == ["unmapped"]


def test_the_declared_check_reports_a_difference_without_changing_either_value():
    draft = intake.evaluate("production_record", spec(), employee_submission() + actual_answer())
    assert draft.complete
    check = draft.checks[0]
    assert (check.value, check.attention) == ("0.5", True)
    assert (draft.values["shipped_qty"].value, draft.values["actual_qty"].value) == ("98", "97.5")


# --- lifecycle, submission and handoff ---------------------------------------------


def test_the_147_story_end_to_end(tmp_path):
    service = build(tmp_path)
    artifact = service.receive("production_record", employee_submission())
    assert artifact.view.state is ArtifactState.NEEDS_INPUT
    with pytest.raises(TransitionError):
        service.submit(artifact.id)
    with pytest.raises(TransitionError):
        service.review(artifact.id, artifact.draft.digest, "reviewer", artifact.seq)

    artifact = service.answer(artifact.id, actual_answer(), artifact.seq)
    assert artifact.view.state is ArtifactState.READY_FOR_REVIEW
    with pytest.raises(TransitionError):
        service.submit(artifact.id)  # unreviewed data never leaves
    artifact = service.review(artifact.id, artifact.draft.digest, "reviewer", artifact.seq)
    artifact = service.submit(artifact.id)

    assert artifact.view.state is ArtifactState.DATA_READY and artifact.view.receipt["record_id"]
    assert service.sink.count() == 1
    [handoff] = service.handoffs()
    assert handoff.view.state is HandoffState.WAITING and handoff.view.inputs == {"production_record": 1}
    [notice] = service.store.notifications()
    assert notice.state is NotificationState.PENDING and notice.recipient_role == RAW["stages"]["market_review"]["owner_role"]
    assert "97.5" not in notice.message  # a summary and a version, not the data

    summaries = [row.summary for row in board.project(service).rows]
    assert any("数据已就绪" in s for s in summaries) and any("待市场部处理" in s for s in summaries)

    [sent] = service.dispatch()
    assert sent.state is NotificationState.SENT
    assert service.handoffs()[0].view.state is HandoffState.WAITING  # sent is not done
    assert service.dispatch()[0].attempts == 1  # a sent notification is never sent again


def test_reviewing_a_draft_that_changed_underneath_is_refused(tmp_path):
    service = build(tmp_path)
    artifact = service.receive("production_record", employee_submission())
    stale_digest = artifact.draft.digest
    artifact = service.answer(artifact.id, actual_answer(), artifact.seq)
    with pytest.raises(StaleRead):
        service.review(artifact.id, stale_digest, "reviewer", artifact.seq)
    with pytest.raises(StaleRead):
        service.answer(artifact.id, actual_answer("97 方"), artifact.seq - 1)


def test_a_failed_write_keeps_the_draft_and_tells_nobody(tmp_path):
    service = build(tmp_path, sink=UnconfiguredSink())
    artifact = service.receive("production_record", employee_submission())
    artifact = service.answer(artifact.id, actual_answer(), artifact.seq)
    artifact = service.review(artifact.id, artifact.draft.digest, "reviewer", artifact.seq)
    artifact = service.submit(artifact.id)
    assert artifact.view.state is ArtifactState.SUBMIT_FAILED
    assert service.handoffs() == [] and service.store.notifications() == []
    [finding] = [f for f in adoption.assess(service) if f.rule == "submission_failures"]
    assert (finding.category, finding.route_to) == ("technical", "operations")


def test_a_crash_after_the_write_resumes_without_a_second_record(tmp_path):
    service = build(tmp_path)
    artifact = service.receive("production_record", employee_submission())
    artifact = service.answer(artifact.id, actual_answer(), artifact.seq)
    artifact = service.review(artifact.id, artifact.draft.digest, "reviewer", artifact.seq)

    class CrashAfterWrite:
        name = "crash"

        def submit(self, key, record):
            original.submit(key, record)
            raise RuntimeError("process died after the target accepted the record")

    original = service.sink
    service.sink = CrashAfterWrite()
    with pytest.raises(RuntimeError):
        service.submit(artifact.id)
    assert service.artifact(artifact.id).view.state is ArtifactState.SUBMITTING

    service.sink = original
    resumed = service.submit(artifact.id)
    assert resumed.view.state is ArtifactState.DATA_READY and resumed.view.receipt["replayed"] is True
    assert original.count() == 1 and len(service.store.notifications()) == 1


def test_a_revision_marks_downstream_stale_and_notifies_once_per_new_version(tmp_path):
    service = build(tmp_path)
    artifact_id = ready(service)
    artifact = service.artifact(artifact_id)
    artifact = service.answer(artifact_id, actual_answer("97 方", "DEMO-CONFIRM-002"), artifact.seq)
    assert artifact.view.version == 2 and artifact.view.state is ArtifactState.READY_FOR_REVIEW
    assert service.handoffs()[0].view.stale is True

    artifact = service.review(artifact_id, artifact.draft.digest, "reviewer", artifact.seq)
    service.submit(artifact_id)
    [handoff] = service.handoffs()
    assert handoff.view.inputs == {"production_record": 2} and handoff.view.stale
    assert len(service.store.notifications()) == 2
    assert service.sink.count() == 2  # a new version is a new record, the old one is kept

    handoff = service.act(handoff.id, "acknowledge", "", handoff.seq)
    assert handoff.view.stale is False


def test_downstream_actions_follow_the_handoff_machine(tmp_path):
    service = build(tmp_path)
    ready(service)
    [handoff] = service.handoffs()
    with pytest.raises(TransitionError):
        service.act(handoff.id, "complete", "", handoff.seq)
    with pytest.raises(TransitionError, match="reason"):
        service.act(handoff.id, "return", " ", handoff.seq)
    handoff = service.act(handoff.id, "start", "", handoff.seq)
    handoff = service.act(handoff.id, "return", "实际量依据不清", handoff.seq)
    assert handoff.view.state is HandoffState.RETURNED
    [finding] = [f for f in adoption.assess(service) if f.rule == "returned_work"]
    assert finding.route_to == "agent_1_workflow"


def test_a_completion_keeps_the_confirmation_it_rests_on(tmp_path):
    service = build(tmp_path)
    ready(service)
    [handoff] = service.handoffs()
    started = service.act(handoff.id, "start", "", handoff.seq)
    record_output(service)
    done = service.act(handoff.id, "complete", "市场部负责人确认已处理", started.seq)
    assert done.view.state is HandoffState.COMPLETED and done.view.reason == "市场部负责人确认已处理"


def test_a_notification_that_keeps_failing_is_abandoned_while_the_data_stays_ready(tmp_path):
    class Down:
        name = "down"

        def deliver(self, role, message, dedupe):
            raise SinkError("channel unreachable")

    service = build(tmp_path, notifier=Down())
    artifact_id = ready(service)
    states = [service.dispatch()[0].state for _ in range(3)]
    assert states == [NotificationState.FAILED, NotificationState.FAILED, NotificationState.ABANDONED]
    assert service.artifact(artifact_id).view.state is ArtifactState.DATA_READY
    assert any("通知发送失败" in row.summary for row in board.project(service).rows)


def test_partial_inputs_are_shown_as_partial_and_nobody_is_told_ready(tmp_path):
    raw = copy.deepcopy(RAW)
    second = copy.deepcopy(raw["templates"]["production_record"])
    second.update(title="第二份输入", checks=[])
    raw["templates"]["second_input"] = second
    raw["stages"]["market_review"]["inputs"] = ["production_record", "second_input"]
    service = build(tmp_path, raw=raw)
    ready(service)
    assert service.handoffs() == [] and service.store.notifications() == []
    [partial] = [row for row in board.project(service).rows if row.kind == "partial"]
    assert partial.awaiting == ["second_input"] and "仍待" in partial.summary


# --- adoption ----------------------------------------------------------------------


def test_adoption_signals_stay_at_stage_level_and_name_who_decides(tmp_path):
    clock = Clock()
    service = build(tmp_path, clock=clock)
    artifact = service.receive("production_record", employee_submission())
    for value in ("97 吨", "97", "97.5 方"):
        artifact = service.answer(artifact.id, actual_answer(value), artifact.seq)
    artifact = service.review(artifact.id, artifact.draft.digest, "reviewer", artifact.seq)
    service.submit(artifact.id)
    clock.now += timedelta(hours=RAW["stages"]["market_review"]["sla_hours"] + 1)

    findings = {f.rule: f for f in adoption.assess(service)}
    assert findings["repeated_questions"].route_to == "agent_2_template"
    assert findings["idle_handoffs"].decided_by == RAW["stages"]["market_review"]["owner_role"]
    for finding in findings.values():
        assert set(finding.scope) <= {"department", "stage", "template", "channel"}
        assert "reviewer" not in json.dumps(finding.model_dump(), ensure_ascii=False)


# --- materials ---------------------------------------------------------------------


def workbook(rows) -> bytes:
    import openpyxl
    book = openpyxl.Workbook()
    for row in rows:
        book.active.append(row)
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def test_a_header_only_template_is_recognised_as_having_no_data():
    labels = [f["label"] for f in FIELDS.values()]
    shape = materials.inspect("t.xlsx", workbook([["X月生产报表"], labels]))
    [sheet] = shape.sheets
    assert shape.header_only and sheet.title == "X月生产报表" and sheet.header_row == 2 and sheet.labels == labels


def test_inspection_counts_data_rows_without_returning_them():
    labels = [f["label"] for f in FIELDS.values()]
    shape = materials.inspect("t.xlsx", workbook([labels, ["SECRET-VALUE-1"] * len(labels)]))
    assert not shape.header_only and shape.sheets[0].data_rows == 1
    assert "SECRET-VALUE-1" not in shape.model_dump_json()


# --- HTTP ---------------------------------------------------------------------------


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "workflow_catalogue_path", str(DEMO))
    with TestClient(app) as client:
        yield client


def test_the_api_refuses_to_run_without_a_catalogue(client, monkeypatch):
    monkeypatch.setattr(settings, "workflow_catalogue_path", "")
    assert client.get("/workflow/board").status_code == 503


def test_review_over_http_needs_a_fresh_approval_bound_to_the_request(client):
    payload = {"template": "production_record",
               "observations": [o.model_dump() for o in employee_submission() + actual_answer()]}
    artifact = client.post("/workflow/artifacts", json=payload)
    assert artifact.status_code == 201, artifact.text
    body = artifact.json()
    assert body["state"] == "ready_for_review"
    request = json.dumps({"digest": body["digest"], "expected_seq": body["seq"]}, separators=(",", ":")).encode()
    url = f"/workflow/artifacts/{body['id']}/review"
    assert client.post(url, content=request, headers={"content-type": "application/json"}).status_code == 403
    reviewed = client.post(url, content=request, headers={"content-type": "application/json",
                                                           "x-bridgeflow-approval": receipt(request)})
    assert reviewed.status_code == 200 and reviewed.json()["state"] == "reviewed"
    submitted = client.post(f"/workflow/artifacts/{body['id']}/submit")
    assert submitted.json()["state"] == "data_ready"
    rows = client.get("/workflow/board").json()["rows"]
    assert {row["kind"] for row in rows} == {"artifact", "handoff"}
    # The next team's notice goes out with the submission instead of waiting for a
    # dispatcher that nothing runs.
    assert next(row for row in rows if row["kind"] == "handoff")["notification"] == "sent"


def test_the_sample_workflow_only_receives_and_leaves_approval_to_a_person(client):
    loaded = client.post("/workflow/sample")
    assert loaded.status_code == 200, loaded.text
    artifacts = [row for row in loaded.json()["rows"] if row["kind"] == "artifact"]
    # Production: one missing its confirmed quantity, one complete; marketing's settlement
    # basis for the second hop is complete too. None of them is approved.
    assert sorted((row["template"], row["state"]) for row in artifacts) == [
        ("production_record", "needs_input"), ("production_record", "ready_for_review"),
        ("settlement_basis", "ready_for_review")]
    assert not [row for row in loaded.json()["rows"] if row["kind"] == "handoff"]
    # A workflow that already holds records is left alone.
    assert client.post("/workflow/sample").status_code == 409


def test_the_sample_is_refused_under_any_other_catalogue(client, monkeypatch, tmp_path):
    other = dict(RAW, version="someone-else-1")
    path = tmp_path / "catalogue.yaml"
    path.write_text(yaml.safe_dump(other, allow_unicode=True), encoding="utf-8")
    monkeypatch.setattr(settings, "workflow_catalogue_path", str(path))
    refused = client.post("/workflow/sample")
    assert refused.status_code == 409 and "demo catalogue" in refused.json()["detail"]


def test_no_business_name_is_written_into_the_workflow_code():
    names = {f["label"] for t in RAW["templates"].values() for f in t["fields"].values()}
    names |= {k for t in RAW["templates"].values() for k in t["fields"] if "_" in k}
    for path in [*Path(catalogue.__file__).parent.glob("*.py"), REPO_ROOT / "backend/src/bridgeflow/api/workflow.py"]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            holder = isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
            if holder and ast.get_docstring(node) is not None:
                node.body = node.body[1:] or [ast.Pass()]
        code = ast.unparse(tree)
        for name in names:
            assert name not in code, f"{name} is written into {path.name}"


@pytest.mark.parametrize("started", [False, True])
def test_revision_must_be_ready_and_acknowledged_before_work_continues(tmp_path, started):
    service = build(tmp_path)
    artifact_id = ready(service)
    handoff = service.handoffs()[0]
    if started:
        handoff = service.act(handoff.id, "start", "", handoff.seq)
    artifact = service.artifact(artifact_id)
    artifact = service.answer(artifact_id, actual_answer("96 方"), artifact.seq)
    handoff = service.handoff(handoff.id)
    action = "complete" if started else "start"
    with pytest.raises(TransitionError, match="Acknowledge"):
        service.act(handoff.id, action, "", handoff.seq)
    with pytest.raises(TransitionError, match="not ready"):
        service.act(handoff.id, "acknowledge", "", handoff.seq)
    assert service.handoff(handoff.id).seq == handoff.seq
    artifact = service.review(artifact_id, artifact.draft.digest, "reviewer", artifact.seq)
    service.submit(artifact_id)
    handoff = service.handoff(handoff.id)
    with pytest.raises(TransitionError, match="Acknowledge"):
        service.act(handoff.id, action, "", handoff.seq)
    handoff = service.act(handoff.id, "acknowledge", "", handoff.seq)
    assert not handoff.view.stale
    if started:
        record_output(service)
    assert service.act(handoff.id, action, "", handoff.seq).view.state == (
        HandoffState.COMPLETED if started else HandoffState.IN_PROGRESS)


def test_a_handoff_is_due_by_its_stage_limit_and_overdue_only_while_open(tmp_path):
    clock = Clock()
    service = build(tmp_path, clock=clock)
    ready(service)
    limit = RAW["stages"]["market_review"]["sla_hours"]
    [row] = [r for r in board.project(service).rows if isinstance(r, board.HandoffRow)]
    assert row.overdue_hours == -limit  # hours left, counted from when it was handed over
    clock.now += timedelta(hours=limit + 5)
    [row] = [r for r in board.project(service).rows if isinstance(r, board.HandoffRow)]
    assert row.overdue_hours == 5 and row.due_at.startswith("2026-09-")
    [handoff] = service.handoffs()
    handoff = service.act(handoff.id, "start", "", handoff.seq, by="示例-市场部")
    record_output(service)
    service.act(handoff.id, "complete", "已核对", handoff.seq, by="示例-市场部")
    [row] = [r for r in board.project(service).rows if isinstance(r, board.HandoffRow) and r.stage == "market_review"]
    assert row.overdue_hours is None  # finished work is not overdue, however late it was


def test_a_timeline_says_who_did_what_and_when_but_never_the_values(tmp_path):
    service = build(tmp_path)
    artifact_id = ready(service)
    [handoff] = service.handoffs()
    service.act(handoff.id, "start", "", handoff.seq, by="示例-市场部")
    steps = service.history("artifact", artifact_id)
    assert [s["type"] for s in steps][:2] == ["material_received", "answer_provided"]
    assert steps[0]["detail"].endswith("field(s)")
    assert "97.5" not in json.dumps(steps, ensure_ascii=False)  # the draft view shows values; the timeline does not
    [opened, started] = service.history("handoff", handoff.id)
    assert opened["type"] == "handoff_opened" and "production_record v1" in opened["detail"]
    assert started["by"] == "示例-市场部"


def test_a_stage_that_produces_a_record_cannot_complete_before_that_record_is_recorded(tmp_path):
    service = build(tmp_path)
    ready(service)
    [handoff] = service.handoffs()
    handoff = service.act(handoff.id, "start", "", handoff.seq)
    [row] = [r for r in board.project(service).rows if isinstance(r, board.HandoffRow)]
    assert row.awaiting_outputs == ["settlement_basis"] and "入库后才能完成" in row.summary
    with pytest.raises(TransitionError, match="not recorded"):
        service.act(handoff.id, "complete", "市场部负责人确认已处理", handoff.seq)
    record_output(service, project="演示项目B")  # another project's output does not count
    with pytest.raises(TransitionError, match="not recorded"):
        service.act(handoff.id, "complete", "市场部负责人确认已处理", handoff.seq)
    record_output(service)
    rows = board.project(service).rows
    [market] = [r for r in rows if isinstance(r, board.HandoffRow) and r.stage == "market_review"]
    assert market.awaiting_outputs == []
    assert service.act(handoff.id, "complete", "市场部负责人确认已处理", handoff.seq).view.state is HandoffState.COMPLETED
    assert any(isinstance(r, board.HandoffRow) and r.stage == "finance_settlement" for r in rows)  # the second hop opened
