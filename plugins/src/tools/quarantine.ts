import { withAccess, type ProductTool } from '../tool-catalogue.ts'
import { defineTool } from '@deepseek-ai/dsh-tools'

import { callBackend, type BackendConfig } from '../backend.ts'
import type { ApprovalReceipts } from '../approval/receipts.ts'

/**
 * An exit for quarantined rows (#88): list them, decide each one, apply to a new batch.
 *
 * The listing never carries cell values — only the department, the row's position and
 * which checks it fails, by column name. Release is revalidation on the host: a row that
 * still fails is refused, and a corrected cell can only come from what the person said,
 * shown to them in the approval. Applying creates a new batch; the frozen one never
 * changes.
 */
type Json = string | number | boolean | null | Json[] | { [key: string]: Json }

export function decideBody(args: Record<string, unknown>, agentId: string, callId: string | undefined) {
  const fixes = (Array.isArray(args.fixes) ? args.fixes : []).map((f: Record<string, unknown>) => {
    const fix: Record<string, unknown> = { column: String(f?.label ?? f?.column ?? ''), value: String(f?.value ?? '') }
    // A proposal the captain drafted (#245): attribution rides with the value; the
    // person's approval is what makes it a decision. Absent means the person dictated it.
    if (f?.proposed_by) fix.proposed_by = String(f.proposed_by)
    if (f?.evidence) fix.evidence = String(f.evidence)
    return fix
  })
  return { batch_id: args.batch_id, department: args.department, index: args.index, action: args.action,
    reason: args.reason, fixes, shift: args.shift === 'left' || args.shift === 'right' ? args.shift : '', confirmed_by: agentId, call_id: callId ?? null }
}

export function applyBody(args: Record<string, unknown>, agentId: string, callId: string | undefined) {
  return { batch_id: args.batch_id, confirmed_by: agentId, call_id: callId ?? null }
}

const anyObject = { schema: { type: 'object' as const, additionalProperties: true as const } }

export function quarantineList(config: BackendConfig): ProductTool {
  return withAccess(defineTool({
    name: 'quarantine_list',
    description: 'List quarantined rows of a batch: department, row index, the checks each row still fails (by column name) and any decision. No cell values.',
    parameters: { batch_id: { type: 'string', required: true } },
    output: { ...anyObject, render: (_args, value) => {
      const list = value as { total?: number; entries?: { department: string; index: number; failing_checks: string[]; decision: string; shift_suggestion?: string }[] }
      return [{ type: 'text', text: `${list.total ?? 0} quarantined row(s). ` + (list.entries ?? []).slice(0, 10)
          .map(e => `${e.department}#${e.index}: ${e.decision || (e.failing_checks.join('; ') || 'releasable')}${e.shift_suggestion ? ` (passes if shifted ${e.shift_suggestion})` : ''}`).join(' | ') }]
    } },
    async execute(args, exec) {
      return callBackend<Record<string, Json>>(config, '/tools/quarantine-list', { batch_id: args.batch_id }, exec)
    },
  }), { kind: 'read' })
}

export function quarantineDecide(config: BackendConfig, receipts: ApprovalReceipts): ProductTool {
  return withAccess(defineTool({
    name: 'quarantine_decide',
    description: 'Record a person\'s decision for one quarantined row: release (only if it passes revalidation, optionally with corrected cells the person stated) or discard, with their reason. Requires approval.',
    parameters: {
      batch_id: { type: 'string', required: true },
      department: { type: 'string', required: true },
      index: { type: 'number', required: true, description: 'Row index from quarantine_list' },
      action: { type: 'string', required: true, enum: ['release', 'discard'] },
      reason: { type: 'string', required: true, description: 'The person\'s reason' },
      shift: { type: 'string', enum: ['left', 'right'], description: 'Release with every cell moved one column, only when quarantine_list suggested that direction and the person agreed' },
      fixes: { type: 'array', description: 'Cells to correct, releasing only. A value the person gave needs no extras; a value YOU proposed from quarantine_row must carry proposed_by and evidence, and the person must have approved it in this decision\'s approval.',
        items: { type: 'object', properties: {
          label: { type: 'string', required: true, description: 'Column name as listed' },
          value: { type: 'string', required: true },
          proposed_by: { type: 'string', description: 'Present only when the captain proposed the value' },
          evidence: { type: 'string', description: 'The row evidence the proposal rests on' },
        }, additionalProperties: false } },
    },
    output: { ...anyObject, render: (_args, value) => [{ type: 'text', text: String((value as { next_step?: string }).next_step ?? 'Recorded.') }] },
    async execute(args, exec) {
      return callBackend<Record<string, Json>>(config, '/tools/quarantine-decide', decideBody(args, exec.agent?.id ?? 'unknown-agent', exec.callId),
        exec, receipts.take(JSON.stringify([exec.agent?.id, exec.callId])))
    },
  }), {
    kind: 'approval',
    reason: 'Record what happens to this quarantined row. Nothing changes until the decisions are applied to a new batch.',
    denialEffect: 'No decision was recorded; the row stays quarantined. Do NOT describe it as released or discarded',
    body: decideBody,
  })
}

export function quarantineApply(config: BackendConfig, receipts: ApprovalReceipts): ProductTool {
  return withAccess(defineTool({
    name: 'quarantine_apply',
    description: 'Apply the recorded quarantine decisions: creates a NEW batch derived from this one (this batch stays frozen) and reports its id and status. Requires approval.',
    parameters: { batch_id: { type: 'string', required: true } },
    output: { ...anyObject, render: (_args, value) => {
      const result = value as { batch?: { batch_id?: string; status?: string }; replayed?: boolean }
      return [{ type: 'text', text: `${result.replayed ? 'Already applied' : 'Applied'}: new batch ${result.batch?.batch_id} (${result.batch?.status}). Use the new batch id from now on.` }]
    } },
    async execute(args, exec) {
      return callBackend<Record<string, Json>>(config, '/tools/quarantine-apply', applyBody(args, exec.agent?.id ?? 'unknown-agent', exec.callId),
        exec, receipts.take(JSON.stringify([exec.agent?.id, exec.callId])))
    },
  }), {
    kind: 'approval',
    reason: 'Create a new batch from the recorded quarantine decisions. The current batch and its reports stay unchanged.',
    denialEffect: 'No new batch was created. Do NOT use or mention a new batch id',
    body: applyBody,
  })
}
