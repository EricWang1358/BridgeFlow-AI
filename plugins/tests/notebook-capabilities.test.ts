import assert from 'node:assert/strict'
import test from 'node:test'
import { isNotebookKind, notebookKinds, notebookPurpose } from '../src/notebook-capabilities.ts'
import { parseNotebook } from '../src/notebooks.ts'

test('each declared purpose persists and resolves the same workflow set', () => {
  for (const kind of notebookKinds) {
    const saved = parseNotebook({ title: 'Business notebook', kind, view: 'state' })
    assert.equal(saved.kind, kind)
    assert.deepEqual(notebookPurpose(saved.kind), notebookPurpose(kind))
  }
  assert.deepEqual(notebookPurpose('quotation').workflows, ['quotation'])
  assert.deepEqual(notebookPurpose('monthly').workflows, ['monthly'])
  assert.deepEqual(notebookPurpose(undefined).workflows, ['quotation', 'monthly'])
})

test('untrusted kind values cannot impersonate a purpose through coercion or object prototypes', () => {
  for (const kind of [['monthly'], { toString: () => 'monthly' }, 'toString', '__proto__', 'unknown']) {
    assert.equal(isNotebookKind(kind), false)
    assert.throws(() => parseNotebook({ title: 'Invalid', kind }), /Invalid notebook kind/)
  }
})
