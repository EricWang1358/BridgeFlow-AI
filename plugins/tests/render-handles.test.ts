// A tool's render is all the model sees of its result. When a later call needs an id, a
// seq, a digest or a version from that result, the render must carry it — otherwise the
// call is impossible for a real model, while a scripted test model (which reads the raw
// value) passes. That is how workflow submission and dictionary decisions went unusable.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { renderBoard, renderDraft } from '../src/tools/workflow.ts'
import { renderDraftEntries } from '../src/tools/dictionary.ts'
import { renderDispositions } from '../src/tools/dispositions.ts'

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
    items: [{ kind: 'master_disagreement', subject: '客户名称', detail: '生产部与市场部不一致', departments: ['production', 'marketing'], next_view: 'integration' }] }))
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
