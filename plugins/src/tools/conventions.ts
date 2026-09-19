import { withAccess, type ProductTool } from '../tool-catalogue.ts'
import { defineTool } from '@deepseek-ai/dsh-tools'

import { callBackend, type BackendConfig } from '../backend.ts'
import type { ApprovalReceipts } from '../approval/receipts.ts'

/**
 * Conventions the business side has not signed off (E13-UC05).
 *
 * Where the dictionary is silent, the declaration fills the gap by convention and says so;
 * every figure resting on one is graded G3. These tools let a person settle that: confirming
 * raises the grade to G2, replacing records their decision and the declaration change the
 * dictionary owner must apply — the model never reinterprets a formula from free text.
 *
 * The preview is a dry run and returns counts and field names only; the cells that would
 * change stay in the browser.
 */
type Json = string | number | boolean | null | Json[] | { [key: string]: Json }

export function decideBody(args: Record<string, unknown>, agentId: string, callId: string | undefined) {
  return { batch_id: args.batch_id, convention: args.convention, action: args.action,
    source: args.source, note: args.note ?? '', requested_value: args.requested_value ?? '',
    expected_version: typeof args.expected_version === 'number' ? args.expected_version : null,
    confirmed_by: agentId, call_id: callId ?? null }
}

const anyObject = { schema: { type: 'object' as const, additionalProperties: true as const } }

export function conventionList(config: BackendConfig): ProductTool {
  return withAccess(defineTool({
    name: 'convention_list',
    description: 'List the conventions this batch\'s declaration fills gaps with: what each says, whether the business side has confirmed or asked to replace it, and its version. Declaration text only, no sheet data.',
    parameters: { batch_id: { type: 'string', required: true } },
    output: { ...anyObject, render: (_args, value) => {
      const list = value as { conventions?: { id: string; state: string; version: number; kind: string }[] }
      const items = list.conventions ?? []
      const open = items.filter(c => c.state === 'unconfirmed').length
      return [{ type: 'text', text: `${items.length} convention(s), ${open} unconfirmed. ` + items.map(c => `${c.id} (${c.kind}, ${c.state}${c.version ? ` v${c.version}` : ''})`).join(' | ') }]
    } },
    async execute(args, exec) {
      return callBackend<Record<string, Json>>(config, '/tools/convention-list', { batch_id: args.batch_id }, exec)
    },
  }), { kind: 'read' })
}

export function conventionPreview(config: BackendConfig): ProductTool {
  return withAccess(defineTool({
    name: 'convention_preview',
    description: 'Dry run: how many cells and which fields would change if a declared constant took another value. Changes nothing. Only constants can be previewed; a formula or rule is changed by editing the declaration.',
    parameters: {
      batch_id: { type: 'string', required: true },
      convention: { type: 'string', required: true, description: 'Convention id from convention_list' },
      requested_value: { type: 'string', required: true, description: 'The number the person gave' },
    },
    output: { ...anyObject, render: (_args, value) => {
      const result = value as { changed_cells?: number; changed_rows?: number; changed_fields?: string[] }
      return [{ type: 'text', text: `${result.changed_cells ?? 0} cell(s) in ${result.changed_rows ?? 0} row(s) would change, in: ${(result.changed_fields ?? []).join('、') || 'nothing'}.` }]
    } },
    async execute(args, exec) {
      return callBackend<Record<string, Json>>(config, '/tools/convention-preview',
        { batch_id: args.batch_id, convention: args.convention, requested_value: args.requested_value }, exec)
    },
  }), { kind: 'read' })
}

export function conventionDecide(config: BackendConfig, receipts: ApprovalReceipts): ProductTool {
  return withAccess(defineTool({
    name: 'convention_decide',
    description: 'Record the business side\'s decision on one convention: confirm it (figures resting on it then count as declared formula, G2) or ask for it to be replaced (recorded with the declaration change for the dictionary owner; nothing is recomputed). Needs the source the decision comes from. Requires approval.',
    parameters: {
      batch_id: { type: 'string', required: true },
      convention: { type: 'string', required: true, description: 'Convention id from convention_list' },
      action: { type: 'string', required: true, enum: ['confirm', 'replace'] },
      source: { type: 'string', required: true, description: 'Where the decision comes from: the document, meeting note or written statement the person named. Never your own reasoning.' },
      note: { type: 'string', description: 'What the business side said the rule should be, in their words' },
      requested_value: { type: 'string', description: 'Replacing a constant: the value they gave' },
      expected_version: { type: 'number', description: 'The version convention_list showed; a mismatch means somebody else decided first' },
    },
    output: { ...anyObject, render: (_args, value) => [{ type: 'text', text: String((value as { next_step?: string }).next_step ?? 'Recorded.') }] },
    async execute(args, exec) {
      return callBackend<Record<string, Json>>(config, '/tools/convention-decide', decideBody(args, exec.agent?.id ?? 'unknown-agent', exec.callId),
        exec, receipts.take(JSON.stringify([exec.agent?.id, exec.callId])))
    },
  }), {
    kind: 'approval',
    reason: 'Record this decision about a convention the dictionary does not state. Confirming changes how firmly the figures resting on it are labelled; replacing changes nothing until the declaration is edited.',
    denialEffect: 'No decision was recorded; the convention stays unconfirmed. Do NOT describe it as confirmed or replaced',
    body: decideBody,
  })
}
