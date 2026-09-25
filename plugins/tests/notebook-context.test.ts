import test from 'node:test'
import assert from 'node:assert/strict'
import { notebookContextText, parseViewing } from '../src/notebook-context.ts'

const batch = 'a'.repeat(32)

test('the captain is told the notebook\'s batch, or that it has none, and what is company-wide', () => {
  const bound = notebookContextText({ batch, kind: 'monthly' }, null)
  assert.match(bound, new RegExp(`bound to batch ${batch}`))
  assert.match(bound, /purpose: monthly/)
  assert.match(bound, /handoff board and discovery projects are company-wide/)
  assert.match(bound, /grants nothing/)
  assert.match(notebookContextText({ batch: null }, null), /has no data yet; no batch is bound/)
  // The live page outranks the saved record; with neither, nothing is claimed.
  assert.match(notebookContextText({ batch: null }, { title: 'x', batch }), /has no data yet/)
  assert.match(notebookContextText(undefined, { title: 'Free text is never passed', batch }), new RegExp(batch))
  assert.doesNotMatch(notebookContextText(undefined, { title: 'Free text is never passed', batch }), /Free text/)
  assert.equal(notebookContextText(undefined, null), '')
})

test('a page report is validated, never guessed at', () => {
  assert.deepEqual(parseViewing({ batch, kind: 'monthly' }), { batch, kind: 'monthly' })
  assert.deepEqual(parseViewing({ batch: '' }), { batch: null })
  assert.equal(parseViewing({ batch: 'not-a-batch' }), null)
  assert.equal(parseViewing({ batch, kind: 'bogus' }), null)
  assert.equal(parseViewing('x'), null)
})
