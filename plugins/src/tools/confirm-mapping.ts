import { defineTool } from '@deepseek-ai/dsh-tools'

import { callBackend, type BackendConfig } from '../backend.ts'

/**
 * Accept or reject one proposed mapping, on the record.
 *
 * This is the first tool here that changes something, and the difference matters:
 * reading a metric is a question, confirming a mapping is a decision somebody will
 * be held to. It is therefore the tool the approval gate exists for.
 *
 * A rejection is recorded as deliberately as an acceptance. Re-asking a question
 * that was already answered no is the fastest way to lose the reviewer.
 */
export interface ConfirmationResult {
  source: string
  target: string
  relation: string
  accepted: boolean
  confirmed_by: string
  confirmed_at: string
  /** The person who approved this exact call, joined from the approval log. */
  authorised_by: string
  /** How many confirmations are now on file, so the answer shows the memory growing. */
  remembered: number
}

export function confirmMapping(config: BackendConfig) {
  return defineTool({
    name: 'confirm_mapping',
    description:
      'Record a human decision about one proposed mapping so it is not asked again ' +
      'next month. Accepting and rejecting are both decisions worth keeping. This ' +
      'changes stored state and requires approval.',
    parameters: {
      source: { type: 'string', required: true, description: 'Entity id, e.g. sku:sku-a1' },
      target: { type: 'string', required: true, description: 'Entity id, e.g. customer:acme-pte-ltd' },
      relation: { type: 'string', required: true, description: 'e.g. ordered_by' },
      accepted: { type: 'boolean', required: true, description: 'true to accept, false to reject' },
      evidence: {
        type: 'string',
        description:
          'What was shown when the decision was made. Recorded so the decision can ' +
          'be re-asked if the evidence later changes.',
      },
      period: { type: 'string', description: 'The period the decision was made in' },
    },
    output: {
      schema: {
        type: 'object',
        properties: {
          source: { type: 'string', required: true },
          target: { type: 'string', required: true },
          relation: { type: 'string', required: true },
          accepted: { type: 'boolean', required: true },
          confirmed_by: { type: 'string', required: true },
          confirmed_at: { type: 'string', required: true },
          authorised_by: { type: 'string' },
          remembered: { type: 'number', required: true },
        },
        additionalProperties: false,
      },
      render: (_args, value) => [
        {
          type: 'text',
          text:
            `${value.accepted ? 'Accepted' : 'Rejected'} ${value.source} → ${value.target} ` +
            `(${value.relation}), recorded by ${value.confirmed_by}` +
            // Who approved it is the sentence an auditor reads. Say so when the join
            // succeeded, and say nothing rather than something plausible when it did not.
            `${value.authorised_by ? `, approved by ${value.authorised_by}` : ''}. ` +
            `${value.remembered} confirmation(s) now on file; this one will not be asked again.`,
        },
      ],
      presentationMeta: (_args, value) => ({
        accepted: value.accepted ?? false,
        relation: value.relation ?? '',
        remembered: value.remembered ?? 0,
      }),
    },
    async execute(args, exec) {
      return callBackend<ConfirmationResult>(
        config,
        '/tools/confirm-mapping',
        {
          source: args.source,
          target: args.target,
          relation: args.relation,
          accepted: args.accepted,
          evidence: args.evidence ?? '',
          period: args.period ?? '',
          // The agent's identity, not a name the caller made up — which is who *ran*
          // the confirmation, not who allowed it.
          confirmed_by: exec.agent?.id ?? 'unknown-agent',
          // Joins this write to the approval that allowed it. Without it the record
          // says the agent confirmed the mapping, which is true and misleading.
          call_id: exec.callId,
        },
        exec.signal,
      )
    },
  })
}
