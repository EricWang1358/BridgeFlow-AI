import { useEffect, useState } from 'react'
import { api, describeError, useUI } from './ui.ts'

/**
 * What the system decided, and how it scores against its own claims.
 *
 * Two readings of the same product. The journal is what happened: every request, its
 * outcome, how long it took, and — when it refused — the sentence it refused with, in its own
 * words. The report is what should happen: the acceptance suite over three held-out
 * industries plus the adversarial half, generated rather than written.
 *
 * The refusals are deliberately the loudest thing on the page. A system whose defining
 * behaviour is "say no when the evidence is missing" should be able to show how often it did,
 * and for what — otherwise that claim is only a sentence in a document.
 */
type Entry = { trace: string; at: string; surface: string; method: string; status: number
  outcome: string; ms: number; actor: string; reason: string; facts: Record<string, unknown> }
type Journal = { day: string; total: number; by_outcome: Record<string, number>; median_ms: number
  slowest_ms: number; refusal_reasons: { reason: string; count: number }[]; entries: Entry[]; days: string[] }
type Check = { industry: string; name: string; passed: boolean; detail: string; owner: string; track: string }
type Report = { generated_at: string; passed?: number; total?: number
  tracks: Record<string, { passed: number; total: number }>; checks: Check[]; refusal?: string; age_hours?: number | null }

const OUTCOMES = ['', 'refused', 'wrote', 'served'] as const

export function DecisionJournal({ batchId }: { batchId: string }) {
  const { t } = useUI()
  const [journal, setJournal] = useState<Journal | null>(null), [error, setError] = useState('')
  const [outcome, setOutcome] = useState<string>(''), [mine, setMine] = useState(true), [revision, setRevision] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    setJournal(null); setError('')
    const query = [outcome && `outcome=${outcome}`, mine && batchId && `batch_id=${batchId}`].filter(Boolean).join('&')
    void api<Journal>(`/journal${query ? `?${query}` : ''}`, { signal: controller.signal })
      .then(setJournal).catch(e => { if (!controller.signal.aborted) setError(describeError(e, t)) })
    return () => controller.abort()
  }, [outcome, mine, batchId, revision])
  if (error) return <p role="alert" className="bf-error">{error}</p>
  if (!journal) return <p role="status" className="bf-loading">{t('loading')}</p>
  return <section className="bf-journal" aria-label={t('decisionJournal')}>
    <div className="bf-card-head">
      <h4>{t('decisionJournal')} · {journal.day}</h4>
      <button onClick={() => setRevision(n => n + 1)}>{t('refresh')}</button>
    </div>
    <p className="bf-hint">{t('decisionJournalHelp')}</p>

    <dl className="bf-facts bf-journal-summary">
      <dt>{t('journalDecisions')}</dt><dd>{journal.total}</dd>
      <dt>{t('journalRefused')}</dt><dd>{journal.by_outcome.refused ?? 0}</dd>
      <dt>{t('journalWrote')}</dt><dd>{journal.by_outcome.wrote ?? 0}</dd>
      <dt>{t('journalLatency')}</dt><dd>{journal.median_ms} / {journal.slowest_ms} ms</dd>
    </dl>

    {journal.refusal_reasons.length > 0 && <div className="bf-callout" data-tone="info">
      <h3>{t('journalTopRefusals')}</h3>
      <ol className="bf-journal-reasons">{journal.refusal_reasons.map(item => <li key={item.reason}>
        <span>{item.reason}</span><span className="bf-badge">{item.count}</span>
      </li>)}</ol>
    </div>}

    <div className="bf-actions">
      {OUTCOMES.map(value => <button key={value || 'all'} aria-pressed={outcome === value}
        onClick={() => setOutcome(value)}>{t(value ? `journal_${value}` : 'journalAll')}</button>)}
      <button aria-pressed={mine} onClick={() => setMine(!mine)}>{t('journalThisBatch')}</button>
    </div>

    {!journal.entries.length && <p className="bf-hint">{t('journalEmpty')}</p>}
    <ol className="bf-journal-list">{journal.entries.map(item => <li key={item.trace + item.at} data-outcome={item.outcome}>
      <span className="bf-journal-time">{item.at.slice(11, 19)}</span>
      <span className="bf-journal-outcome" data-outcome={item.outcome}>{t(`journal_${item.outcome}`)}</span>
      <span className="bf-journal-surface bf-mono">{item.method} {item.surface}</span>
      <span className="bf-journal-ms">{item.ms} ms</span>
      {item.reason && <span className="bf-journal-reason">{item.reason}</span>}
      <span className="bf-journal-trace bf-mono" title={t('journalTrace')}>{item.trace}</span>
    </li>)}</ol>
  </section>
}

export function EvalReport() {
  const { t } = useUI()
  const [report, setReport] = useState<Report | null>(null), [error, setError] = useState('')
  useEffect(() => {
    const controller = new AbortController()
    void api<Report>('/eval/report', { signal: controller.signal })
      .then(setReport).catch(e => { if (!controller.signal.aborted) setError(describeError(e, t)) })
    return () => controller.abort()
  }, [])
  if (error) return <p role="alert" className="bf-error">{error}</p>
  if (!report) return <p role="status" className="bf-loading">{t('loading')}</p>
  if (report.refusal) return <section className="bf-eval" aria-label={t('evalReport')}>
    <h4>{t('evalReport')}</h4><p className="bf-hint">{report.refusal}</p>
  </section>
  const failed = report.checks.filter(c => !c.passed)
  return <section className="bf-eval" aria-label={t('evalReport')}>
    <h4>{t('evalReport')}</h4>
    <p className="bf-hint">{t('evalReportHelp')}
      {report.age_hours !== null && report.age_hours !== undefined
        ? ` · ${t('evalGenerated')} ${report.age_hours} h`
        : ''}</p>
    <dl className="bf-facts">
      {Object.entries(report.tracks).map(([track, counts]) => <div key={track} style={{ display: 'contents' }}>
        <dt>{t(`evalTrack_${track}`)}</dt><dd>{counts.passed} / {counts.total}</dd>
      </div>)}
    </dl>
    {/* A red row names the issue that owns it: that is what stops a failing expectation
        being deleted so the table turns green. */}
    {failed.length > 0
      ? <ul className="bf-records-list">{failed.map(check => <li key={`${check.industry}-${check.name}`}>
        <span><strong>{check.industry}</strong> · {check.name}</span>
        <span className="bf-hint">{check.detail}{check.owner ? ` · ${check.owner}` : ''}</span>
      </li>)}</ul>
      : <p className="bf-hint">{t('evalAllGreen')}</p>}
  </section>
}
