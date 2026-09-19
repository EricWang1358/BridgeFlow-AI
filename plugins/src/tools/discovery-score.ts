import { defineTool } from '@deepseek-ai/dsh-tools'
import { callBackend, type BackendConfig } from '../backend.ts'
import type { ApprovalReceipts } from '../approval/receipts.ts'
import { withAccess, type ProductTool } from '../tool-catalogue.ts'
import { references } from './discovery-graph.ts'

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue }
const rating = { type: 'object', additionalProperties: false, properties: {
  score: { type: 'string', description: 'Declared decimal value, not an AI estimate; omit if unknown' },
  rationale: { type: 'string' }, references,
} } as const
export function scoreBody(args: Record<string, unknown>, _agent: string, callId: string | undefined) {
  return { score: args.score, call_id: callId ?? null }
}
export function discoveryScoreSave(config: BackendConfig, receipts: ApprovalReceipts): ProductTool {
  return withAccess(defineTool({
    name: 'discovery_score_save',
    description: 'Save human-reviewed effort/value ratings against the exact configured policy fingerprint and ' +
      'candidate version. Never invent scales, weights, values or evidence. Unknown axes may be omitted; incomplete ' +
      'ratings are saved without coordinates. This does not approve a project or promise savings.',
    parameters: { score: { type: 'object', required: true, additionalProperties: false, properties: {
      id: { type: 'string', required: true }, project_id: { type: 'string', required: true },
      opportunity_id: { type: 'string', required: true }, opportunity_version: { type: 'number', required: true },
      policy_fingerprint: { type: 'string', required: true }, expected_seq: { type: 'number', required: true },
      effort: rating, value: rating,
    } } },
    output: { schema: { type: 'object', additionalProperties: true }, render: (_args, value) => [{ type: 'text', text: JSON.stringify(value) }] },
    async execute(args, exec) {
      return callBackend<Record<string, JsonValue>>(config, '/tools/discovery-score-save',
        scoreBody(args, exec.agent?.id ?? 'unknown-agent', exec.callId), exec,
        receipts.take(JSON.stringify([exec.agent?.id, exec.callId])))
    },
  }), { kind: 'approval', reason: 'Save these exact ratings, rationales and source references under the displayed policy fingerprint. This is not project approval.',
    denialEffect: 'No score revision was saved. Do not claim a priority or project decision', body: scoreBody })
}
