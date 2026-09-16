import { defineTool } from '@deepseek-ai/dsh-tools'
import { callBackend, type BackendConfig } from '../backend.ts'
import type { ApprovalReceipts } from '../approval/receipts.ts'
import { withAccess, type ProductTool } from '../tool-catalogue.ts'

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue }
export const references = { type: 'array', items: { type: 'object', additionalProperties: false, properties: {
  material_id: { type: 'string', required: true }, version: { type: 'number', required: true },
  locator: { type: 'object', required: true, additionalProperties: false, properties: {
    kind: { type: 'string', required: true, enum: ['header', 'rows', 'lines'] },
    sheet: { type: 'string' }, start: { type: 'number' }, end: { type: 'number' },
  } },
} } } as const

export function graphBody(args: Record<string, unknown>, _agent: string, callId: string | undefined) {
  return { graph: args.graph, call_id: callId ?? null }
}
export function discoveryGraphSave(config: BackendConfig, receipts: ApprovalReceipts): ProductTool {
  return withAccess(defineTool({
    name: 'discovery_graph_save',
    description: 'Save a reviewed information/document flow draft against an exact opportunity version. ' +
      'Never infer edges from matching field or department names. Preserve missing/conflicting evidence, ' +
      'parallel branches and rework. Confirmed edges need explicit human confirmation. Saving executes no workflow.',
    parameters: { graph: { type: 'object', required: true, additionalProperties: false, properties: {
      id: { type: 'string', required: true }, project_id: { type: 'string', required: true },
      opportunity_id: { type: 'string', required: true }, opportunity_version: { type: 'number', required: true },
      title: { type: 'string', required: true }, expected_seq: { type: 'number', required: true },
      departments: { type: 'array', required: true, items: { type: 'string' } },
      nodes: { type: 'array', required: true, items: { type: 'object', additionalProperties: false, properties: {
        id: { type: 'string', required: true }, title: { type: 'string', required: true },
        department: { type: 'string', required: true }, role: { type: 'string', required: true },
        trigger: { type: 'string', required: true }, inputs: { type: 'array', items: { type: 'string' } },
        outputs: { type: 'array', items: { type: 'string' } }, references: { ...references, required: true },
      } } },
      edges: { type: 'array', required: true, items: { type: 'object', additionalProperties: false, properties: {
        id: { type: 'string', required: true }, source: { type: 'string', required: true }, target: { type: 'string', required: true },
        kind: { type: 'string', required: true, enum: ['information', 'document'] },
        status: { type: 'string', required: true, enum: ['confirmed', 'inferred', 'missing', 'conflict'] },
        rationale: { type: 'string', required: true }, condition: { type: 'string' }, rework: { type: 'boolean' },
        references, confirmation: { type: 'string' },
      } } },
    } } },
    output: { schema: { type: 'object', additionalProperties: true }, render: (_args, value) => [{ type: 'text', text: JSON.stringify(value) }] },
    async execute(args, exec) {
      return callBackend<Record<string, JsonValue>>(config, '/tools/discovery-graph-save',
        graphBody(args, exec.agent?.id ?? 'unknown-agent', exec.callId), exec.signal,
        receipts.take(JSON.stringify([exec.agent?.id, exec.callId])))
    },
  }), { kind: 'approval', reason: 'Save this exact flow draft, including uncertain edges and evidence. This does not execute the workflow.',
    denialEffect: 'No graph revision was saved. Do not claim the flow was confirmed or a project approved', body: graphBody })
}
