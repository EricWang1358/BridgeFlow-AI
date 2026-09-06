export type AuditEvent = { type: string; seq?: number; time: number; data: Record<string, unknown> }
export function projectAudit(events: AuditEvent[]) {
  const review = events.filter(e => e.type === 'bridgeflow/review').at(-1)
  const start = events.filter(e => e.type === 'bridgeflow/review' && e.data.review_id === review?.data.review_id).at(0)
  const calls = events.filter(e => e.type === 'tool/call' && e.data.name === 'subagent' && start && e.time >= start.time)
  const asks = events.filter(e => e.type === 'approval/asked' && e.data.toolName === 'confirm_mapping')
  const approvals = asks.map(ask => ({ id: String(ask.data.id), call: String(ask.data.callId), time: ask.time,
    outcome: String(events.find(e => e.type === 'approval/decided' && e.data.id === ask.data.id)?.data.outcome ?? 'running'),
    note: String(events.filter(e => e.type === 'bridgeflow/approval-note' && e.data.callId === ask.data.callId).at(-1)?.data.note ?? '') }))
  return { review: review?.data, calls, approvals }
}

/** Never substitute a saved report for a newer run that has no final report yet. */
export function selectReview(audit: ReturnType<typeof projectAudit>, batchId: string) {
  const sameBatch = !!batchId && audit.review?.batch_id === batchId
  const reportId = sameBatch ? String(audit.review?.report_id ?? '') : ''
  return {
    reportId,
    waiting: sameBatch && !reportId,
    runId: sameBatch ? String(audit.review?.review_id ?? '') : '',
    calls: sameBatch ? audit.calls : [],
  }
}
