import { withAccess, type ProductTool } from '../tool-catalogue.ts'
import { defineTool } from '@deepseek-ai/dsh-tools'

import { callBackend, type BackendConfig } from '../backend.ts'

/**
 * The month, quarter or year a batch falls in, against 环比 (prior) or 同比 (last_year) (#301).
 *
 * Quarters and years are added up from their month batches by the backend, under the
 * dictionary's declaration of how each measure adds across months; the model receives the
 * figures and the months they cover, never the rows, and never adds months up itself.
 * A refused figure comes back with its reason — say it, do not fill the gap.
 */
type Coverage = { months?: string[]; considered?: string[]; present?: string[]; missing?: string[]
  unusable?: Record<string, string>; complete?: boolean }
type Fact = { metric: string; unit?: string; value?: number | null; state: string; reason?: string; as_of?: string; source_count?: number }
type Change = { metric: string; unit?: string; current?: number | null; base?: number | null; absolute?: number | null
  relative?: number | null; basis?: string; state: string; reason?: string }
export type PeriodComparison = { grain?: string; period?: string; base_kind?: string; base_period?: string; status?: string
  reason?: string; current?: { coverage?: Coverage; facts?: Fact[] }; base?: { coverage?: Coverage } | null; changes?: Change[] }

function months(coverage: Coverage | undefined): string {
  if (!coverage) return '—'
  const missing = [...(coverage.missing ?? []), ...Object.keys(coverage.unusable ?? {})]
  return `${(coverage.present ?? []).join(', ') || 'none'}${missing.length ? `; lacking ${missing.join(', ')}` : ''}${coverage.complete ? '' : ' (incomplete period)'}`
}

function change(c: Change): string {
  if (c.state !== 'compared') return `${c.metric}: ${c.state}${c.reason ? ` — ${c.reason}` : ''}`
  const delta = c.basis === 'percentage_points' ? `${c.absolute} pt` : `${c.absolute}${c.relative == null ? '' : ` (${(c.relative * 100).toFixed(1)}%)`}`
  return `${c.metric}: ${c.current} ${c.unit ?? ''} against ${c.base}; change ${delta}`
}

/** Runs on replay too, so nothing here may assume a fully-shaped value. */
export function renderComparison(value: PeriodComparison) {
  const facts = value.current?.facts ?? []
  const lines = value.status === 'compared'
    ? (value.changes ?? []).map(change)
    : facts.map(f => f.state === 'computed'
      ? `${f.metric}: ${f.value} ${f.unit ?? ''}${f.as_of ? ` (balance as of ${f.as_of})` : ''}`
      : `${f.metric}: ${f.state}${f.reason ? ` — ${f.reason}` : ''}`)
  return [{ type: 'text' as const, text:
    `${value.period} (${value.grain}) against ${value.base_kind} ${value.base_period}: ${value.status}${value.reason ? ` — ${value.reason}` : ''}\n` +
    `months in ${value.period}: ${months(value.current?.coverage)}\n` +
    (value.base ? `months in ${value.base_period}: ${months(value.base.coverage)}\n` : '') +
    lines.map(l => `- ${l}`).join('\n') }]
}

export function comparePeriods(config: BackendConfig): ProductTool {
  return withAccess(defineTool({
    name: 'compare_periods',
    description:
      'Compare the month, quarter or year that a batch falls in against the previous period (prior, 环比) or the same ' +
      'period last year (last_year, 同比). Quarters and years are added up from their monthly batches by declared rules; ' +
      'ratios are recomputed from their parts. Returns each figure, which months it covers, and why any figure is ' +
      'refused (a month missing, a measure without a declared aggregation, a month-only metric). Never add months up ' +
      'yourself, and never present an incomplete period as a full one.',
    parameters: {
      batch_id: { type: 'string', required: true, description: 'Immutable batch id; the view is as of this batch\'s month' },
      grain: { type: 'string', enum: ['month', 'quarter', 'year'], description: 'Default quarter' },
      base: { type: 'string', enum: ['prior', 'last_year'], description: 'prior = 环比, last_year = 同比. Default prior' },
      metrics: {
        type: 'array', items: { type: 'string' },
        description: 'Declared metric names; omit for the brief\'s key metrics. An unknown name is refused with the declared list.',
      },
    },
    output: {
      schema: { type: 'object', additionalProperties: true },
      render: (_args, value) => renderComparison(value as PeriodComparison),
    },
    async execute(args, exec) {
      return callBackend<PeriodComparison>(config, '/tools/compare-periods', {
        batch_id: args.batch_id, grain: args.grain ?? 'quarter', base: args.base ?? 'prior', metrics: args.metrics ?? [],
      }, exec)
    },
  }), { kind: 'read' })
}
