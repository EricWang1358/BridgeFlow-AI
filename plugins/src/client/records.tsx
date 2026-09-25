import { useEffect, useState } from 'react'
import { AgentRuns, DecisionJournal, EvalReport } from './observability.tsx'
import { api, describeError, formatDateTime, navigate, useUI, type Summary, useGloss, conventionName, useDataRevision } from './ui.ts'
import { Explain } from './explain.tsx'

/**
 * 记录 — who decided what, when, and on what evidence.
 *
 * Read-only by construction: the version chain, the conventions and the dispositions each
 * live in the module that produced them, and this page only reports them side by side. It
 * offers no decision button, because every decision here needs the evidence and the
 * approval that live where it came from.
 */
type Convention = { id: string; text: string; kind: string; state: string; version: number
  source: string; note: string; decided_by: string; at: string; declaration_change: string }
type Disposition = { check_id: string; title?: string; state: string; version: number; note: string; decided_by: string; at: string; closed: boolean }
type Artifact = { report_id: string; period: string; status: string; created_at: number; kind?: string }

export function RecordsView({ batchId, summary, artifacts, language }: {
  batchId: string
  summary: Summary | null
  artifacts: Artifact[]
  language: string
}) {
  const { t, colon, paren } = useUI(), gloss = useGloss()
  const dataRevision = useDataRevision()
  const [conventions, setConventions] = useState<Convention[]>([])
  const [dispositions, setDispositions] = useState<Disposition[]>([]), [dispositionNote, setDispositionNote] = useState('')
  const [error, setError] = useState('')
  useEffect(() => {
    if (!batchId) return
    const controller = new AbortController(), signal = controller.signal
    setConventions([]); setDispositions([]); setDispositionNote(''); setError('')
    void api<{ conventions: Convention[] }>(`/conventions/batches/${batchId}`, { signal })
      .then(value => setConventions(value.conventions ?? []))
      .catch(e => { if (!signal.aborted) setError(describeError(e, t)) })
    // A batch with no saved review has no dispositions yet; that is a state, not an error.
    void api<{ dispositions: Disposition[]; refusal?: string }>(`/reviews/${batchId}/dispositions`, { signal })
      .then(value => { setDispositions(value.dispositions ?? []); setDispositionNote(value.refusal ?? '') })
      .catch(() => { if (!signal.aborted) setDispositionNote(t('recordsNoReview')) })
    return () => controller.abort()
  }, [batchId, dataRevision])
  if (batchId && !summary) return <p role="status" className="bf-loading">{t('loading')}</p>
  return <section className="bf-records" aria-label={t('records')}>
    <div className="bf-card-head"><h3>{t('records')}{summary ? ` · ${summary.period}` : ''}</h3></div>
    <p className="bf-hint">{t('recordsHelp')}</p>
    <Explain text={t('how_records')} />
    {error && <p role="alert" className="bf-error">{error}</p>}

    {summary ? <>
    <h4>{t('recordsLineage')}</h4>
    <ul className="bf-records-list">
      <li><span>{t('batchId')}</span><code className="bf-mono">{batchId}</code></li>
      {summary.derived_from && <li><span>{t('derivedFrom')}</span>
        <button onClick={() => navigate({ batch: summary.derived_from!, view: 'records' })}><code className="bf-mono">{summary.derived_from}</code></button></li>}
      {summary.superseded_by?.map(id => <li key={id}><span>{t('superseded')}</span>
        <button onClick={() => navigate({ batch: id, view: 'records' })}><code className="bf-mono">{id}</code></button></li>)}
      <li><span>{t('dictionaryFile')}</span><code className="bf-mono">{summary.dictionary}</code></li>
    </ul>

    <h4>{t('integrationAssumptions')}</h4>
    {!conventions.length && <p className="bf-hint">{t('recordsNoConventions')}</p>}
    <ul className="bf-records-list">
      {conventions.map(item => <li key={item.id}>
        <span><strong>{item.id.startsWith('rollup.') ? conventionName(item.id, t) : gloss.label(item.id)}</strong> <span className="bf-convention" data-state={item.state}>{t(`conventionState_${item.state}`)}</span></span>
        <span className="bf-hint">{item.state === 'unconfirmed'
          ? t(`conventionKind_${item.kind}`)
          : `${t('conventionSource')}${colon}${item.source}${paren(`${item.decided_by} · v${item.version}`)}`}</span>
      </li>)}
    </ul>

    <h4>{t('risk_dispositions')}</h4>
    {dispositionNote && <p className="bf-hint">{dispositionNote}</p>}
    <ul className="bf-records-list">
      {dispositions.map(item => <li key={item.check_id}>
        <span><strong>{item.title ? gloss.text(item.title) : item.check_id}</strong></span>
        <span className="bf-hint">{item.state}{item.decided_by ? ` · ${item.decided_by}` : ''}{item.note ? ` · ${item.note}` : ''}</span>
      </li>)}
    </ul>

    <h4>{t('artifacts')}</h4>
    <ul className="bf-records-list">
      {artifacts.map(item => <li key={`${item.kind}-${item.report_id}`}>
        <button onClick={() => navigate({ batch: batchId, view: item.kind === 'brief' ? 'brief' : 'artifact', report: item.report_id })}>
          {item.period} · {t(item.kind === 'brief' ? 'monthlyBrief' : 'review')}</button>
        <span className="bf-hint">{formatDateTime(item.created_at * 1000, language)} · {t(item.status)}</span>
      </li>)}
      {!artifacts.length && <li><span className="bf-hint">{t('emptyArtifacts')}</span></li>}
    </ul>

    <p className="bf-hint">{t('recordsReadOnly')}</p>
    </> : <p className="bf-callout" role="note">{t('recordsNoBatch')}</p>}

    <AgentRuns batchId={batchId} />
    <DecisionJournal batchId={batchId} />
    <EvalReport />
  </section>
}
