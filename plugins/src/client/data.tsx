import { useEffect, useState } from 'react'
import { departments, ResupplyForm, TemplateDownload } from './workspace.tsx'
import { api, describeError, navigate, useUI, type Summary } from './ui.ts'

/**
 * 数据 — one timeline for a month's files: take the template, self-check, import, fix (E14).
 *
 * Before this page the same month lived in three places: a dialog for new uploads, a second
 * form inside it for replacing one department, and a studio section for what the master
 * still disagrees about. They are one sequence in real life, so they are one page here, and
 * each department owns a row carrying everything that can happen to its file.
 *
 * Nothing on the right is an action: it states what this batch still has open and hands the
 * reader to the module that settles it.
 */
type Source = { id: string; filename: string; sheet: string; preview_available: boolean; total?: number; sha256?: string }
type Quality = { by_kind: Record<string, number>; total: number }

const STEPS = ['stepTemplate', 'stepSelfCheck', 'stepImport', 'stepFix'] as const

export function DataView({ batchId, summary, sources, onImport, onRefresh }: {
  batchId: string
  summary: Summary | null
  sources: Source[]
  onImport: () => void
  onRefresh: () => void
}) {
  const { t } = useUI()
  const [quality, setQuality] = useState<Quality | null>(null), [error, setError] = useState('')
  useEffect(() => {
    if (!summary?.period) return
    const controller = new AbortController()
    setQuality(null)
    void api<Quality>(`/monthly/inbox?period=${encodeURIComponent(summary.period)}`, { signal: controller.signal })
      .then(setQuality).catch(e => { if (!controller.signal.aborted) setError(describeError(e, t)) })
    return () => controller.abort()
  }, [summary?.period, batchId])
  if (!summary) return <p className="bf-hint">{t('studioStartHelp')}</p>
  const present = new Map(summary.departments.map(d => [d.department, d]))
  const fileOf = new Map(sources.map(s => [s.id, s]))
  const kinds = quality?.by_kind ?? {}
  const masterIssues = Object.entries(kinds).filter(([kind]) => kind.startsWith('master_')).reduce((n, [, v]) => n + v, 0)
  return <section className="bf-data" aria-label={t('dataWorkspace')}>
    <div className="bf-card-head">
      <h3>{t('dataWorkspace')} · {summary.period}</h3>
      <button onClick={onImport}>{t('addSources')}</button>
    </div>
    <p className="bf-hint">{t('dataHelp')}</p>
    {error && <p role="alert" className="bf-error">{error}</p>}

    <ol className="bf-data-steps">
      {STEPS.map((step, index) => <li key={step}><span aria-hidden="true">{index + 1}</span>
        <span><strong>{t(step)}</strong><small>{t(`${step}Hint`)}</small></span></li>)}
    </ol>

    <div className="bf-data-split">
      <div className="bf-data-files">
        {departments.map(name => {
          const row = present.get(name), file = fileOf.get(name)
          return <article key={name} className="bf-data-row" data-state={row ? 'present' : 'missing'}>
            <div className="bf-data-row-head">
              <strong>{t(name)}</strong>
              {row
                ? <span className="bf-hint bf-mono">{file?.filename ?? '—'} · {row.rows} {t('rows')}{row.quarantined ? ` · ${row.quarantined} ${t('quarantine')}` : ''}{row.corrections ? ` · ${row.corrections} ${t('corrections')}` : ''}</span>
                : <span className="bf-hint">{t('departmentMissing')}</span>}
              <span className="bf-chip" data-status={row ? 'ready' : 'partial'}>{t(row ? 'fileSubmitted' : 'notSubmitted')}</span>
              <div className="bf-actions" style={{ marginBottom: 0 }}>
                <TemplateDownload period={summary.period} department={name} />
                {row
                  ? file?.preview_available
                    ? <button onClick={() => navigate({ batch: batchId, view: 'source', source: name })}>{t('sourcePreview')}</button>
                    : null
                  : <button className="bf-primary" onClick={onImport}>{t('upload')}</button>}
              </div>
            </div>
            {row && <ResupplyForm batch={summary} department={name} onDerived={id => { navigate({ batch: id, view: 'data' }); onRefresh() }} />}
          </article>
        })}
      </div>

      <aside className="bf-data-quality">
        <h4>{t('batchQuality')}</h4>
        <ul>
          <li><button onClick={() => navigate({ batch: batchId, view: 'integration' })}>
            <span>{t('item_master_disagreement')}</span><span className="bf-badge" data-open={masterIssues > 0}>{masterIssues}</span></button></li>
          <li><button onClick={() => navigate({ batch: batchId, view: 'quarantine' })}>
            <span>{t('quarantine')}</span><span className="bf-badge" data-open={(kinds.quarantined_row ?? 0) > 0}>{kinds.quarantined_row ?? 0}</span></button></li>
          <li><button onClick={() => navigate({ batch: batchId, view: 'columns' })}>
            <span>{t('pendingColumnQuestions')}</span><span className="bf-badge" data-open={(kinds.column_question ?? 0) > 0}>{kinds.column_question ?? 0}</span></button></li>
          <li><button onClick={() => navigate({ batch: batchId, view: 'integration' })}>
            <span>{t('item_missing_provenance')}</span><span className="bf-badge" data-open={(kinds.missing_provenance ?? 0) > 0}>{kinds.missing_provenance ?? 0}</span></button></li>
        </ul>
        <div className="bf-actions">
          <button className="bf-primary" data-tour-id="master-open" disabled={!summary.master_rows}
            onClick={() => { navigate({ batch: batchId, view: 'integration' }); window.dispatchEvent(new Event('bridgeflow:master-opened')) }}>
            {t('integrationMaster')}</button>
          <button className="bf-quiet" onClick={() => navigate({ batch: batchId, view: 'master' })}>{t('master')}</button>
        </div>
        <p className="bf-hint">{t('batchQualityHint')}</p>
        <p className="bf-hint">{summary.master_rows} {t('masterCompleteRows')} · {t('dictionaryInForce')} <code className="bf-mono">{summary.dictionary}</code></p>
      </aside>
    </div>
  </section>
}
