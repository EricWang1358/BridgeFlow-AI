import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { settlePlaybook } from '../src/settle-playbook.ts'
import { renderInbox } from '../src/tools/checklist.ts'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const backend = readFileSync(`${root}/backend/src/bridgeflow/integration.py`, 'utf8') + readFileSync(`${root}/backend/src/bridgeflow/monthly/inbox.py`, 'utf8')
const tools = readdirSync(`${root}/plugins/src/tools`).map(f => readFileSync(`${root}/plugins/src/tools/${f}`, 'utf8')).join('\n')
  + readFileSync(`${root}/plugins/src/tools/review-batch.ts`, 'utf8')

test('every kind of open item says how it is settled, in both languages', () => {
  const master = [...backend.matchAll(/Issue\(kind="([a-z_]+)"/g)].map(m => `master_${m[1]}`)
  const inbox = [...readFileSync(`${root}/backend/src/bridgeflow/monthly/inbox.py`, 'utf8').matchAll(/kind="([a-z_]+)"/g)].map(m => m[1]!)
  for (const kind of new Set([...master, ...inbox])) {
    const entry = settlePlaybook[kind]
    assert.ok(entry, `${kind} has no settle entry`)
    assert.ok(/[一-鿿]/.test(entry.how[0]) && !/[一-鿿]/.test(entry.how[1]), `${kind}: zh then en`)
  }
})

test('the playbook names only real captain tools and no business field names', () => {
  for (const [kind, entry] of Object.entries(settlePlaybook)) for (const tool of entry.captain ?? [])
    assert.ok(tools.includes(`'${tool}'`), `${kind}: ${tool} is not a tool`)
  const spec = readFileSync(`${root}/data/company_templates/integration.yaml`, 'utf8')
  const fields = [...spec.matchAll(/^ {2}([^\s:#][^:]*):$/gm)].map(m => m[1]!).filter(f => /[一-鿿]/.test(f))
  const text = JSON.stringify(settlePlaybook)
  assert.deepEqual(fields.filter(f => text.includes(f)), [])
})

test('monthly_inbox tells the captain how each item is settled and what it may start', () => {
  const [block] = renderInbox({ period: '2024-07' }, { total: 2, batch_id: 'b', by_kind: {}, items: [
    { kind: 'column_question', subject: 'x', detail: '', departments: ['finance'], next_view: 'columns' },
    { kind: 'master_disagreement', subject: 'y', detail: '', departments: ['production'], next_view: 'integration' }] } as never)
  assert.match(block!.text, /how to settle: An uploaded column/)
  assert.match(block!.text, /Captain can start: column_candidates, confirm_column_match \(ask first\)/)
  assert.match(block!.text, /A person does it; the captain can only suggest/)
})
