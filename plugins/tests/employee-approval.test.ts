import assert from 'node:assert/strict'
import { createHash, createHmac } from 'node:crypto'
import test from 'node:test'
import type { Agent } from '@deepseek-ai/dsh-agent'
import { ApprovalNotes } from '../src/approval/notes.ts'
import { ApprovalReceipts } from '../src/approval/receipts.ts'

const agent = { id: 'session-a' } as Agent

test('employee proof belongs to the exact pending session and call and disappears on settlement', () => {
  const notes = new ApprovalNotes()
  const body = JSON.stringify({ artifact_id: 'abc', expected_seq: 3 })
  const close = notes.open(agent, 'call-1', { operation: 'workflow_record', body })
  const ticket = notes.ticket(agent.id, 'call-1')!
  assert.equal(notes.write('session-b', 'call-1', ticket), undefined)
  assert.equal(notes.write(agent.id, 'call-1', 'forged-ticket'), undefined)
  assert.deepEqual(notes.write(agent.id, 'call-1', ticket), { operation: 'workflow_record', body })
  assert.equal(notes.authorize(agent.id, 'call-1', ticket, 'permit-a', 'alice'), true)
  assert.equal(notes.authorize(agent.id, 'call-1', ticket, 'permit-b', 'bob'), false)
  assert.equal(notes.permit(agent.id, 'call-1'), 'permit-a')
  close()
  assert.equal(notes.permit(agent.id, 'call-1'), undefined)
  assert.equal(notes.authorize(agent.id, 'call-1', ticket, 'late', 'alice'), false)
})

test('native receipt signature binds the backend employee permit as well as exact request bytes', () => {
  const original = process.env.BRIDGEFLOW_SERVICE_TOKEN
  process.env.BRIDGEFLOW_SERVICE_TOKEN = 'employee-approval-test-secret-32-characters'
  try {
    const receipts = new ApprovalReceipts()
    const body = { handoff_id: 'stage:abc', action: 'start', expected_seq: 2 }
    receipts.authorize('call', body, 'a'.repeat(64))
    const value = receipts.take('call')
    const [stamp, nonce, signature, permit] = value.split('.')
    assert.equal(permit, 'a'.repeat(64))
    const digest = createHash('sha256').update(JSON.stringify(body)).digest('hex')
    const signed = `${stamp}.${nonce}.${digest}.${permit}`
    assert.equal(signature, createHmac('sha256', process.env.BRIDGEFLOW_SERVICE_TOKEN).update(signed).digest('hex'))
    assert.throws(() => receipts.take('call'), /No current approval/)
    assert.notEqual(signature, createHmac('sha256', process.env.BRIDGEFLOW_SERVICE_TOKEN)
      .update(`${stamp}.${nonce}.${digest}.${'b'.repeat(64)}`).digest('hex'))
  } finally {
    if (original === undefined) delete process.env.BRIDGEFLOW_SERVICE_TOKEN
    else process.env.BRIDGEFLOW_SERVICE_TOKEN = original
  }
})
