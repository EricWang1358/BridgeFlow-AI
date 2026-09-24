import { withAccess } from '../tool-catalogue.ts'
import { defineTool } from '@deepseek-ai/dsh-tools'

import { callBackend, type BackendConfig } from '../backend.ts'

/**
 * The declared columns an unknown uploaded column could be — and nothing else.
 *
 * A department exporting its sheet under a header the dictionary does not know is
 * the most ordinary way a batch fails to join. The dictionary is written by people in
 * advance (`CLAUDE.md`, 「字典由人预设，模型只做匹配」), so the useful question is not
 * "what should be declared" but "which already-declared column is this". That
 * question has a closed answer set, and this tool hands the model exactly that set
 * with structural evidence: type fit, and for entity columns the share of distinct
 * values it has in common with another department's column of the same kind, by hash.
 *
 * No cell ever reaches the model.
 */
export interface Candidate {
  target: string
  role: string
  type_fits: boolean
  /** Absent when there is nothing comparable, which is not evidence against. */
  entity_overlap?: number
  overlap_with: string
  decided: string
}

export interface CandidateList {
  batch_id: string
  period: string
  questions: {
    department: string
    column: string
    original: string
    profile: Record<string, string | number | boolean>
    candidates: Candidate[]
  }[]
  applied: string[]
  needs_dictionary_owner: string[]
  truncated: boolean
}

export function columnCandidates(config: BackendConfig) {
  return withAccess(defineTool({
    name: 'column_candidates',
    description:
      'List each uploaded column of a batch that the field dictionary does not know (an empty list when it knows them all), ' +
      'with the columns the dictionary already declares for that department as its only possible matches, ' +
      'plus structural evidence (type fit, hashed value overlap). No cell values. ' +
      'Propose at most one match per column, explain the evidence, then call confirm_column_match so a person decides. ' +
      'Never propose a target that is not listed; if nothing fits, say the dictionary owner must decide. ' +
      'Call it directly when someone asks about unrecognised columns; reading batch_summary first is not needed.',
    parameters: {
      batch_id: { type: 'string', required: true, description: 'The batch to examine' },
    },
    output: {
      schema: {
        type: 'object',
        properties: {
          batch_id: { type: 'string', required: true },
          period: { type: 'string' },
          questions: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                department: { type: 'string' }, column: { type: 'string' }, original: { type: 'string' },
                profile: { type: 'object', additionalProperties: true },
                candidates: {
                  type: 'array',
                  items: {
                    type: 'object',
                    properties: {
                      target: { type: 'string' }, role: { type: 'string' }, type_fits: { type: 'boolean' },
                      entity_overlap: { type: 'number' }, overlap_with: { type: 'string' },
                      decided: { type: 'string' },
                    },
                    additionalProperties: false,
                  },
                },
              },
              additionalProperties: false,
            },
          },
          applied: { type: 'array', items: { type: 'string' } },
          needs_dictionary_owner: { type: 'array', items: { type: 'string' } },
          truncated: { type: 'boolean' },
        },
        additionalProperties: false,
      },
      render: (_args, value) => {
        const questions = value.questions ?? []
        const lines = questions.slice(0, 8).map(q => {
          const options = (q.candidates ?? []).map(c =>
            `${c.target} [${c.role}${c.type_fits ? '' : ', type mismatch'}` +
            `${c.entity_overlap !== undefined ? `, ${Math.round(c.entity_overlap * 100)}% shared with ${c.overlap_with}` : ''}` +
            `${c.decided ? `, ${c.decided}` : ''}]`)
          return `${q.department}.${q.column}: ${options.join('; ') || 'no declared candidate'}`
        })
        const owner = value.needs_dictionary_owner ?? []
        return [{
          type: 'text',
          text:
            (questions.length ? `${questions.length} unknown column(s). ${lines.join(' | ')}` : 'No unknown column has a declared candidate.') +
            (owner.length ? ` Dictionary owner needed for: ${owner.join(', ')}.` : '') +
            (value.truncated ? ' (list truncated)' : ''),
        }]
      },
      presentationMeta: (_args, value) => ({ questions: (value.questions ?? []).length }),
    },
    async execute(args, exec) {
      return callBackend<CandidateList>(config, '/tools/column-candidates', { batch_id: args.batch_id }, exec)
    },
  }), { kind: 'read' })
}
