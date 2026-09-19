import { withAccess } from '../tool-catalogue.ts'
import { defineTool } from '@deepseek-ai/dsh-tools'

import { callBackend, type BackendConfig } from '../backend.ts'

/**
 * What the columns look like, when a batch cannot be joined.
 *
 * The refusal that blocks a Master Table names the department with no declared
 * joinable column. That is correct and it is half an answer: the operator is left
 * holding four spreadsheets and the same question the machine could not answer.
 * Stopping there is the failure mode this product exists to remove — a person
 * staring at a dead end is exactly what they were doing before we showed up.
 *
 * So this hands the model the structural facts it needs to match an existing human declaration:
 * how unique each column is, how much of it is filled, whether it is
 * identifier-shaped, and — the load-bearing signal — how far one department's values
 * overlap another's, computed over hashes.
 *
 * **No cell ever reaches the model.** Counts and ratios only; the overlap proves two
 * departments name the same things without either side's values travelling
 * (`CLAUDE.md`, seventh hard constraint). And nothing here knows what a `sku` is:
 * every signal is structural, because the customer's schema is still being
 * negotiated and code must not encode it (eighth constraint).
 */
export interface ColumnProfile {
  department: string
  column: string
  original: string
  dtype: string
  rows: number
  filled: number
  distinct: number
  distinct_ratio: number
  fill_ratio: number
  identifier_shaped: boolean
  average_length: number
}

export interface BatchProfile {
  batch_id: string
  period: string
  columns: ColumnProfile[]
  overlaps: {
    left: string; right: string
    left_dtype: string; right_dtype: string
    shared: number; left_coverage: number; right_coverage: number
  }[]
  undeclared: string[]
  declared: Record<string, string[]>
  truncated: boolean
}

export function profileBatch(config: BackendConfig) {
  return withAccess(defineTool({
    name: 'profile_batch',
    description:
      'Describe column counts, ratios and hashed value overlap without returning cell values. ' +
      'Use lookup_field_dictionary to find the human-declared candidates in this batch. ' +
      'Propose uploaded-column matches only within those existing declarations, citing profile evidence. ' +
      'Overlap alone never proves a cross-entity relation. If no declared candidate fits, report ' +
      'needs_configuration and ask the responsible person to configure the dictionary. ' +
      'Never create fields, entity kinds, relations or a new dictionary.',
    parameters: {
      batch_id: { type: 'string', required: true, description: 'The batch to profile' },
    },
    output: {
      schema: {
        type: 'object',
        properties: {
          batch_id: { type: 'string', required: true },
          period: { type: 'string' },
          // Spelled out rather than `additionalProperties: true`: the model reads
          // these field names to decide what to propose, so they are part of the
          // contract, not incidental payload.
          columns: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                department: { type: 'string' }, column: { type: 'string' },
                original: { type: 'string' }, dtype: { type: 'string' },
                rows: { type: 'number' }, filled: { type: 'number' }, distinct: { type: 'number' },
                distinct_ratio: { type: 'number' }, fill_ratio: { type: 'number' },
                identifier_shaped: { type: 'boolean' }, average_length: { type: 'number' },
              },
              additionalProperties: false,
            },
          },
          overlaps: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                left: { type: 'string' }, right: { type: 'string' },
                left_dtype: { type: 'string' }, right_dtype: { type: 'string' },
                shared: { type: 'number' },
                left_coverage: { type: 'number' }, right_coverage: { type: 'number' },
              },
              additionalProperties: false,
            },
          },
          undeclared: { type: 'array', items: { type: 'string' } },
          declared: { type: 'object', additionalProperties: true },
          truncated: { type: 'boolean' },
        },
        additionalProperties: false,
      },
      render: (_args, value) => {
        const blocked = value.undeclared ?? []
        const best = (value.overlaps ?? [])
          .filter(o => o.left_dtype === 'string' && o.right_dtype === 'string')
          .slice(0, 6)
          .map(o => `${o.left} ~ ${o.right} (${Math.round((o.left_coverage ?? 0) * 100)}%/${Math.round((o.right_coverage ?? 0) * 100)}% of distinct values shared)`)
        return [{
          type: 'text',
          text:
            (blocked.length
              ? `No declared joinable column in: ${blocked.join(', ')}. `
              : 'Every department has a declared joinable column. ') +
            `${value.columns?.length ?? 0} columns profiled. ` +
            (best.length ? `Strongest cross-department overlaps: ${best.join('; ')}.` : 'No cross-department overlap above the reporting threshold.') +
            (value.truncated ? ' (list truncated)' : ''),
        }]
      },
      presentationMeta: (_args, value) => ({
        blocked: (value.undeclared ?? []).length,
        columns: (value.columns ?? []).length,
      }),
    },
    async execute(args, exec) {
      return callBackend<BatchProfile>(config, '/tools/profile-batch', { batch_id: args.batch_id }, exec)
    },
  }), { kind: 'read' })
}
