export type AuditEvent = { type: string; seq?: number; time: number; data: Record<string, unknown> }
function results(event: AuditEvent): {callId:string;text:string}[] {
  if (event.type !== 'tool/result') return []
  const message = event.data.message as {content?:{type:string;toolCallId?:string;content?:{type:string;text?:string}[]}[]} | undefined
  return (message?.content ?? []).filter(block=>block.type==='tool-result').map(block=>({callId:block.toolCallId??'',text:(block.content??[]).filter(item=>item.type==='text').map(item=>item.text??'').join('')}))
}
/** Review lifecycle is projected from actual native calls/results, never synthetic log events. */
function reviewEvents(events:AuditEvent[]):AuditEvent[] {
  const calls=new Map(events.filter(e=>e.type==='tool/call').map(e=>[String(e.data.callId),e]))
  const values:AuditEvent[]=[]
  for(const event of events) {
    if(event.type==='bridgeflow/review'){values.push(event);continue} // Older auditable metadata.
    for(const result of results(event)) {
      const call=calls.get(result.callId),name=call?.data.name
      if(name!=='review_context' && name!=='review_finalize')continue
      try {
        const data=JSON.parse(result.text) as Record<string,unknown>
        if(name==='review_context' && data.review_id && data.batch_id) values.push({...event,type:'bridgeflow/review',data:{review_id:data.review_id,batch_id:data.batch_id,status:'dispatching'}})
        else if(name==='review_finalize' && data.report_id && data.batch_id) {
          const current=values.at(-1)
          if(current?.data.batch_id===data.batch_id)values.push({...event,type:'bridgeflow/review',data:{...current.data,report_id:data.report_id,status:data.status}})
        }
      } catch { /* A refused/malformed native result cannot become a validated report. */ }
    }
  }
  return values
}

export function projectAudit(events: AuditEvent[]) {
  const reviews = reviewEvents(events)
  const review = reviews.at(-1)
  const start = reviews.filter(e => e.data.review_id === review?.data.review_id).at(0)
  const calls = events.filter(e => e.type === 'tool/call' && e.data.name === 'subagent' && start && e.time >= start.time)
  const asks = events.filter(e => e.type === 'approval/asked' && e.data.toolName === 'confirm_mapping')
  const approvals = asks.map(ask => ({ id: String(ask.data.id), call: String(ask.data.callId), time: ask.time,
    outcome: String(events.find(e => e.type === 'approval/decided' && e.data.id === ask.data.id)?.data.outcome ?? 'running'),
    note: String(events.filter(e => e.type === 'bridgeflow/approval-note' && e.data.callId === ask.data.callId).at(-1)?.data.note ?? events.flatMap(results).find(result=>result.callId===ask.data.callId)?.text.match(/The reviewer said: "([\s\S]*?)"\. Nothing was written/)?.[1] ?? '') }))
  // Writes the captain finished in this session: every write waits for an approval, so a call
  // that was allowed and has since returned is one. The Studio reloads when this count moves.
  const allowed = new Set(events.filter(e => e.type === 'approval/decided' && e.data.outcome === 'allowed-once')
    .map(e => String(events.find(ask => ask.type === 'approval/asked' && ask.data.id === e.data.id)?.data.callId ?? '')))
  const writes = events.flatMap(results).filter(result => allowed.has(result.callId)).length
  return { review: review?.data, calls, approvals, writes }
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
