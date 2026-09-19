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
      return callBackend<Record<string, Json>>(config, '/tools/monthly-checklist', { period: args.period }, exec.signal)
    },
  }), { kind: 'read' })
}
