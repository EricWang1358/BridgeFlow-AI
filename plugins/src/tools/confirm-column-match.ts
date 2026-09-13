import { withAccess } from '../tool-catalogue.ts'
import { defineTool } from '@deepseek-ai/dsh-tools'

import { callBackend, type BackendConfig } from '../backend.ts'
import type { ApprovalReceipts } from '../approval/receipts.ts'

/**
 * A person's decision that an uploaded column is, or is not, a declared column.
 *
 * The host refuses any target outside the batch's closed candidate set before an
 * approval is spent, so a proposal cannot turn into a new field. Acceptance renames
 * the column on later imports; the dictionary and frozen batches never change.
 */
export interface ColumnMatchResult {
  department: string
  column: string
  target: string
  accepted: boolean
  confirmed_at: string
  authorised_by: string
  next_step: string
  remaining_candidates: string[]
}

/** Identical body at approval and dispatch; changing even one value invalidates it. */
export function columnMatchBody(args: Record<string, unknown>, agentId: string, callId: string | undefined) {
  return {
    batch_id: args.batch_id, department: args.department, column: args.column, target: args.target,
    accepted: args.accepted, reason: args.reason ?? '', confirmed_by: agentId, call_id: callId ?? null,
  }
}

export function confirmColumnMatch(config: BackendConfig, receipts: ApprovalReceipts) {
  return withAccess(defineTool({
    name: 'confirm_column_match',
    description:
      'Record a human decision that one uploaded column is (accepted=true) or is not (accepted=false) ' +
      'a column the dictionary already declares, as listed by column_candidates. ' +
      'The decision applies to later imports; the current batch and the dictionary do not change. ' +
      'This changes stored state and requires approval.',
    parameters: {
      batch_id: { type: 'string', required: true, description: 'Batch the proposal was made from' },
      department: { type: 'string', required: true, description: 'Department of the uploaded column' },
      column: { type: 'string', required: true, description: 'Uploaded column, as listed by column_candidates' },
      target: { type: 'string', required: true, description: 'Declared column, from that question\'s candidates' },
      accepted: { type: 'boolean', required: true, description: 'true to accept the match, false to reject it' },
      reason: { type: 'string', description: 'The evidence cited for the proposal, kept with the decision' },
    },
    output: {
      schema: {
        type: 'object',
        properties: {
          department: { type: 'string', required: true },
          column: { type: 'string', required: true },
          target: { type: 'string', required: true },
          accepted: { type: 'boolean', required: true },
          confirmed_at: { type: 'string', required: true },
          authorised_by: { type: 'string' },
          next_step: { type: 'string', required: true },
          remaining_candidates: { type: 'array', items: { type: 'string' } },
        },
        additionalProperties: false,
      },
      render: (_args, value) => [{
        type: 'text',
        text:
          `${value.accepted ? 'Accepted' : 'Rejected'} ${value.department}.${value.column} → ${value.target}. ` +
          `${value.next_step}` +
          ((value.remaining_candidates ?? []).length ? ` Remaining: ${(value.remaining_candidates ?? []).join(', ')}.` : ''),
      }],
      presentationMeta: (_args, value) => ({ accepted: value.accepted ?? false }),
    },
    async execute(args, exec) {
      return callBackend<ColumnMatchResult>(
        config,
        '/tools/confirm-column-match',
        columnMatchBody(args, exec.agent?.id ?? 'unknown-agent', exec.callId),
        exec.signal,
        receipts.take(JSON.stringify([exec.agent?.id, exec.callId])),
      )
    },
  }), {
    kind: 'approval',
    reason: 'Remember that an uploaded column is a declared dictionary column, for future imports. Nothing is written without approval.',
    denialEffect: 'Nothing was written; the column stays unknown and the next import will still need configuration. Do NOT claim the match was saved',
    body: columnMatchBody,
  })
}
