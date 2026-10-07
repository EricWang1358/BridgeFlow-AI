// A tool's render is all the model sees of its result. When a later call needs an id, a
// seq, a digest or a version from that result, the render must carry it — otherwise the
// call is impossible for a real model, while a scripted test model (which reads the raw
// value) passes. That is how workflow submission and dictionary decisions went unusable.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { renderBoard, renderDraft } from '../src/tools/workflow.ts'
import { renderChecklist } from '../src/tools/checklist.ts'
import { renderDraftEntries } from '../src/tools/dictionary.ts'
import { renderDispositions } from '../src/tools/dispositions.ts'
import { memorySave, renderMemories, saveBody } from '../src/tools/memory.ts'

const text = (blocks: { text: string }[]) => blocks.map(b => b.text).join('\n')

test('workflow_draft shows the id, seq and digest that record and approve_submit take', () => {
  const out = text(renderDraft({ artifact_id: 'a'.repeat(32), seq: 4, digest: 'd1g3st', state: 'ready_for_review',
    values: { 实际量: '116.5 (m3)' } }))
  for (const handle of ['a'.repeat(32), 'seq=4', 'd1g3st', '实际量=116.5 (m3)']) assert.match(out, new RegExp(handle.replace(/[()]/g, '\\$&')))
})

test('workflow_board shows each row id and seq that workflow_handoff takes', () => {
  const out = text(renderBoard({ rows: [{ kind: 'handoff', id: 'h-1', seq: 2, state: 'waiting', summary: '待市场部处理' }] }))
  assert.match(out, /id=h-1 seq=2 state=waiting/)
})

test('workflow_board says which output a handoff still owes before it can complete', () => {
  const out = text(renderBoard({ rows: [{ kind: 'handoff', id: 'h-2', seq: 3, state: 'in_progress', summary: '处理中', awaiting_outputs: ['settlement_basis'] }] }))
  assert.match(out, /cannot_complete_until_recorded=settlement_basis/)
})

test('dictionary_draft_view shows the entry_id that dictionary_decide takes', () => {
  const out = text(renderDraftEntries({ entries: [{ entry_id: 'e-7', department: 'finance', column: '项目编号', role: 'entity:project', decision: 'pending', evidence: '重合 100%' }] }))
  assert.match(out, /\[e-7\]/)
})

test('risk_dispositions shows the version that risk_disposition_record checks', () => {
  const out = text(renderDispositions({ open: 1, dispositions: [{ check_id: 'net_margin', state: '待确认', version: 3, available: ['confirm'] }] }))
  assert.match(out, /net_margin v3/)
})

test('monthly_inbox lists the items and the filter, not only counts', async () => {
  const { renderInbox } = await import('../src/tools/checklist.ts')
  const out = text(renderInbox({ department: 'finance' }, { total: 2, by_kind: { master_disagreement: 1, missing_provenance: 1 },
    batch_id: 'selected-notebook-batch',
    items: [{ kind: 'master_disagreement', subject: '客户名称', detail: '生产部与市场部不一致', departments: ['production', 'marketing'], next_view: 'integration' }] }))
  assert.match(out, /in batch selected-notebook-batch/)
  assert.match(out, /Filtered by department=finance: 1 listed/)
  assert.match(out, /master_disagreement: 客户名称 — 生产部与市场部不一致 \[departments: production\/marketing; settled in: integration\]/)
})

test('integration_summary lists open items and conventions, not only counts', async () => {
  const { renderIntegration } = await import('../src/tools/integration.ts')
  const out = text(renderIntegration({ rows: 4, complete_rows: 3, issues_by_kind: { disagreement: 1 },
    open_items: [{ kind: 'disagreement', field: '客户名称', departments: ['production', 'marketing'] }],
    assumptions: { vat_rate: '增值税按 13%' }, convention_states: { vat_rate: 'unconfirmed' }, next_step: 'Explain who decides.' }))
  assert.match(out, /- disagreement: 客户名称 \[departments: production\/marketing\]/)
  assert.match(out, /- vat_rate \(unconfirmed\): 增值税按 13%/)
  assert.match(out, /Explain who decides\./)
})

