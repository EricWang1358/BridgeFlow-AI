import { withAccess } from '../tool-catalogue.ts'
import { defineTool } from '@deepseek-ai/dsh-tools'

import { callBackend, type BackendConfig } from '../backend.ts'

/**
 * A metric, computed by rule.
 *
 * This is the tool half of issue #13 — "rules compute, the model explains". Today
 * the evaluator serialises every cleaned row into the prompt (5.3 KB for an 18-row
 * sample) and asks the model to work the figures out itself, which is why no number
 * on the risk panel can be traced to a row and why a judge asking "where did 18%
 * come from" gets no answer (`docs/04`, beat 5).
 *
 * The contract is deliberately narrow: the model chooses WHICH metric it wants and
 * receives the arithmetic already done, together with the rows it came from. It
 * never sees the raw table through this tool, and it never does the sum itself.
 */
export interface MetricResult {
  metric: string
  period: string
  value: number
  unit: string
  /** The formula in words, so the explanation can quote it rather than invent one. */
  formula: string
  /**
   * A bounded sample of the cells that contributed — never all of them.
   *
   * The PRD sizes one batch at 200,000 rows. A tool that keeps rows out of the
   * prompt and then returns one entry per summed cell has moved the leak rather
   * than closed it, and every agent in the fan-out would pay for it separately.
   */
  evidence: Array<{ department: string; row: number; column: string; value: string }>
  /** How many cells were actually summed, however few are shown above. */
  evidence_total: number
  /** True when `evidence` is a sample. Say so; do not imply the list is complete. */
  evidence_truncated: boolean
}

export function aggregateMetric(config: BackendConfig) {
  return withAccess(defineTool({
    name: 'aggregate_metric',
    description:
      'Compute one metric for one period by rule. Returns the figure, the count of ' +
      'cells it was derived from, and a bounded SAMPLE of those cells — never the whole ' +
      'table. Use this instead of adding figures up yourself: your arithmetic cannot be ' +
      'audited, and a finding without traceable evidence is rejected.',
    parameters: {
      metric: {
        type: 'string',
        required: true,
        description:
          'Metric name. Ask list_metrics first if unsure — the set is configured, not fixed in code.',
      },
      period: { type: 'string', required: true, description: 'Month, e.g. 2025-11' },
      batch_id: { type: 'string', description: 'Immutable batch id from the upload panel; always supply for uploaded data' },
      entity: {
        type: 'string',
        description: 'Optional entity id to scope the metric to, e.g. a SKU or customer',
      },
    },
    output: {
      schema: {
        type: 'object',
        properties: {
          metric: { type: 'string', required: true },
          period: { type: 'string', required: true },
          value: { type: 'number', required: true },
          unit: { type: 'string', required: true },
          formula: { type: 'string', required: true },
          evidence_total: { type: 'number', required: true },
          evidence_truncated: { type: 'boolean', required: true },
          evidence: {
            type: 'array',
            required: true,
            items: {
              type: 'object',
              properties: {
                department: { type: 'string', required: true },
                row: { type: 'number', required: true },
                column: { type: 'string', required: true },
                value: { type: 'string', required: true },
                filename: { type: 'string' }, sheet: { type: 'string' },
                source_row: { type: 'number' }, original_column: { type: 'string' },
              },
              additionalProperties: false,
            },
          },
        },
        additionalProperties: false,
      },
      // Runs on replay too, so it must not assume a fully-shaped value.
      render: (_args, value) => {
        const evidence = value.evidence ?? []
        return [
          {
            type: 'text',
            text:
              `${value.metric} for ${value.period} = ${value.value} ${value.unit}\n` +
              `computed as: ${value.formula}\n` +
              `from ${value.evidence_total} source cell(s)` +
              (value.evidence_truncated ? `, ${evidence.length} shown` : '') +
              ': ' +
              evidence.map((e) => `${e.filename || e.department} row ${(e.source_row ?? -1) > 0 ? e.source_row : e.row} ${e.original_column || e.column}=${e.value}`).join('; '),
          },
        ]
      },
      // Bounded, replayable facts for the UI card. The canonical value is not
      // persisted, so anything the card needs at result time has to come through here.
      presentationMeta: (_args, value) => ({
        metric: value.metric ?? '',
        value: value.value ?? 0,
        unit: value.unit ?? '',
        formula: value.formula ?? '',
        evidenceCount: value.evidence_total ?? (value.evidence ?? []).length,
        evidence_truncated: value.evidence_truncated ?? false,
      }),
    },
    async execute(args, exec) {
      return callBackend<MetricResult>(
        config,
        '/tools/aggregate-metric',
        { metric: args.metric, period: args.period, entity: args.entity ?? null, batch_id: args.batch_id ?? null },
        exec,
      )
    },
  }), { kind: 'read' })
}
