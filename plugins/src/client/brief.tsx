import { useEffect, useState } from 'react'
import { MetricCharts } from './charts.tsx'
import { api, describeError, navigate, useUI } from './ui.ts'
import { Chip } from './workspace.tsx'

/**
 * The one-page monthly brief (E13-UC01) with evidence grades (E13-UC06).
 *
 * Read-only and model-free: the backend projects the saved review, the frozen batch and its
 * master table. Order and key metrics come from the dictionary's brief declaration; nothing
 * here re-ranks, re-computes or re-words a figure.
 */
type Grade = { grade: string | null; chain: string[]; missing: string[] }
type Change = { metric?: string; field?: string; unit?: string; current: number | null; base: number | null; absolute: number | null; relative: number | null; basis?: string; state: string; key?: string[]; breach?: string }
type Totals = { field: string; current: number; base: number; absolute: number; relative: number | null; new_entities: number; discontinued: number; continuing: number }
type Comparison = { base_kind: string; base_period: string; base_batch_id: string; status: string; reason: string; changed_fields: string[]; metrics: Change[]; totals: Totals[]; breaches: Change[] }
type Metric = { metric: string; check_id: string; title: string; value: number; unit: string; status: string; formula: string; source_count: number; owner: string; grade: Grade; change: Change | null }
type Attention = { check_id: string; title: string; metric: string; value: number; unit: string; threshold: number; attention_when: string; owner: string; decision_owner: string; action: string; explanation: string; grade: Grade; advice_grade: Grade }
type Brief = {
  period: string; bound: Record<string, string>; report_status: string; stale: boolean; latest_report_id: string; missing_departments: string[]
  headline: { attention: number; ok: number; open_items: number; missing_departments: number }
  key_metrics: Metric[]; attention: Attention[]; open_items: Record<string, number>; completeness: Record<string, number>
  grade_summary: Record<string, number>; manager_decision: string; limitations: string[]; comparison: Comparison | null
}

const number = (value: number, unit: string) => `${value.toLocaleString(undefined, { maximumFractionDigits: unit === '%' ? 2 : 2 })}${unit === '%' ? '%' : ` ${unit}`}`

function ChangeMark({ change, unit }: { change: Change | null; unit: string }) {
  const { t } = useUI()
  if (!change) return null
  if (change.state === 'not_computable') return <small className="bf-change" data-state="none">{t('comparisonNotComputable')}</small>
  if (change.state !== 'compared' || change.absolute === null) return <small className="bf-change" data-state="none">{t('comparisonMissingBase')}</small>
  const sign = change.absolute > 0 ? '+' : ''
  // A metric that is already a ratio changes by points; a ratio of two ratios misleads (D7).
  const amount = change.basis === 'percentage_points'
    ? `${sign}${change.absolute.toFixed(2)} ${t('percentagePoints')}`
    : `${sign}${number(change.absolute, unit)}${change.relative === null ? '' : `（${sign}${(change.relative * 100).toFixed(1)}%）`}`
  return <small className="bf-change" data-state={change.absolute === 0 ? 'flat' : change.absolute > 0 ? 'up' : 'down'}>{amount}</small>
}

export function GradeMark({ grade }: { grade: Grade }) {
  const { t } = useUI()
  const label = grade.grade ?? t('gradeMissing')
  const why = [...grade.chain, ...grade.missing].join('\n')
  return <span className="bf-grade" data-grade={grade.grade ?? 'missing'} title={why} aria-label={`${t('evidenceGrade')} ${label}: ${why}`}>{label}</span>
}