test('compare_periods says which months a figure covers and why a figure is missing', async () => {
  const { renderComparison } = await import('../src/tools/compare-periods.ts')
  const refused = text(renderComparison({ grain: 'quarter', period: '2024-Q3', base_kind: 'prior', base_period: '2024-Q2', status: 'no_base',
    reason: '2024-Q2 lacks 2024-04', current: { coverage: { present: ['2024-07'], missing: [], complete: false },
      facts: [{ metric: 'net_margin', unit: '%', value: 4.2, state: 'computed' },
              { metric: 'receivable_months', state: 'month_only', reason: 'needs its own convention' }] },
    base: { coverage: { present: [], missing: ['2024-04'] } }, changes: [] }))
  assert.match(refused, /2024-Q3 \(quarter\) against prior 2024-Q2: no_base — 2024-Q2 lacks 2024-04/)
  assert.match(refused, /months in 2024-Q3: 2024-07 \(incomplete period\)/)
  assert.match(refused, /- receivable_months: month_only — needs its own convention/)
  const compared = text(renderComparison({ grain: 'month', period: '2024-07', base_kind: 'prior', base_period: '2024-06', status: 'compared',
    current: { coverage: { present: ['2024-07'], complete: true } }, base: { coverage: { present: ['2024-06'], complete: true } },
    changes: [{ metric: 'net_margin', unit: '%', current: 4.2, base: 5, absolute: -0.8, basis: 'percentage_points', state: 'compared' }] }))
  assert.match(compared, /- net_margin: 4.2 % against 5; change -0.8 pt/)
})

test('workflow_scope shows the ids and decision_seq that workflow_accept_scope takes, and staleness', async () => {
  const { renderScope } = await import('../src/tools/workflow.ts')
  const waiting = text(renderScope({ accepted: null, current: false, stale_reasons: [], runnable_candidates: ['production_to_marketing_handoff'],
    pending: [{ project_id: 'demo-handoff', decision_id: 'mvp', decision_seq: 4, scope: ['试点'], candidates: ['production_to_marketing_handoff'] }] }))
  assert.match(waiting, /project_id=demo-handoff decision_id=mvp decision_seq=4/)
  const stale = text(renderScope({ accepted: { project_id: 'demo-handoff', decision_id: 'mvp', decision_seq: 4, scope: ['试点'], exclusions: [] },
    current: false, stale_reasons: ['decision_revised'], runnable_candidates: [] }))
  assert.match(stale, /STALE \(decision_revised\)/)
})

test('monthly_checklist names the batch a month is bound to, so a month without an id can be looked up', () => {
  const out = text(renderChecklist({ period: '2024-07', batch_id: 'b'.repeat(32), ready_to_close: false,
    steps: [{ id: 'review', state: 'open', count: 1, owner_role: '总经办' }] }))
  assert.match(out, /2024-07 \(batch_id=b{32}\)/)
})

test('memory_search shows the id and version memory_save revises, and the solution itself', () => {
  const out = text(renderMemories({ memories: [{ id: 'mem-1a2b3c4d', version: 2, title: '运费混入单价', problem: '材料成本虚高',
    solution: '按备注列识别运费行', source: '采购部例会纪要', departments: ['procurement'] }] }))
  for (const handle of ['mem-1a2b3c4d v2', '按备注列识别运费行', '材料成本虚高', '采购部例会纪要', 'procurement']) assert.match(out, new RegExp(handle))
  assert.match(text(renderMemories({ memories: [], next_step: 'No saved memory matches.' })), /No saved memory/)
})

test('memory_save signs the same body it sends and refuses an incomplete memory before approval', () => {
  const args = { title: 't', problem: 'p', solution: 's', source: 'src', departments: ['finance'] }
  assert.equal(JSON.stringify(saveBody(args, 'captain', 'c1')), JSON.stringify(saveBody(args, 'captain', 'c1')))
  assert.equal(saveBody(args, 'captain', 'c1').memory_id, null)
  const access = memorySave({ baseUrl: 'http://x', timeoutMs: 1 }, {} as never).access
  assert.ok(access.kind === 'approval' && access.precheck)
  assert.equal(access.precheck(args), null)
  assert.match(String(access.precheck({ ...args, source: ' ' })), /source/)
})
