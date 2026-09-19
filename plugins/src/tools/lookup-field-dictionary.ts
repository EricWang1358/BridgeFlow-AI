import { withAccess } from '../tool-catalogue.ts'
import { defineTool } from '@deepseek-ai/dsh-tools'

import { callBackend, type BackendConfig } from '../backend.ts'

/**
 * What the OA field dictionary says a column means.
 *
 * This tool exists so the model never has to guess. Column names, entity kinds and
 * relations are configuration, not code (`CLAUDE.md`, eighth hard constraint): the
 * real XLS schema is still being negotiated with the customer, so a spelling the
 * model recognises today is not evidence of anything.
 *
 * When the dictionary has nothing to say, that is the answer. It is not an
 * invitation to fall back on what a column is called.
 */
export interface ColumnMeaning {
  department: string
  column: string
  /** The declared entity kind. Absent when the dictionary does not claim this column. */
  kind?: string
  /** Where the answer came from, so a finding can cite it. */
  source: 'declared' | 'undeclared'
}

export function lookupFieldDictionary(config: BackendConfig) {
  return withAccess(defineTool({
    name: 'lookup_field_dictionary',
    description:
      'Look up what a department column means according to the OA field dictionary. ' +
      'Returns kind=null when the dictionary does not declare the column — treat that ' +
      'as "unknown", never as permission to infer the meaning from the column name.',
    parameters: {
      department: {
        type: 'string',
        required: true,
        description: 'production | procurement | finance | marketing',
      },
      column: { type: 'string', required: true, description: 'The column name as it appears in the sheet' },
    },
    output: {
      schema: {
        type: 'object',
        properties: {
          department: { type: 'string', required: true },
          column: { type: 'string', required: true },
          // Absent rather than null: a value schema takes one type per property, and
          // "the dictionary does not declare this column" is the absence of an answer.
          kind: { type: 'string' },
          source: { type: 'string', required: true },
        },
        additionalProperties: false,
      },
      // Renderers run on live streaming and on replay, so they must survive a value
      // that an older log wrote differently. Never let display crash a replay.
      render: (_args, value) => [
        {
          type: 'text',
          text: value.kind
            ? `${value.department}.${value.column} is declared as ${value.kind}.`
            : `The field dictionary does not declare ${value.department}.${value.column}. ` +
              `Its meaning is unknown — do not infer it from the column name.`,
        },
      ],
    },
    async execute(args, exec) {
      return callBackend<ColumnMeaning>(
        config,
        '/tools/lookup-field-dictionary',
        { department: args.department, column: args.column },
        exec,
      )
    },
  }), { kind: 'read' })
}