export function MonthlyBrief({ batchId }: { batchId: string }) {
  const { t } = useUI()
  const [brief, setBrief] = useState<Brief | null>(null), [error, setError] = useState(''), [needsReview, setNeedsReview] = useState(false), [revision, setRevision] = useState(0)
  const [exporting, setExporting] = useState(false), [exportError, setExportError] = useState('')
  useEffect(() => {
    const controller = new AbortController()
    setBrief(null); setError(''); setNeedsReview(false)
    void api<Brief>(`/conclusions/batches/${batchId}`, { signal: controller.signal }).then(setBrief).catch(e => {
      if (controller.signal.aborted) return
      const detail = e instanceof Error ? e.message : String(e)
      if (/Complete the review/.test(detail)) setNeedsReview(true); else setError(describeError(e, t))
    })
    return () => controller.abort()
  }, [batchId, revision])
  async function exportReport() {
    // Generated from this same brief, so the document cannot say anything this page does not.
    setExportError(''); setExporting(true)
    try {
      const file = await api<{ filename: string; base64: string }>(`/conclusions/batches/${batchId}/report`)
      const bytes = Uint8Array.from(atob(file.base64), c => c.charCodeAt(0))
      const link = document.createElement('a')
      link.href = URL.createObjectURL(new Blob([bytes], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' }))
      link.download = file.filename
      link.click()
      URL.revokeObjectURL(link.href)
    } catch (e) { setExportError(describeError(e, t)) } finally { setExporting(false) }
  }
  if (needsReview) return <div className="bf-empty"><strong>{t('briefNeedsReview')}</strong>{t('briefNeedsReviewHelp')}</div>
  if (error) return <div><p role="alert" className="bf-error">{error}</p><button onClick={() => setRevision(n => n + 1)}>{t('refresh')}</button></div>
  if (!brief) return <p role="status" className="bf-loading">{t('loading')}</p>
  const grades = ['G1', 'G2', 'G3', 'G4'].map(g => `${g} ${brief.grade_summary[g] ?? 0}`).join(' · ')
  return <section className="bf-brief" aria-label={t('monthlyBrief')}>
    <div className="bf-card-head"><h3>{t('monthlyBrief')} · {brief.period}</h3><Chip status={brief.report_status} />
      <button data-tour-id="brief-export" disabled={brief.stale || exporting} onClick={() => void exportReport()}>{t(exporting ? 'busy' : 'exportReport')}</button></div>
    {exportError && <p role="alert" className="bf-error">{exportError}</p>}
    {brief.stale && <div className="bf-callout" data-tone="warn"><p>{t('briefStale')}</p></div>}
    {brief.missing_departments.length > 0 && <div className="bf-callout" data-tone="warn"><h3>{t('partial')}</h3><p>{t('briefMissing')}：{brief.missing_departments.map(d => t(d)).join('、')}</p></div>}
    <p className="bf-brief-headline" role="status">
      <strong>{brief.headline.attention}</strong> {t('briefAttention')} · <strong>{brief.headline.ok}</strong> {t('briefOk')} · <strong>{brief.headline.open_items}</strong> {t('briefOpenItems')}
    </p>
    <p className="bf-hint">{t('evidenceGrades')}：{grades}{brief.grade_summary.missing ? ` · ${t('gradeMissing')} ${brief.grade_summary.missing}` : ''} · {t('gradeLegend')}</p>

    <h4>{t('briefKeyMetrics')}</h4>
    <dl className="bf-brief-metrics">{brief.key_metrics.map(m => <div key={m.metric}>
      <dt>{m.title}</dt>
      <dd><b>{number(m.value, m.unit)}</b> <Chip status={m.status} /> <GradeMark grade={m.grade} /> <ChangeMark change={m.change} unit={m.unit} /><small>{m.formula} · {t(m.owner)}</small></dd>
    </div>)}</dl>

    <h4>{t('briefAttentionItems')}</h4>
    {!brief.attention.length && <p className="bf-hint">{t('briefNoAttention')}</p>}
    <ol className="bf-brief-attention">{brief.attention.map(a => <li key={a.check_id}>
      <div className="bf-check"><span className="bf-check-title">{a.title}</span><b>{number(a.value, a.unit)}</b><GradeMark grade={a.grade} /></div>
      <p className="bf-hint">{t(a.attention_when === 'above' ? 'briefAbove' : 'briefBelow')} {number(a.threshold, a.unit)} · {t('briefOwner')} {a.decision_owner}</p>
      <p>{t('briefAction')}：{a.action} <GradeMark grade={a.advice_grade} /></p>
      <p className="bf-hint">{a.explanation}</p>
    </li>)}</ol>

    <h4>{t('periodComparison')}</h4>
    {!brief.comparison || brief.comparison.status !== 'compared'
      ? <p className="bf-hint" role="status">{t(brief.comparison?.status === 'no_base' ? 'comparisonNoBase'
        : brief.comparison?.status === 'declaration_changed' ? 'comparisonChanged'
        : brief.comparison?.status === 'unavailable' ? 'comparisonUnavailable' : 'comparisonUnusable')}
        {brief.comparison?.base_period ? ` · ${t('comparisonBase')} ${brief.comparison.base_period}` : ''}
        {brief.comparison?.reason ? ` · ${brief.comparison.reason}` : ''}</p>
      : <>
        <p className="bf-hint">{t('comparisonBase')} {brief.comparison.base_period}</p>
        {brief.comparison.breaches.length > 0 && <div className="bf-callout" data-tone="warn">
          <h3>{t('comparisonBreaches')} · {brief.comparison.breaches.length}</h3>
          <ul>{brief.comparison.breaches.map((b, i) => <li key={i}>{b.key?.join(' · ')} · {b.field} · {number(b.current ?? 0, '')} ← {number(b.base ?? 0, '')} <ChangeMark change={b} unit="" /></li>)}</ul>
        </div>}
        <details><summary>{t('comparisonTotals')} · {brief.comparison.totals.length}</summary>
          <div className="bf-scroll"><table><thead><tr><th>{t('comparisonField')}</th><th>{brief.period}</th><th>{brief.comparison.base_period}</th><th>Δ</th><th>{t('comparisonTotals')}</th></tr></thead>
            <tbody>{brief.comparison.totals.map(row => <tr key={row.field}><td>{row.field}</td><td data-numeric="true">{number(row.current, '')}</td><td data-numeric="true">{number(row.base, '')}</td>
              <td data-numeric="true">{number(row.absolute, '')}{row.relative === null ? '' : `（${(row.relative * 100).toFixed(1)}%）`}</td>
              <td data-numeric="true">{number(row.new_entities, '')} / {number(row.discontinued, '')} / {number(row.continuing, '')}</td></tr>)}</tbody></table></div>
        </details>
      </>}

    <h4>{t('briefOpenItems')}</h4>
    <ul className="bf-brief-open">
      <li>{t('masterOpenQuestions')}：{brief.open_items.master_issues} <button onClick={() => navigate({ batch: batchId, view: 'integration' })}>{t('integrationMaster')}</button></li>
      <li>{t('quarantine')}：{brief.open_items.quarantined_rows}</li>
      <li>{t('pendingColumnQuestions')}：{brief.open_items.column_questions}</li>
    </ul>
    <p className="bf-hint">{t('briefCompleteness')}：{brief.completeness.complete_rows} / {brief.completeness.master_rows} {t('masterCompleteRows')} · {t('integrationAssumptions')} {brief.completeness.assumptions}</p>
    <details><summary>{t('briefDecisionAndLimits')}</summary><p>{brief.manager_decision}</p><ul>{brief.limitations.map((l, i) => <li key={i}>{l}</li>)}</ul></details>
    <MetricCharts batchId={batchId} />
  </section>
}
