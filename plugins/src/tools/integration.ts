import { withAccess, type ProductTool } from '../tool-catalogue.ts'
import { defineTool } from '@deepseek-ai/dsh-tools'

import { callBackend, type BackendConfig } from '../backend.ts'

/**
 * The 跨部门业务整合总表 as the captain may see it: how many rows, how many complete, and
 * the open items with who must decide them. Values stay in the browser view.
 */
type Json = string | number | boolean | null | Json[] | { [key: string]: Json }

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
      render: (_args, value) => {
        const summary = value as { rows?: number; complete_rows?: number; issues_by_kind?: Record<string, number> }
        return [{ type: 'text', text: `${summary.complete_rows ?? 0}/${summary.rows ?? 0} complete rows; open items: ${JSON.stringify(summary.issues_by_kind ?? {})}` }]
      },
    },
    async execute(args, exec) {
      return callBackend<Record<string, Json>>(config, '/tools/integration-summary', { batch_id: args.batch_id }, exec.signal)
    },
  }), { kind: 'read' })
}
