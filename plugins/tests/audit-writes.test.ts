import test from 'node:test'
import assert from 'node:assert/strict'
import { projectAudit, type AuditEvent } from '../src/client/audit.ts'

const at = (type: string, data: Record<string, unknown>): AuditEvent => ({ type, time: 0, data })
const result = (callId: string): AuditEvent => at('tool/result', { message: { content: [{ type: 'tool-result', toolCallId: callId, content: [{ type: 'text', text: '{}' }] }] } })

test('a write counts once it was allowed and has returned; a rejection or a read does not', () => {
  const events = [
    at('approval/asked', { id: 'a1', callId: 'c1', toolName: 'confirm_column_match' }),
    at('approval/decided', { id: 'a1', outcome: 'allowed-once' }),
    at('approval/asked', { id: 'a2', callId: 'c2', toolName: 'convention_decide' }),
    at('approval/decided', { id: 'a2', outcome: 'rejected' }),
    result('c2'), result('c3'),
  ]
  assert.equal(projectAudit(events).writes, 0, 'allowed but not returned yet')
  assert.equal(projectAudit([...events, result('c1')]).writes, 1)
})
