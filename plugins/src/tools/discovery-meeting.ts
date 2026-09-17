import { defineTool } from '@deepseek-ai/dsh-tools'
import { callBackend, type BackendConfig } from '../backend.ts'
import type { ApprovalReceipts } from '../approval/receipts.ts'
import { withAccess, type ProductTool } from '../tool-catalogue.ts'
import { references } from './discovery-graph.ts'

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue }
const statement = { type: 'object', additionalProperties: false, properties: {
  text: { type: 'string', required: true }, basis: { type: 'string', required: true, enum: ['reported', 'assumption'] }, references,
} } as const
const statements = { type: 'array', items: statement } as const
const strings = { type: 'array', items: { type: 'string' } } as const
export function meetingBody(args: Record<string, unknown>, _agent: string, callId: string | undefined) {
  return { meeting: args.meeting, call_id: callId ?? null }
}
export function discoveryMeetingSave(config: BackendConfig, receipts: ApprovalReceipts): ProductTool {
  return withAccess(defineTool({
    name: 'discovery_meeting_save',
    description: 'Save reviewed meeting preparation or minutes against exact candidate versions. Record scope, risks, ' +
      'resource assumptions, stage dependencies/exit criteria and questions. Reported statements need sources; ' +
      'estimates must be assumptions. Attendance is reported, not verified voting. This never approves an MVP or sends notifications.',
    parameters: { meeting: { type: 'object', required: true, additionalProperties: false, properties: {
      id: { type: 'string', required: true }, project_id: { type: 'string', required: true }, title: { type: 'string', required: true },
      candidates: { type: 'array', required: true, items: { type: 'object', additionalProperties: false, properties: {
        id: { type: 'string', required: true }, version: { type: 'number', required: true },
      } } },
      scope: { ...statements, required: true }, exclusions: strings, risks: statements, resources: statements,
      stages: { type: 'array', required: true, items: { type: 'object', additionalProperties: false, properties: {
        id: { type: 'string', required: true }, title: { type: 'string', required: true }, owner_role: { type: 'string', required: true },
        exit_criteria: { ...strings, required: true }, depends_on: strings, rationale: { ...statement, required: true },
      } } },
      discussion_questions: strings, phase: { type: 'string', enum: ['preparation', 'minutes'] },
      participants: strings, minutes: statements, change_reason: { type: 'string', required: true },
      expected_seq: { type: 'number', required: true },
    } } },
    output: { schema: { type: 'object', additionalProperties: true }, render: (_args, value) => [{ type: 'text', text: JSON.stringify(value) }] },
    async execute(args, exec) {
      return callBackend<Record<string, JsonValue>>(config, '/tools/discovery-meeting-save',
        meetingBody(args, exec.agent?.id ?? 'unknown-agent', exec.callId), exec.signal,
        receipts.take(JSON.stringify([exec.agent?.id, exec.callId])))
    },
  }), { kind: 'approval', reason: 'Save this exact meeting preparation or minutes with its source versions and assumptions. This is not project approval.',
    denialEffect: 'No meeting revision was saved. Do not claim a meeting decision or approved project', body: meetingBody })
}
