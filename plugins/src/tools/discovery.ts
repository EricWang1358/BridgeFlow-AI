import { defineTool } from '@deepseek-ai/dsh-tools'
import { callBackend, type BackendConfig } from '../backend.ts'
import type { ApprovalReceipts } from '../approval/receipts.ts'
import { withAccess, type ProductTool } from '../tool-catalogue.ts'

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue }

export function proposalBody(args: Record<string, unknown>, _agent: string, callId: string | undefined) {
  return { proposal: args.proposal, call_id: callId ?? null }
}

export function discoveryPropose(config: BackendConfig, receipts: ApprovalReceipts): ProductTool {
  return withAccess(defineTool({
    name: 'discovery_propose',
    description: 'Save a discovery opportunity draft after human review. This never approves an MVP or publishes ' +
      'business rules. Each claim needs a current material version and a validated source position. ' +
      'Retain assumptions as inferred and unresolved questions explicitly. Never invent source IDs or versions.',
    parameters: {
      proposal: {
        type: 'object', required: true,
        properties: {
          id: { type: 'string', required: true }, project_id: { type: 'string', required: true },
          title: { type: 'string', required: true }, expected_seq: { type: 'number', required: true },
          departments: { type: 'array', items: { type: 'string' }, required: true },
          open_questions: { type: 'array', items: { type: 'string' }, required: true },
          claims: { type: 'array', required: true, items: {
            type: 'object', additionalProperties: false, properties: {
              kind: { type: 'string', required: true, enum: ['problem', 'input', 'output', 'human_checkpoint', 'rule_dependency', 'value_hypothesis'] },
              text: { type: 'string', required: true },
              basis: { type: 'string', required: true, enum: ['reported', 'inferred'] },
              references: { type: 'array', required: true, items: {
                type: 'object', additionalProperties: false, properties: {
                  material_id: { type: 'string', required: true }, version: { type: 'number', required: true },
                  locator: { type: 'object', required: true, additionalProperties: false, properties: {
                    kind: { type: 'string', required: true, enum: ['header', 'rows', 'lines'] },
                    sheet: { type: 'string' }, start: { type: 'number' }, end: { type: 'number' },
                  } },
                },
              } },
            },
          } },
        }, additionalProperties: false,
      },
    },
    output: {
      schema: { type: 'object', additionalProperties: true },
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value) }],
    },
    async execute(args, exec) {
      return callBackend<Record<string, string | number>>(config, '/tools/discovery-propose',
        proposalBody(args, exec.agent?.id ?? 'unknown-agent', exec.callId), exec.signal,
        receipts.take(JSON.stringify([exec.agent?.id, exec.callId])))
    },
  }), {
    kind: 'approval', reason: 'Save this exact discovery proposal and its references. This is not MVP approval.',
    denialEffect: 'No proposal was saved. Keep unresolved questions and do not claim project approval',
    body: proposalBody,
  })
}

export function discoveryMaterials(config: BackendConfig): ProductTool {
  return withAccess(defineTool({
    name: 'discovery_materials',
    description: 'List registered material IDs, exact versions and source positions for a known discovery project. ' +
      'Returns at most ten materials and five sheet summaries each, with total counts and truncation. ' +
      'No raw rows, text or business meaning is returned. Ask the person for meaning; do not invent it from structure. ' +
      'Use these references for discovery_propose; an empty template is not actual business evidence.',
    parameters: {
      project_id: { type: 'string', required: true },
      material_id: { type: 'string', description: 'Optional exact material ID to inspect remaining sheets' },
      sheet_offset: { type: 'number', description: 'Zero-based sheet offset; requires material_id' },
      offset: { type: 'number', description: 'Zero-based offset, default 0' },
      limit: { type: 'number', description: 'Page size 1–10, default 5' },
    },
    output: {
      schema: { type: 'object', additionalProperties: true },
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value) }],
    },
    async execute(args, exec) {
      return callBackend<Record<string, JsonValue>>(config, '/tools/discovery-materials', args, exec.signal)
    },
  }), { kind: 'read' })
}

export function registrationBody(args: Record<string, unknown>, _agent: string, callId: string | undefined) {
  return { upload_id: args.upload_id, digest: args.digest, material: args.material, call_id: callId ?? null }
}

export function discoveryRegister(config: BackendConfig, receipts: ApprovalReceipts): ProductTool {
  return withAccess(defineTool({
    name: 'discovery_register',
    description: 'Register an uploaded discovery material after native approval. Use the exact upload ID, digest ' +
      'and metadata returned by the browser upload, never file paths or raw file content. Registration retains ' +
      'parser failures and unsupported formats explicitly; it does not validate business rules or approve a project.',
    parameters: {
      upload_id: { type: 'string', required: true }, digest: { type: 'string', required: true },
      material: { type: 'object', required: true, additionalProperties: false, properties: {
        id: { type: 'string', required: true }, project_id: { type: 'string', required: true },
        department: { type: 'string', required: true }, period: { type: 'string', required: true },
        filename: { type: 'string', required: true }, expected_seq: { type: 'number', required: true },
        declared_kind: { type: 'string', required: true, enum: ['template', 'records', 'narrative', 'meeting', 'rule'] },
        source_description: { type: 'string', required: true },
      } },
    },
    output: {
      schema: { type: 'object', additionalProperties: true },
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value) }],
    },
    async execute(args, exec) {
      return callBackend<Record<string, JsonValue>>(config, '/tools/discovery-register',
        registrationBody(args, exec.agent?.id ?? 'unknown-agent', exec.callId), exec.signal,
        receipts.take(JSON.stringify([exec.agent?.id, exec.callId])))
    },
  }), { kind: 'approval', reason: 'Register this exact uploaded file and its stated provenance. This does not approve its business rules.',
    denialEffect: 'No material was registered. The temporary upload expires; do not claim it is available as evidence',
    body: registrationBody })
}
