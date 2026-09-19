import { withAccess, type ProductTool } from '../tool-catalogue.ts'
import { defineTool } from '@deepseek-ai/dsh-tools'

import { callBackend, type BackendConfig } from '../backend.ts'
import type { ApprovalReceipts } from '../approval/receipts.ts'

/**
 * What happens to a risk finding after the review names it (E07-UC07).
 *
 * The states and who may move between them are the company's declaration, not this tool's
 * invention: the listing reports what is allowed next, and a move outside it is refused by
 * the host. Recording one is a person's decision, so it needs their approval, and the
 * approver is who the record names.
 */
type Json = string | number | boolean | null | Json[] | { [key: string]: Json }

export function recordBody(args: Record<string, unknown>, agentId: string, callId: string | undefined) {
  return { batch_id: args.batch_id, check_id: args.check_id, action: args.action, note: args.note ?? '',
    report_id: args.report_id ?? null,
    expected_version: typeof args.expected_version === 'number' ? args.expected_version : null,
    confirmed_by: agentId, call_id: callId ?? null }
}

const anyObject = { schema: { type: 'object' as const, additionalProperties: true as const } }

export function riskDispositions(config: BackendConfig): ProductTool {
  return withAccess(defineTool({
    name: 'risk_dispositions',
    description: 'The state of each attention finding in a batch\'s review: current state, who decided it, and which actions the company\'s declaration allows next. No cell values.',
    parameters: { batch_id: { type: 'string', required: true } },
    output: { ...anyObject, render: (_args, value) => {
      const result = value as { open?: number; refusal?: string
        dispositions?: { check_id: string; state: string; available: string[] }[] }
      if (result.refusal) return [{ type: 'text', text: result.refusal }]
      return [{ type: 'text', text: `${result.open ?? 0} open finding(s). ` + (result.dispositions ?? [])
        .map(d => `${d.check_id}: ${d.state}${d.available.length ? ` → ${d.available.join('/')}` : ''}`).join(' | ') }]
    } },
    async execute(args, exec) {
      return callBackend<Record<string, Json>>(config, '/tools/risk-dispositions', { batch_id: args.batch_id }, exec)
    },
  }), { kind: 'read' })
}

export function riskDispositionRecord(config: BackendConfig, receipts: ApprovalReceipts): ProductTool {
  return withAccess(defineTool({
    name: 'risk_disposition_record',
    description: 'Record the person\'s decision on one risk finding — the action must be one the declaration allows from its current state, and actions the declaration marks as needing a reason are refused without one. Requires approval.',
    parameters: {
      batch_id: { type: 'string', required: true },
      check_id: { type: 'string', required: true, description: 'Finding id from risk_dispositions' },
      action: { type: 'string', required: true, description: 'One of the actions risk_dispositions listed as available' },
      note: { type: 'string', description: 'The person\'s reason, in their words' },
      expected_version: { type: 'number', description: 'The version risk_dispositions showed; a mismatch means somebody decided first' },
      report_id: { type: 'string', description: 'A specific review report; the latest is used otherwise' },
    },
    output: { ...anyObject, render: (_args, value) => [{ type: 'text', text: String((value as { next_step?: string }).next_step ?? 'Recorded.') }] },
    async execute(args, exec) {
      return callBackend<Record<string, Json>>(config, '/tools/risk-disposition-record', recordBody(args, exec.agent?.id ?? 'unknown-agent', exec.callId),
        exec, receipts.take(JSON.stringify([exec.agent?.id, exec.callId])))
    },
  }), {
    kind: 'approval',
    reason: 'Record this decision about a risk finding. The report and its figures do not change; what changes is what the company says it is doing about this finding.',
    denialEffect: 'Nothing was recorded; the finding stays in its current state. Do NOT describe it as confirmed, assigned or closed',
    body: recordBody,
  })
}
