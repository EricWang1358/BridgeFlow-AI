import { withAccess, type ProductTool } from '../tool-catalogue.ts'
import { defineTool } from '@deepseek-ai/dsh-tools'

import { callBackend, type BackendConfig } from '../backend.ts'
import type { ApprovalReceipts } from '../approval/receipts.ts'

/**
 * The dictionary draft lifecycle (#205, E05-UC07/UC08): profiles → draft (transcribed
 * from the business's OA dictionary spreadsheet, or proposed from column statistics)
 * → decide entry by entry → publish as a new version.
 *
 * Publishing never happens without a person: the draft tools hand the model the
 * evidence and the person the decision, and the publish is the widest grant in the
 * system. Every write is approval-gated and validated host-side before the approval
 * is spent.
 */

type Json = string | number | boolean | null | Json[] | { [key: string]: Json }

export interface DraftResult {
  draft_id: string
  source: string
  basis: string
  departments: string[]
  missing_departments: string[]
  entries: number
  pending: number
  unmapped: number
  notes: string[]
  model_call?: { provider: string, model: string, started_at: string, finished_at: string } | null
  next_step: string
}

export function draftBody(args: Record<string, unknown>, agentId: string, callId: string | undefined) {
  return { batch_id: args.batch_id, confirmed_by: agentId, call_id: callId ?? null }
}

export function importBody(args: Record<string, unknown>, agentId: string, callId: string | undefined) {
  return { file_token: args.file_token, confirmed_by: agentId, call_id: callId ?? null }
}

export function decideBody(args: Record<string, unknown>, agentId: string, callId: string | undefined) {
  return {
    draft_id: args.draft_id, entry_id: args.entry_id, decision: args.decision, reason: args.reason ?? '',
    column: args.column ?? '', role: args.role ?? '', rollup: args.rollup ?? '',
    confirmed_by: agentId, call_id: callId ?? null,
  }
}

export function publishBody(args: Record<string, unknown>, agentId: string, callId: string | undefined) {
  return { draft_id: args.draft_id, confirmed_by: agentId, call_id: callId ?? null }
}

function renderDraft(value: DraftResult) {
  const missing = value.missing_departments ?? []
  return `${value.entries} entry(ies) from ${value.basis} (${value.source}); ` +
    `${value.pending} undecided.` +
    (missing.length ? ` No declaration for: ${missing.join(', ')} — nothing was inferred.` : '') +
    ` ${value.next_step}`
}

export function dictionaryProfiles(config: BackendConfig): ProductTool {
  return withAccess(defineTool({
    name: 'dictionary_profiles',
    description:
      'Per-department column statistics of one batch: type, fill rate, uniqueness, cross-department ' +
      'value overlap, plus which departments the dictionary leaves undeclared. No cell values. ' +
      'This is the input dictionary drafting works from, and the honest picture to show the person.',
    parameters: {
      batch_id: { type: 'string', required: true, description: 'The batch to profile' },
    },
    output: {
      schema: { type: 'object', properties: { batch_id: { type: 'string' } }, additionalProperties: true },
      render: (_args, value) => [{
        type: 'text',
        text: `Column profiles for batch ${value.batch_id ?? ''}. ` +
          `${((value.columns ?? []) as unknown as unknown[]).length} column(s); ` +
          `${((value.overlaps ?? []) as unknown as unknown[]).length} cross-department overlap(s); ` +
          `undeclared: ${((value.undeclared ?? []) as unknown as string[]).join(', ') || 'none'}.`,
      }],
    },
    async execute(args, exec) {
      return callBackend(config, '/tools/dictionary-profiles', { batch_id: args.batch_id }, exec)
    },
  }), { kind: 'read' })
}

