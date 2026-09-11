import { withAccess } from '../tool-catalogue.ts'
import { defineTool } from '@deepseek-ai/dsh-tools'
import { callBackend, type BackendConfig } from '../backend.ts'

export function batchSummary(config: BackendConfig) {
  return withAccess(defineTool({
    name: 'batch_summary',
    description: 'Read bounded counts and readiness of an uploaded batch, without raw data rows. Use the exact batch id supplied by the user.',
    parameters: { batch_id: { type: 'string', required: true } },
    output: {
      schema: {
        type: 'object', properties: {
          batch_id: { type: 'string', required: true }, period: { type: 'string', required: true },
          master_rows: { type: 'number', required: true }, unresolved: { type: 'number', required: true },
          status: { type: 'string', required: true }, refusal: { type: 'string', required: true },
          departments: { type: 'array', required: true, items: { type: 'object', properties: {
            department: { type: 'string', required: true }, rows: { type: 'number', required: true },
            corrections: { type: 'number', required: true }, quarantined: { type: 'number', required: true },
          }, additionalProperties: false } },
        }, additionalProperties: false,
      },
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value) }],
      presentationMeta: (_args, value) => value,
    },
    async execute(args, exec) {
      return callBackend(config, '/tools/batch-summary', args, exec.signal)
    },
  }), { kind: 'read' })
}
