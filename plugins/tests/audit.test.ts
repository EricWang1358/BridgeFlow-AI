import test from 'node:test'
import assert from 'node:assert/strict'
import { projectAudit, selectReview, type AuditEvent } from '../src/client/audit.ts'
const event = (type: string, time: number, data: Record<string, unknown>): AuditEvent => ({ type, time, data })
test('state projection scopes Spawn counts to the latest review and keeps truthful partial status', () => {
  const result = projectAudit([
    event('bridgeflow/review', 1, { review_id: 'old', batch_id: 'a', status: 'dispatching' }),
    event('tool/call', 2, { name: 'subagent', callId: 'old-call' }),
    event('bridgeflow/review', 3, { review_id: 'new', batch_id: 'b', status: 'dispatching' }),
    event('tool/call', 4, { name: 'subagent', callId: 'new-call' }),
    event('bridgeflow/review', 5, { review_id: 'new', batch_id: 'b', status: 'partial', report_id: 'report' }),
  ])
  assert.equal(result.review?.status, 'partial')
  assert.deepEqual(result.calls.map(c => c.data.callId), ['new-call'])
})
test('approval notes join by call identity and outcomes by approval identity', () => {
  const result = projectAudit([
    event('approval/asked', 1, { id: 'a', callId: 'call-a', toolName: 'confirm_mapping' }),
    event('approval/asked', 2, { id: 'b', callId: 'call-b', toolName: 'confirm_mapping' }),
    event('bridgeflow/approval-note', 3, { callId: 'call-b', note: 'Needs owner review' }),
    event('approval/decided', 4, { id: 'b', outcome: 'rejected' }),
    event('approval/decided', 5, { id: 'unrelated', outcome: 'allowed-once' }),
  ])
  assert.equal(result.approvals[0]?.outcome, 'running')
  assert.equal(result.approvals[0]?.note, '')
  assert.equal(result.approvals[1]?.outcome, 'rejected')
  assert.equal(result.approvals[1]?.note, 'Needs owner review')
})
test('empty audit is unknown rather than an invented successful workflow', () => {
  assert.deepEqual(projectAudit([]), { review: undefined, calls: [], approvals: [], writes: 0 })
})

test('a rerun cannot inherit an earlier successful report, or another batch captain', () => {
  const audit = projectAudit([
    event('bridgeflow/review', 1, { review_id: 'old', batch_id: 'a', status: 'validated', report_id: 'old-report' }),
    event('bridgeflow/review', 2, { review_id: 'new', batch_id: 'a', status: 'dispatching' }),
    event('tool/call', 3, { name: 'subagent', callId: 'new-call' }),
  ])
  assert.equal(selectReview(audit, 'a').waiting, true)
  assert.equal(selectReview(audit, 'a').reportId, '')
  assert.equal(selectReview(audit, 'a').runId, 'new')
  assert.equal(selectReview(audit, 'b').waiting, false)
  assert.deepEqual(selectReview(audit, 'b').calls, [])
  const done = projectAudit([event('bridgeflow/review', 4, { review_id: 'new', batch_id: 'a', report_id: 'new-report', status: 'partial' })])
  assert.equal(selectReview(done, 'a').reportId, 'new-report')
  assert.equal(selectReview(done, 'a').waiting, false)
})

test('native tool results provide review lifecycle and refusal notes without foreign session events', () => {
  const result = (time:number,callId:string,text:string) => event('tool/result',time,{message:{content:[{type:'tool-result',toolCallId:callId,content:[{type:'text',text}]}]}})
  const audit=projectAudit([
    event('tool/call',1,{name:'review_context',callId:'context'}),
    result(2,'context',JSON.stringify({review_id:'run',batch_id:'batch'})),
    event('tool/call',3,{name:'subagent',callId:'child'}),
    event('tool/call',4,{name:'review_finalize',callId:'finalize'}),
    result(5,'finalize',JSON.stringify({report_id:'report',batch_id:'batch',status:'partial'})),
    event('approval/asked',6,{id:'approval',callId:'mapping',toolName:'confirm_mapping'}),
    event('approval/decided',7,{id:'approval',outcome:'rejected'}),
    result(8,'mapping','The reviewer said: "Check the customer". Nothing was written.'),
  ])
  assert.deepEqual(audit.review,{review_id:'run',batch_id:'batch',report_id:'report',status:'partial'})
  assert.equal(audit.calls.length,1)
  assert.equal(audit.approvals[0]?.note,'Check the customer')
})