export function dictionaryDraftView(config: BackendConfig): ProductTool {
  return withAccess(defineTool({
    name: 'dictionary_draft_view',
    description:
      'One dictionary draft with every entry: department, column, role, evidence, uncertainty and ' +
      'its decision. Read this aloud to the person before asking them to decide each entry.',
    parameters: {
      draft_id: { type: 'string', required: true, description: 'The draft to show' },
    },
    output: {
      schema: { type: 'object', properties: { draft_id: { type: 'string' } }, additionalProperties: true },
      render: (_args, value) => [{
        type: 'text',
        text: ((value.entries ?? []) as unknown as { department: string, column: string, role: string, decision: string, evidence: string }[])
          .map(entry => `${entry.department}.${entry.column} → ${entry.role} [${entry.decision}] ${entry.evidence}`).join(' | ') ||
          'The draft has no entries.',
      }],
    },
    async execute(args, exec) {
      return callBackend(config, '/tools/dictionary-draft-view', { draft_id: args.draft_id }, exec)
    },
  }), { kind: 'read' })
}

export function dictionaryImport(config: BackendConfig, receipts: ApprovalReceipts): ProductTool {
  return withAccess(defineTool({
    name: 'dictionary_import',
    description:
      'Transcribe the business\'s OA dictionary spreadsheet (a Feishu file token the person gives you) ' +
      'into a dictionary draft. Deterministic and free — no model runs. Common-key String rows become ' +
      'entity declarations, Number rows become measures whose rollup the person must still name. ' +
      'Requires approval; the draft changes nothing until every entry is decided and published.',
    parameters: {
      file_token: { type: 'string', required: true, description: 'Feishu Drive token of the dictionary spreadsheet' },
    },
      output: {
        schema: {
          type: 'object', additionalProperties: true,
          properties: {
            draft_id: { type: 'string' }, entries: { type: 'number' }, pending: { type: 'number' },
            missing_departments: { type: 'array', items: { type: 'string' } }, next_step: { type: 'string' },
            version: { type: 'string' }, decision: { type: 'string' }, dictionary: { type: 'string' },
          },
        },
        render: (_args, value) => [{ type: 'text', text: renderDraft(value as unknown as DraftResult) }],
      },
    async execute(args, exec) {
      return callBackend<Record<string, Json>>(config, '/tools/dictionary-import',
        importBody(args, exec.agent?.id ?? 'unknown-agent', exec.callId),
        exec, receipts.take(JSON.stringify([exec.agent?.id, exec.callId])))
    },
  }), {
    kind: 'approval',
    reason: 'Turn this OA dictionary spreadsheet into a draft. Nothing is declared or published yet.',
    denialEffect: 'No draft was created. Do NOT present transcribed entries as decided or published',
    body: importBody,
  })
}

export function dictionaryDraft(config: BackendConfig, receipts: ApprovalReceipts): ProductTool {
  return withAccess(defineTool({
    name: 'dictionary_draft',
    description:
      'Propose the missing dictionary declarations from one batch\'s column statistics (dictionary_profiles ' +
      'is the same input, shown first). A billed model call, recorded either way; every proposal without ' +
      'evidence is dropped host-side. Requires approval. Nothing is decided by this call.',
    parameters: {
      batch_id: { type: 'string', required: true, description: 'The batch whose columns the draft works from' },
    },
      output: {
        schema: {
          type: 'object', additionalProperties: true,
          properties: {
            draft_id: { type: 'string' }, entries: { type: 'number' }, pending: { type: 'number' },
            missing_departments: { type: 'array', items: { type: 'string' } }, next_step: { type: 'string' },
            version: { type: 'string' }, decision: { type: 'string' }, dictionary: { type: 'string' },
          },
        },
        render: (_args, value) => [{ type: 'text', text: renderDraft(value as unknown as DraftResult) }],
      },
    async execute(args, exec) {
      return callBackend<Record<string, Json>>(config, '/tools/dictionary-draft',
        draftBody(args, exec.agent?.id ?? 'unknown-agent', exec.callId),
        exec, receipts.take(JSON.stringify([exec.agent?.id, exec.callId])))
    },
  }), {
    kind: 'approval',
    reason: 'Run the billed drafting call on this batch\'s column statistics. The output is a draft, never a declaration.',
    denialEffect: 'No draft was created and no model call was billed. Do NOT claim a draft exists',
    body: draftBody,
  })
}

