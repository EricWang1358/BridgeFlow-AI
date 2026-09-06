import assert from 'node:assert/strict'
import { test } from 'node:test'

import { cellText, columnLabel } from '../src/client/ui.ts'

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
