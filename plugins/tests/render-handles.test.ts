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
