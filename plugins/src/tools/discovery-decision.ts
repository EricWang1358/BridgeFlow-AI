import { defineTool } from '@deepseek-ai/dsh-tools'
import { callBackend, type BackendConfig } from '../backend.ts'
import type { ApprovalReceipts } from '../approval/receipts.ts'
import { withAccess, type ProductTool } from '../tool-catalogue.ts'
import { references } from './discovery-graph.ts'

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue }
const strings = { type: 'array', items: { type: 'string' } } as const
const common = {
  id: { type: 'string', required: true }, project_id: { type: 'string', required: true },
  expected_seq: { type: 'number', required: true }, proposal_version: { type: 'number', required: true },
  rationale: { type: 'string', required: true },
} as const
const output = { schema: { type: 'object', additionalProperties: true },
  render: (_args: unknown, value: unknown) => [{ type: 'text' as const, text: JSON.stringify(value) }] } as const
export function decisionBody(args: Record<string, unknown>, _agent: string, callId: string | undefined) {
  return { ...args, call_id: callId ?? null }
}
export function discoveryDecisionTools(config: BackendConfig, receipts: ApprovalReceipts): ProductTool[] {
  const propose = defineTool({
    name: 'discovery_decision_propose',
    description: 'Propose or revise an MVP decision based on exact recorded meeting minutes and the declared policy fingerprint. ' +
      'Revision discards previous votes and condition confirmations. This does not approve the project. Never invent eligible people or rules.',
    parameters: { proposal: { type: 'object', required: true, additionalProperties: false, properties: {
      id: { type: 'string', required: true }, project_id: { type: 'string', required: true },
      meeting_id: { type: 'string', required: true }, meeting_version: { type: 'number', required: true },
      selected_candidates: { ...strings, required: true }, scope: { ...strings, required: true }, exclusions: strings,
      rationale: { type: 'string', required: true }, policy_fingerprint: { type: 'string', required: true },
      expected_seq: { type: 'number', required: true }, conditions: { type: 'array', items: {
        type: 'object', additionalProperties: false, properties: {
          id: { type: 'string', required: true }, description: { type: 'string', required: true }, confirmer: { type: 'string', required: true },
        },
      } },
    } } }, output,
    async execute(args, exec) {
      return callBackend<Record<string, JsonValue>>(config, '/tools/discovery-decision-propose', decisionBody(args, '', exec.callId),
        exec.signal, receipts.take(JSON.stringify([exec.agent?.id, exec.callId])))
    },
  })
  const vote = defineTool({
    name: 'discovery_decision_vote',
    description: 'Record the approving employee\'s own yes/no/abstain vote on this exact proposal version. ' +
      'Never vote on behalf of a named attendee; verified identity determines the voter. Passing the tally is not project approval.',
    parameters: { ...common, choice: { type: 'string', required: true, enum: ['yes', 'no', 'abstain'] } }, output,
    async execute(args, exec) {
      return callBackend<Record<string, JsonValue>>(config, '/tools/discovery-decision-vote', decisionBody(args, '', exec.callId),
        exec.signal, receipts.take(JSON.stringify([exec.agent?.id, exec.callId])))
    },
  })
  const resolve = defineTool({
    name: 'discovery_decision_resolve',
    description: 'Record the assigned employee\'s sourced confirmation of one MVP condition. It does not release conditional approval; ' +
      'the declared approver must explicitly finalize again after all conditions are confirmed.',
    parameters: { ...common, condition_id: { type: 'string', required: true }, references: { ...references, required: true } }, output,
    async execute(args, exec) {
      return callBackend<Record<string, JsonValue>>(config, '/tools/discovery-decision-resolve', decisionBody(args, '', exec.callId),
        exec.signal, receipts.take(JSON.stringify([exec.agent?.id, exec.callId])))
    },
  })
  const finalize = defineTool({
    name: 'discovery_decision_finalize',
    description: 'The declared decision owner explicitly approves or rejects an exact MVP proposal. Approval requires the declared vote ' +
      'threshold; unresolved conditions produce only a conditional decision. Never claim release from votes alone or stale historical records.',
    parameters: { ...common, outcome: { type: 'string', required: true, enum: ['approve', 'reject'] } }, output,
    async execute(args, exec) {
      return callBackend<Record<string, JsonValue>>(config, '/tools/discovery-decision-finalize', decisionBody(args, '', exec.callId),
        exec.signal, receipts.take(JSON.stringify([exec.agent?.id, exec.callId])))
    },
  })
  return [
    withAccess(propose, { kind: 'approval', reason: 'Review the entire proposal and policy fingerprint. Revision resets all votes and confirmations.', denialEffect: 'No proposal was saved or revised', body: decisionBody }),
    withAccess(vote, { kind: 'approval', reason: 'Cast or replace your own vote on this exact proposal; this does not approve the project.', denialEffect: 'No vote was recorded', body: decisionBody }),
    withAccess(resolve, { kind: 'approval', reason: 'Confirm this condition with these exact sources as the assigned employee.', denialEffect: 'The condition remains unchanged', body: decisionBody }),
    withAccess(finalize, { kind: 'approval', reason: 'Record your explicit project decision. Unmet conditions withhold the Agent 2 handoff.', denialEffect: 'No project decision was recorded', body: decisionBody }),
  ]
}
