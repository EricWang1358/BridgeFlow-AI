import { withAccess } from '../tool-catalogue.ts'
import { defineTool } from '@deepseek-ai/dsh-tools'

import { callBackend, type BackendConfig } from '../backend.ts'

/**
 * Which metrics exist, and what each one needs.
 *
 * The set is configured rather than compiled in, for the same reason column names
 * are: the customer's schema is still being negotiated, so a metric that makes sense
 * for the sample data may not survive contact with the real export.
 */
export interface MetricCatalogue {
  metrics: Array<{ name: string; unit: string; formula: string; requires: string[] }>
}

export function listMetrics(config: BackendConfig) {
  return withAccess(defineTool({
    name: 'list_metrics',
    description:
      'List the metrics that can be computed, with their formula and the declared ' +
      'fields each one needs. Call this before aggregate_metric rather than guessing a name.',
    parameters: { batch_id: { type: 'string', description: 'Uploaded batch whose frozen dictionary to use.' } },
    output: {
      schema: {
        type: 'object',
        properties: {
          metrics: {
            type: 'array',
            required: true,
            items: {
              type: 'object',
              properties: {
                name: { type: 'string', required: true },
                unit: { type: 'string', required: true },
                formula: { type: 'string', required: true },
                requires: { type: 'array', required: true, items: { type: 'string' } },
              },
              additionalProperties: false,
            },
          },
        },
        additionalProperties: false,
      },
      render: (_args, value) => {
        const metrics = value.metrics ?? []
        return metrics.length === 0
          ? [
              {
                type: 'text',
                text:
                  'No metrics are configured. The field dictionary has not been filled in, ' +
                  'so nothing can be computed by rule yet.',
              },
            ]
          : [
              {
                type: 'text',
                text: metrics
                  .map(
                    (m) =>
                      `${m.name} (${m.unit}) = ${m.formula}; needs ${(m.requires ?? []).join(', ')}`,
                  )
                  .join('\n'),
              },
            ]
      },
    },
    async execute(args, exec) {
      const value = await callBackend<MetricCatalogue>(config, '/tools/list-metrics', args, exec.signal)
      // The Python catalogue also carries private evaluator settings. The tool's
      // public contract deliberately exposes only the declared metric interface.
      return { metrics: value.metrics.map(({ name, unit, formula, requires }) => ({ name, unit, formula, requires })) }
    },
  }), { kind: 'read' })
}