export function dictionaryDecide(config: BackendConfig, receipts: ApprovalReceipts): ProductTool {
  return withAccess(defineTool({
    name: 'dictionary_decide',
    description:
      'Record the person\'s decision on one draft entry: accepted, modified (give column and/or role — the ' +
      'replacement wins) or rejected (with their reason). A measure entry needs its rollup (sum / average / ' +
      'period_end) named in the same decision. Requires approval; this is the person deciding, not you.',
    parameters: {
      draft_id: { type: 'string', required: true, description: 'The draft being reviewed' },
      entry_id: { type: 'string', required: true, description: 'Entry id from dictionary_draft_view' },
      decision: { type: 'string', required: true, description: 'accepted, modified or rejected' },
      reason: { type: 'string', description: 'The person\'s reason, kept with the decision' },
      column: { type: 'string', description: 'modified: the replacement column' },
      role: { type: 'string', description: 'modified: entity:<kind> / measure:<name> / period / currency' },
      rollup: { type: 'string', description: 'sum / average / period_end, required for measures' },
    },
    output: {
      schema: {
        type: 'object', additionalProperties: true,
        properties: {
          entry_id: { type: 'string' }, decision: { type: 'string' },
          pending: { type: 'number' }, next_step: { type: 'string' },
          decided_by: { type: 'string' },
        },
      },
      render: (_args, value) => [{
        type: 'text',
        text: `${value.decision} ${value.entry_id}. ${value.pending} entry(ies) still undecided. ${value.next_step}`,
      }],
    },
    async execute(args, exec) {
      return callBackend(config, '/tools/dictionary-draft-decide',
        decideBody(args, exec.agent?.id ?? 'unknown-agent', exec.callId),
        exec, receipts.take(JSON.stringify([exec.agent?.id, exec.callId])))
    },
  }), {
    kind: 'approval',
    reason: 'Record this person\'s decision on one dictionary draft entry.',
    denialEffect: 'The entry stays undecided. Do NOT claim a decision was recorded',
    body: decideBody,
  })
}

export function dictionaryPublish(config: BackendConfig, receipts: ApprovalReceipts): ProductTool {
  return withAccess(defineTool({
    name: 'dictionary_publish',
    description:
      'Publish a fully-decided draft as a new dictionary version. Refused unless every entry has a decision, ' +
      'every measure has its rollup, and the merged dictionary passes the import side\'s own checks. ' +
      'Only later imports are affected; frozen batches keep their dictionary. Requires approval.',
    parameters: {
      draft_id: { type: 'string', required: true, description: 'The draft to publish' },
    },
    output: {
      schema: {
        type: 'object', additionalProperties: true,
        properties: {
          draft_id: { type: 'string' }, version: { type: 'string' },
          dictionary: { type: 'string' }, next_step: { type: 'string' },
        },
      },
      render: (_args, value) => [{
        type: 'text',
        text: `Published ${value.draft_id} as ${value.version}. ${value.next_step}`,
      }],
    },
    async execute(args, exec) {
      return callBackend(config, '/tools/dictionary-draft-publish',
        publishBody(args, exec.agent?.id ?? 'unknown-agent', exec.callId),
        exec, receipts.take(JSON.stringify([exec.agent?.id, exec.callId])))
    },
  }), {
    kind: 'approval',
    reason: 'Write this decided draft as the new dictionary version. This is the widest write in the system.',
    denialEffect: 'No version was written and the active dictionary is unchanged. Do NOT claim the dictionary changed',
    body: publishBody,
  })
}
