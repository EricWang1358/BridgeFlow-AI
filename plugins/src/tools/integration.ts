import { withAccess, type ProductTool } from '../tool-catalogue.ts'
import { defineTool } from '@deepseek-ai/dsh-tools'

import { callBackend, type BackendConfig } from '../backend.ts'

/**
 * The 跨部门业务整合总表 as the captain may see it: how many rows, how many complete, and
 * the open items with who must decide them. Values stay in the browser view.
 */
type Json = string | number | boolean | null | Json[] | { [key: string]: Json }

type IntegrationText = { rows?: number; complete_rows?: number; issues_by_kind?: Record<string, number>
  open_items?: { kind: string; field?: string; departments?: string[] }[]; assumptions?: Record<string, string>
  convention_states?: Record<string, string>; next_step?: string }
/**
 * The open items, the conventions and the next step — what the persona asks the captain to
 * explain — not only their counts. Counts alone sent a real captain to six other tools to
 * find out what the items were (#253). Declaration text and handles only; no cell values.
 */
export function renderIntegration(summary: IntegrationText) {
  const items = summary.open_items ?? []
  const lines = items.slice(0, 10).map(i => `- ${i.kind}${i.field ? `: ${i.field}` : ''} [departments: ${(i.departments ?? []).join('/') || '—'}]`)
  const assumptions = Object.entries(summary.assumptions ?? {})
  const conventions = assumptions.slice(0, 8).map(([id, text]) => `- ${id} (${summary.convention_states?.[id] ?? 'unconfirmed'}): ${text}`)
  const total = Object.values(summary.issues_by_kind ?? {}).reduce((n, c) => n + c, 0)
  return [{ type: 'text' as const, text:
    `${summary.complete_rows ?? 0}/${summary.rows ?? 0} complete rows; ${total} open item(s) by kind ${JSON.stringify(summary.issues_by_kind ?? {})}.`
    + (lines.length ? `\nOpen items${total > lines.length ? ` (first ${lines.length} of ${total})` : ''}:\n${lines.join('\n')}` : '')
    + (conventions.length ? `\nConventions the dictionary does not state${assumptions.length > conventions.length ? ` (first ${conventions.length} of ${assumptions.length})` : ''}:\n${conventions.join('\n')}` : '')
    + (summary.next_step ? `\n${summary.next_step}` : '') }]
}

export function integrationSummary(config: BackendConfig): ProductTool {
  return withAccess(defineTool({
    name: 'integration_summary',
    description:
      'Summarise the cross-department master table built from the business dictionary for an imported batch: row counts, ' +
      'complete rows, and open items (missing departments, disagreements, formula mismatches, undeclared constants, roll-up rules). ' +
      'No cell values. Lists the conventions (assumptions) the declaration uses where the dictionary is silent; say so when a figure rests on one. ' +
      'Undeclared constants and roll-up rules are for the dictionary owner to declare; never supply them yourself.',
    parameters: { batch_id: { type: 'string', required: true } },
    output: {
      schema: { type: 'object', additionalProperties: true },
      render: (_args, value) => renderIntegration(value as IntegrationText),
    },
    async execute(args, exec) {
      return callBackend<Record<string, Json>>(config, '/tools/integration-summary', { batch_id: args.batch_id }, exec)
    },
  }), { kind: 'read' })
}
