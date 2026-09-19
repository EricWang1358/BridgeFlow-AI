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
          // Every field the host returns is declared: a strict schema that lags the host
          // turns a correct answer into an invalid tool result, which only a real captain
          // ever hit (#41 live run). A contract test on the Python side keeps them in step.
          demo_case: { type: 'string' }, dictionary: { type: 'string' },
          declared_entities: { type: 'object', additionalProperties: true },
          matched_columns: { type: 'array', items: { type: 'string' } },
          stale_matches: { type: 'array', items: { type: 'string' } },
          column_questions: { type: 'number' }, derived_from: { type: 'string' },
          // Batches derived from this one (E14-UC04): a report bound to this batch rests on
          // data that has since been corrected.
          superseded_by: { type: 'array', items: { type: 'string' } },
          // Intake columns dropped as unrepresentable (docs/33); names and types, never values.
          dropped_columns: { type: 'array', items: { type: 'object', additionalProperties: true } },
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
      const summary = await callBackend<Record<string, unknown>>(config, '/tools/batch-summary', args, exec)
      // JSON null means "absent" here; the declared schema has no null type.
      return Object.fromEntries(Object.entries(summary).filter(([, value]) => value !== null)) as never
    },
  }), { kind: 'read' })
}
