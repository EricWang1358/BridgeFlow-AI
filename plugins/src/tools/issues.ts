import { withAccess, type ProductTool } from '../tool-catalogue.ts'
import { defineTool } from '@deepseek-ai/dsh-tools'

import { callBackend, type BackendConfig } from '../backend.ts'

/**
 * Agent-readable issue details and the bounded cell read (#245).
 *
 * `batch_issues` is the right-hand panel as the model may see it: every open item
 * with the tool that settles it — corrections with their change and rule, held rows
 * WITHOUT their values, intake findings, stale matches, column questions, unresolved
 * mappings. `quarantine_row` is the one bounded read the revised boundary allows:
 * exactly one held row per call — values, the headers as uploaded, provenance, the
 * checks it fails — each read written to the cell-access log. Neither decides
 * anything; disposal still goes through quarantine_decide's approval gate.
 */

const anyObject = { schema: { type: 'object' as const, additionalProperties: true as const } }

interface IssueItem {
  id: string
  kind: string
  department: string
  subject: string
  detail: string
  next_step: string
  checks?: string[]
  releasable?: boolean | null
  rule?: string
  before?: unknown
  after?: unknown
  severity?: string
}

interface BatchIssues {
  batch_id: string
  status: string
  total: number
  truncated: boolean
  counts: Record<string, number>
  items: IssueItem[]
  next_step: string
}

export function batchIssues(config: BackendConfig): ProductTool {
  return withAccess(defineTool({
    name: 'batch_issues',
    description:
      'Everything waiting on somebody in one batch, as the data panel shows it: sanitizer corrections ' +
      '(with before/after and rule), quarantined rows (checks only — read values with quarantine_row), ' +
      'intake findings, dropped columns, stale matches, column questions, unresolved mappings. ' +
      'Each item names the tool that settles it. Walk the person through them item by item.',
    parameters: {
      batch_id: { type: 'string', required: true, description: 'The batch to enumerate' },
    },
    output: {
      ...anyObject,
      render: (_args, value) => {
        const issues = value as unknown as BatchIssues
        const lines = (issues.items ?? []).slice(0, 12).map(item => {
          const change = item.before !== undefined && item.before !== null
            ? ` (${item.rule}: ${JSON.stringify(item.before)} → ${JSON.stringify(item.after)})` : ''
          const checks = item.checks?.length ? ` [${item.checks.join('; ')}]` : ''
          return `${item.kind} ${item.department ? item.department + '.' : ''}${item.subject}${change}${checks}`
        })
        return [{
          type: 'text',
          text: `${issues.total} open item(s): ${JSON.stringify(issues.counts)}.` +
            (lines.length ? ` ${lines.join(' | ')}` : '') +
            (issues.truncated ? ' (list truncated)' : '') + ` ${issues.next_step}`,
        }]
      },
    },
    async execute(args, exec) {
      return callBackend(config, '/tools/batch-issues', { batch_id: args.batch_id }, exec)
    },
  }), { kind: 'read' })
}

export function quarantineRow(config: BackendConfig): ProductTool {
  return withAccess(defineTool({
    name: 'quarantine_row',
    description:
      'Read exactly one quarantined row: its cell values, the headers as the department wrote them, ' +
      'the file and sheet it came from, and the checks it currently fails. This is the evidence for ' +
      'proposing a fix to the person — one row per call, each read is logged. Never read rows nobody ' +
      'asked about; propose fixes only for cells you can support from this row and explain, and let ' +
      'the person decide via quarantine_decide.',
    parameters: {
      batch_id: { type: 'string', required: true, description: 'The batch holding the row' },
      department: { type: 'string', required: true, description: 'Department of the held row' },
      index: { type: 'number', required: true, description: 'Row position from quarantine_list or batch_issues' },
    },
    output: {
      ...anyObject,
      render: (_args, value) => {
        const row = value as unknown as {
          department: string, index: number, values: Record<string, unknown>,
          original_columns: Record<string, string>, filename: string, sheet: string,
          failing_checks: string[], releasable: boolean, shift_suggestion: string, next_step: string,
        }
        const cells = Object.entries(row.values ?? {}).map(([name, v]) =>
          `${row.original_columns?.[name] ?? name}=${JSON.stringify(v)}`).join(', ')
        return [{
          type: 'text',
          text: `${row.department} held row ${row.index} (${row.filename}${row.sheet ? ` · ${row.sheet}` : ''}): ` +
            `${cells}. Fails: ${row.failing_checks?.join('; ') || 'nothing — releasable'}.` +
            (row.shift_suggestion ? ` A ${row.shift_suggestion} shift would pass.` : '') +
            ` ${row.next_step}`,
        }]
      },
    },
    async execute(args, exec) {
      return callBackend(config, '/tools/quarantine-row',
        { batch_id: args.batch_id, department: args.department, index: args.index }, exec)
    },
  }), { kind: 'read' })
}
