import assert from 'node:assert/strict'
import { test } from 'node:test'

import { cellText, columnLabel, describeFailure, failureReason } from '../src/client/ui.ts'

const t = (key: string) => ({ finance: '财务', production: '生产' }[key] ?? key)

test('a column header keeps its department out of the field name', () => {
  // Rendered as one string these wrapped a character per line in a narrow column,
  // which is not a styling complaint: the header became unreadable.
  assert.deepEqual(columnLabel('finance.ar_days', t), { group: '财务', label: 'ar days' })
  assert.deepEqual(columnLabel('period_from', t), { group: '', label: 'period from' })
})

test('an entity id reads as the identifier, with its kind as the caption', () => {
  const { text, note } = cellText('customer:acme-pte-ltd')
  assert.equal(text, 'acme-pte-ltd')
  assert.equal(note, 'customer')
})

test('a rollup decision is a sentence, not a JSON blob', () => {
  // `{"finance.amount":"sum","finance.gl_account":"disagreed"}` was printed verbatim
  // into a business table and an operator was asked to sign off on it.
  const { text } = cellText({ 'finance.amount': 'sum', 'finance.gl_account': 'disagreed' })
  assert.equal(text, 'amount = sum; gl_account = disagreed')
})

test('a long list says how much it is not showing', () => {
  const { text, note } = cellText(['a', 'b', 'c', 'd', 'e'])
  assert.equal(text, 'a、b、c')
  assert.equal(note, '+2')
})

test('figures are marked as figures so the column can align them', () => {
  assert.deepEqual(cellText(11700), { text: '11,700', numeric: true, empty: false })
  assert.equal(cellText('4000-SALES-A1').numeric, false)
})

test('an absent value is visibly absent rather than blank', () => {
  for (const value of [null, undefined, '']) {
    const cell = cellText(value)
    assert.equal(cell.text, '—')
    assert.equal(cell.empty, true)
  }
})

test('clipping keeps the whole value reachable', () => {
  // Shortening a business value without keeping the original is a lie the table
  // tells quietly, so the full text travels with the clipped one.
  const long = 'batch label — this row carries no readable date and the rest of a very long explanation'
  const { text, full } = cellText(long)
  assert.ok(text.endsWith('…'))
  assert.equal(full, long)
})

test('zero is a figure, not an absence', () => {
  const cell = cellText(0)
  assert.equal(cell.text, '0')
  assert.equal(cell.empty, false)
})

test('our own view keys translate while business field names stay as declared', () => {
  const t = (key: string) => ({ view_candidate: '已声明候选列', finance: '财务' } as Record<string, string>)[key] ?? key
  assert.deepEqual(columnLabel('candidate', t), { group: '', label: '已声明候选列' })
  assert.deepEqual(columnLabel('finance.ar_days', t), { group: '财务', label: 'ar days' })
  assert.deepEqual(columnLabel('output_qty', t), { group: '', label: 'output qty' })
})

test('a figure shortened for display is marked approximate and keeps its exact value', () => {
  assert.deepEqual(cellText(97.5), { text: (97.5).toLocaleString(undefined, { maximumFractionDigits: 4 }), numeric: true, empty: false })
  const long = cellText(0.123456789)
  assert.equal(long.text.startsWith('≈'), true)
  assert.equal(long.full, '0.123456789')
})

test('a failure keeps its three parts instead of one flattened sentence', () => {
  // Heading, what it means for the reader, then the service's own words (docs/design
  // 12-states E03). Flattened into `操作未完成：<stack>` the middle part disappears and
  // the last one reads like a crash.
  const t = (key: string) => ({ requestFailed: '操作未完成', networkFailed: '连接不上服务',
    networkFailedTitle: '连接中断' } as Record<string, string>)[key] ?? key
  assert.deepEqual(describeFailure(new Error('Batch not found'), t),
    { title: '操作未完成', body: '', detail: 'Batch not found' })
  assert.deepEqual(describeFailure(new TypeError('Failed to fetch'), t),
    { title: '连接中断', body: '连接不上服务', detail: '' })
  // Somebody's own sentence is the body as written — no heading is invented over it.
  assert.deepEqual(describeFailure('请选择当前纪要中的候选', t),
    { title: '', body: '请选择当前纪要中的候选', detail: '' })
})

test('a withheld access check is worded as withheld, and only when the service says so', () => {
  // "Cannot be confirmed" and "denied" send a user to entirely different next steps
  // (docs/design 01-portal P10). The status code alone cannot tell them apart: a 503
  // is also how half the service says "not configured", so the reason is read from
  // x-bridgeflow-reason and never inferred.
  const t = (key: string) => ({ requestFailed: '操作未完成',
    accessUnavailableTitle: '暂时无法确认你的访问范围', accessUnavailableBody: '这不表示你没有权限。',
    accessUnconfiguredTitle: '访问范围尚未配置', accessUnconfiguredBody: '重试不会有帮助。',
  } as Record<string, string>)[key] ?? key
  const tagged = (reason: string) => Object.assign(new Error('Access control could not reach Feishu: timeout'),
    { status: 503, reason })
  assert.deepEqual(describeFailure(tagged('access_unavailable'), t), {
    title: '暂时无法确认你的访问范围', body: '这不表示你没有权限。',
    detail: 'Access control could not reach Feishu: timeout',
  })
  assert.equal(describeFailure(tagged('access_unconfigured'), t).title, '访问范围尚未配置')
  assert.equal(failureReason(tagged('access_unavailable')), 'access_unavailable')

  // An untagged 503 is somebody else's 503 and stays the generic failure.
  const untagged = Object.assign(new Error('Integration declaration is not configured'), { status: 503 })
  assert.deepEqual(describeFailure(untagged, t),
    { title: '操作未完成', body: '', detail: 'Integration declaration is not configured' })
  assert.equal(failureReason(untagged), '')
})
