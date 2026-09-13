import { isNotebookKind, type NotebookKind } from './notebook-capabilities.ts'
import { z } from 'zod'
import { defineDomain, domainTable, type KvTable } from '@deepseek-ai/dsh-storage-domain'
import type { Context } from '@deepseek-ai/cordis'
import type {} from '@deepseek-ai/dsh-api-session-controller'
import type { SessionId } from '@deepseek-ai/dsh-session'

export type Notebook = { title: string; kind?: NotebookKind; batch?: string; view?: string; source?: string; report?: string }
const views = new Set(['integration', 'handoff', 'state', 'source', 'artifact', 'quotation', 'master', 'mappings', 'corrections', 'quarantine', 'review'])
const departments = new Set(['production', 'procurement', 'finance', 'marketing'])

/** This is navigation metadata, never a prompt, model fact, or approval grant. */
export function parseNotebook(value: unknown): Notebook {
  if (!value || typeof value !== 'object') throw new Error('Invalid notebook')
  const data = value as Record<string, unknown>
  if (typeof data.title !== 'string' || !data.title.trim() || data.title.length > 120) throw new Error('Notebook title is required (maximum 120 characters)')
  const result: Notebook = { title: data.title.trim() }
  if (data.kind !== undefined) {
    if (!isNotebookKind(data.kind)) throw new Error('Invalid notebook kind')
    result.kind = data.kind
  }
  for (const key of ['batch', 'report'] as const) {
    if (data[key] === undefined) continue
    if (typeof data[key] !== 'string' || !/^[a-f0-9]{32}$/.test(data[key])) throw new Error(`Invalid ${key}`)
    result[key] = data[key]
  }
  if (data.view !== undefined) {
    if (typeof data.view !== 'string' || !views.has(data.view)) throw new Error('Invalid view')
    result.view = data.view
  }
  if (data.source !== undefined) {
    if (typeof data.source !== 'string' || !departments.has(data.source)) throw new Error('Invalid source')
    result.source = data.source
  }
  if ((result.source || result.report) && !result.batch) throw new Error('A batch is required for a source or report')
  return result
}

const notebookSchema = z.custom<Notebook>(value => {
  try { parseNotebook(value); return true } catch { return false }
})
export type ApprovalNote = {sessionId:string; callId:string; note:string; author:string; time:number; status?:'draft'|'final'|'unused'|undefined; outcome?:string|undefined}
export const notebookDomain = defineDomain({name:'bridgeflow_notebooks',version:1,layout:'per-record',tables:{
  notebooks:domainTable<string,Notebook>(notebookSchema),
  approval_notes:domainTable<string,ApprovalNote>(z.object({sessionId:z.string(),callId:z.string(),note:z.string().max(240),author:z.string(),time:z.number(),status:z.enum(['draft','final','unused']).optional(),outcome:z.string().optional()})),
}})
export type NotebookTable = KvTable<string,Notebook>

export async function readNotebook(ctx: Context, id: SessionId, table:NotebookTable): Promise<Notebook | null> {
  await ctx.sessionController.inspect(id)
  return table.get(id) ?? null
}

export async function saveNotebook(ctx: Context, id: SessionId, notebook: Notebook, table:NotebookTable): Promise<void> {
  const resolved = await ctx.sessionController.resolveAgent(id)
  if ('error' in resolved) throw new Error(resolved.error.message)
  // The pinned Session.append API cannot mark downstream events ignorable.
  // Keep plugin metadata in the official domain store, never in an unreadable log.
  await ctx.sessionController.rename({ sessionId: id, title: notebook.title })
  if (!await ctx.sessions.flush(resolved.agent.session)) throw new Error('Session persistence is unavailable; notebook was not confirmed saved')
  await table.put(id,notebook)
}
