import { withAccess, type ProductTool } from '../tool-catalogue.ts'
import { defineTool } from '@deepseek-ai/dsh-tools'

import { callBackend, type BackendConfig } from '../backend.ts'

/**
 * Where this month's close has got to (E14-UC01).
 *
 * A read-only projection: each step's state comes from the module that owns it, so the
 * captain cannot tell someone a step is done while the page they open says otherwise. The
 * result carries counts and the names of what is outstanding — departments, issue kinds,
 * roles — never a row or a cell value.
 */
type Json = string | number | boolean | null | Json[] | { [key: string]: Json }

export function checklistTool(config: BackendConfig): ProductTool {
  return withAccess(defineTool({
    name: 'monthly_checklist',
    description: 'The monthly close checklist for a period: each declared step with its state (done, open, blocked, unknown), how many things are outstanding, who owns it, and whether the month is ready to close. Counts and names only, never rows.',
    parameters: { period: { type: 'string', required: true, description: 'YYYY-MM' } },
    output: { schema: { type: 'object', additionalProperties: true }, render: (_args, value) => {
      const result = value as { period?: string; ready_to_close?: boolean; refusal?: string
        steps?: { id: string; state: string; count: number; owner_role: string }[] }
      if (result.refusal) return [{ type: 'text', text: result.refusal }]
      const open = (result.steps ?? []).filter(s => s.state !== 'done')
      return [{ type: 'text', text: result.ready_to_close
        ? `${result.period}: every declared step is done.`
        : `${result.period}: ${open.length} step(s) outstanding — ` + open.map(s => `${s.id} (${s.state}${s.count ? ` ×${s.count}` : ''}, ${s.owner_role || 'unassigned'})`).join(' | ') }]
    } },
    async execute(args, exec) {
      return callBackend<Record<string, Json>>(config, '/tools/monthly-checklist', { period: args.period }, exec)
    },
  }), { kind: 'read' })
}

/**
 * What is still waiting on someone, across modules (E14-UC05).
 *
 * A projection with no handling state and no decisions: each item names where it is settled,
 * and settling happens in the module that holds the evidence and the approval.
 */
type InboxArgs = { department?: string; kind?: string }
type InboxText = { total?: number; by_kind?: Record<string, number>; by_department?: Record<string, number>
  items?: { kind: string; subject?: string; detail?: string; departments?: string[]; next_view?: string }[] }
/**
 * The items themselves, not only their counts. Counts alone sent a real captain back for
 * more: it re-asked by kind and by each department and got the same sentence every time,
 * because the filters narrow the items this render used to drop — seven calls for one
 * question. Capped, with the true total, as every tool result here is.
 */
export function renderInbox(args: InboxArgs, result: InboxText) {
  const kinds = Object.entries(result.by_kind ?? {}).map(([kind, n]) => `${kind} ${n}`).join(', ')
  const items = result.items ?? []
  const filter = [args.department && `department=${args.department}`, args.kind && `kind=${args.kind}`].filter(Boolean).join(', ')
  const lines = items.slice(0, 15).map(item => `- ${item.kind}: ${item.subject || '(no subject)'}${item.detail ? ` — ${item.detail}` : ''}`
    + ` [departments: ${(item.departments ?? []).join('/') || 'all'}; settled in: ${item.next_view || 'its module'}]`)
  return [{ type: 'text' as const, text: `${result.total ?? 0} open item(s) in the period (by kind: ${kinds || 'none'}). `
    + `${filter ? `Filtered by ${filter}: ` : ''}${items.length} listed${items.length > 15 ? ', first 15 shown' : ''}.`
    + (lines.length ? `\n${lines.join('\n')}` : '') }]
}

export function inboxTool(config: BackendConfig): ProductTool {
  return withAccess(defineTool({
    name: 'monthly_inbox',
    description: 'Open items for a period across modules (master questions, quarantined rows, column questions, a review left on corrected data): counts by kind and department, and each item with where it is settled. Never rows or cell values; the inbox decides nothing.',
    parameters: {
      period: { type: 'string', required: true, description: 'YYYY-MM' },
      department: { type: 'string', description: 'Narrow the listing to one department' },
      kind: { type: 'string', description: 'Narrow the listing to one kind of item' },
    },
    output: { schema: { type: 'object', additionalProperties: true }, render: (args, value) => renderInbox(args as InboxArgs, value as InboxText) },
    async execute(args, exec) {
      return callBackend<Record<string, Json>>(config, '/tools/monthly-inbox',
        { period: args.period, department: args.department ?? '', kind: args.kind ?? '' }, exec)
    },
  }), { kind: 'read' })
}
