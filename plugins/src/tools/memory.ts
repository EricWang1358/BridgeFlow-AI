import { withAccess, type ProductTool } from '../tool-catalogue.ts'
import { defineTool } from '@deepseek-ai/dsh-tools'

import { callBackend, type BackendConfig } from '../backend.ts'
import type { ApprovalReceipts } from '../approval/receipts.ts'

/**
 * Long-term memory (#303): solutions worth keeping beyond one conversation.
 *
 * Searching is a read the captain makes before working a problem out again. Saving and
 * retiring are the person's decision, so both need approval and the approver is who the
 * record names. A memory holds the method and the conclusion with where it came from —
 * never spreadsheet rows — and a retired one stays in the history but is no longer found.
 */
type Json = string | number | boolean | null | Json[] | { [key: string]: Json }

const departments = { type: 'array', items: { type: 'string', enum: ['production', 'procurement', 'finance', 'marketing'] } } as const
const anyObject = { schema: { type: 'object' as const, additionalProperties: true as const } }

type Found = { memories?: { id: string; title: string; problem: string; solution: string; source: string
  departments: string[]; version: number }[]; next_step?: string }
/** The render is all the model reads: each memory's id and version (for revising) and its full text. */
export function renderMemories(result: Found) {
  const items = result.memories ?? []
  if (!items.length) return [{ type: 'text' as const, text: String(result.next_step ?? 'No saved memory matches.') }]
  return [{ type: 'text' as const, text: items.map(m => `[${m.id} v${m.version}] ${m.title}\n`
    + `departments: ${m.departments.length ? m.departments.join(', ') : 'company-wide'}; source: ${m.source}\n`
    + `problem: ${m.problem}\nsolution: ${m.solution}`).join('\n\n') + `\n\n${result.next_step ?? ''}` }]
}

export function saveBody(args: Record<string, unknown>, agentId: string, callId: string | undefined) {
  return { title: args.title, problem: args.problem, solution: args.solution, source: args.source,
    departments: Array.isArray(args.departments) ? args.departments : [],
    tags: Array.isArray(args.tags) ? args.tags : [],
    memory_id: typeof args.memory_id === 'string' && args.memory_id ? args.memory_id : null,
    expected_version: typeof args.expected_version === 'number' ? args.expected_version : null,
    note: args.note ?? '', confirmed_by: agentId, call_id: callId ?? null }
}

export function retireBody(args: Record<string, unknown>, agentId: string, callId: string | undefined) {
  return { memory_id: args.memory_id, reason: args.reason,
    expected_version: typeof args.expected_version === 'number' ? args.expected_version : null,
    confirmed_by: agentId, call_id: callId ?? null }
}

export function memorySearch(config: BackendConfig): ProductTool {
  return withAccess(defineTool({
    name: 'memory_search',
    description: 'Search the company\'s long-term memory: solutions people saved from earlier conversations, each with the problem, '
      + 'the solution, where it came from and the departments it concerns. Search before working out a recurring problem again. '
      + 'Returns the best matches with their id and version; no batch data.',
    parameters: {
      query: { type: 'string', required: true, description: 'The problem in a few words, in the person\'s language' },
      department: { type: 'string', enum: ['production', 'procurement', 'finance', 'marketing'],
        description: 'Only this department\'s memories and company-wide ones' },
      limit: { type: 'number', description: 'At most this many matches, 1-10; 5 by default' },
    },
    output: { ...anyObject, render: (_args, value) => renderMemories(value as Found) },
    async execute(args, exec) {
      return callBackend<Record<string, Json>>(config, '/tools/memory-search',
        { query: args.query, department: args.department ?? null, limit: typeof args.limit === 'number' ? args.limit : 5 }, exec)
    },
  }), { kind: 'read' })
}

export function memorySave(config: BackendConfig, receipts: ApprovalReceipts): ProductTool {
  return withAccess(defineTool({
    name: 'memory_save',
    description: 'Save a solution the person settled on to long-term memory, or revise one (memory_id and the expected_version '
      + 'memory_search showed). Only when the person agrees it is worth keeping. Record the method and the conclusion in their '
      + 'words with the source they name — never spreadsheet rows or cell values. Requires approval.',
    parameters: {
      title: { type: 'string', required: true, description: 'What it is about, at most 80 characters' },
      problem: { type: 'string', required: true, description: 'The problem as it showed up' },
      solution: { type: 'string', required: true, description: 'What to do about it, as the person settled it' },
      source: { type: 'string', required: true, description: 'Where the solution comes from: this conversation, a meeting note or document the person named. Never your own reasoning alone.' },
      departments: { ...departments, description: 'Departments it concerns; empty means company-wide' },
      tags: { type: 'array', items: { type: 'string' }, description: 'A few short keywords that help find it' },
      memory_id: { type: 'string', description: 'Revising: the memory to revise' },
      expected_version: { type: 'number', description: 'Revising: the version memory_search showed' },
      note: { type: 'string', description: 'Revising: why it changed' },
    },
    output: { ...anyObject, render: (_args, value) => [{ type: 'text', text: String((value as { next_step?: string }).next_step ?? 'Saved.') }] },
    async execute(args, exec) {
      return callBackend<Record<string, Json>>(config, '/tools/memory-save', saveBody(args, exec.agent?.id ?? 'unknown-agent', exec.callId),
        exec, receipts.take(JSON.stringify([exec.agent?.id, exec.callId])))
    },
  }), {
    kind: 'approval',
    reason: 'Save this solution to long-term memory. Later conversations will find it and may suggest it again; it records you as the person who saved it.',
    denialEffect: 'Nothing was saved to long-term memory. Do NOT describe it as remembered',
    body: saveBody,
    precheck: args => [args.title, args.problem, args.solution, args.source].every(v => typeof v === 'string' && v.trim())
      ? null : 'A memory needs a title, the problem, the solution and its source; ask the person for what is missing.',
  })
}

export function memoryRetire(config: BackendConfig, receipts: ApprovalReceipts): ProductTool {
  return withAccess(defineTool({
    name: 'memory_retire',
    description: 'Retire a memory that no longer holds (the process or the agreement changed), with the person\'s reason. '
      + 'It stays in the history but search stops finding it. Requires approval.',
    parameters: {
      memory_id: { type: 'string', required: true },
      reason: { type: 'string', required: true, description: 'Why it no longer holds, in the person\'s words' },
      expected_version: { type: 'number', description: 'The version memory_search showed' },
    },
    output: { ...anyObject, render: (_args, value) => [{ type: 'text', text: String((value as { next_step?: string }).next_step ?? 'Retired.') }] },
    async execute(args, exec) {
      return callBackend<Record<string, Json>>(config, '/tools/memory-retire', retireBody(args, exec.agent?.id ?? 'unknown-agent', exec.callId),
        exec, receipts.take(JSON.stringify([exec.agent?.id, exec.callId])))
    },
  }), {
    kind: 'approval',
    reason: 'Retire this memory: search stops finding it, and its history stays readable.',
    denialEffect: 'The memory was not retired and is still found by search',
    body: retireBody,
  })
}
