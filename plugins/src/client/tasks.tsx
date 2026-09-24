import { useEffect, useState } from 'react'
import { CloseChecklist, OpenItemInbox } from './checklist.tsx'
import { WorkflowProgress } from './workflow-progress.tsx'
import { api, describeError, navigate, startReview, useUI, type Summary } from './ui.ts'
import { Explain } from './explain.tsx'
import { useGuestMode } from './guest.tsx'
import type { projectAudit } from './audit.ts'

type DemoCase = { case_id: string; title: [string, string]; summary: [string, string] }

function DemoCaseGuide({ caseId, batchId }: { caseId: string; batchId: string }) {
  const { t, language } = useUI()
  const [sample, setSample] = useState<DemoCase | null>(null)
  useEffect(() => {
    const controller = new AbortController()
    setSample(null)
    void api<{ cases: DemoCase[] }>('/batches/demo/cases', { signal: controller.signal })
      .then(value => setSample(value.cases.find(item => item.case_id === caseId) ?? null))
      .catch(() => { if (!controller.signal.aborted) setSample(null) })
    return () => controller.abort()
  }, [caseId])
  if (!sample) return null
  const pick = (pair: [string, string]) => pair[language === 'zh' ? 0 : 1]
  return <div className="bf-callout bf-demo-guide" data-tone="info" role="note">
    <h3>{t('sampleCaseLabel')} · {pick(sample.title)}</h3>
    <p>{pick(sample.summary)}</p>
    <button onClick={() => navigate({ batch: batchId, view: 'data' })}>{t('sampleCaseOpenData')}</button>
  </div>
}

/**
 * 本月任务 — the one page that answers "what is still on me this month" (E14-UC01 + E14-UC05).
 *
 * The close checklist and the open-item inbox were two panels reporting the same facts: the
 * checklist said "the master still has 4 open items", the inbox listed those four. Here they
 * sit side by side and point at each other — focusing a step filters the items to the ones
 * that step is waiting on — so the count is read once and the person is never asked which of
 * two lists to believe.
 */
export function TasksView({ batchId, summary, audit, savedReportStatus, notebookKind, onImport, onRefresh }: {
  batchId: string
  summary: Summary | null
  audit: ReturnType<typeof projectAudit>
  savedReportStatus: string | undefined
  notebookKind: string
  onImport: () => void
  onRefresh: () => void
}) {
  const { t } = useUI()
  const guest = useGuestMode()
  const [focus, setFocus] = useState('')
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  if (!summary) return <p className="bf-hint">{t('studioStartHelp')}</p>
  const reviewReady = summary.status === 'ready'
  return <section className="bf-tasks" aria-label={t('closeChecklist')}>
    <div className="bf-card-head">
      <h3>{t('monthlyTasks')} · {summary.period}</h3>
      <button className="bf-primary" disabled={busy || !reviewReady || (guest.guest && !guest.llm)} onClick={async () => {
        setError(''); setBusy(true)
        try { await startReview(batchId, summary.period); onRefresh() }
        catch (e) { setError(describeError(e, t)) } finally { setBusy(false) }
      }} data-tour-id="review-start">{t(busy ? 'busy' : 'startReview')}</button>
    </div>
    {summary.demo_case && <DemoCaseGuide caseId={summary.demo_case} batchId={batchId} />}
    {!reviewReady && <p className="bf-hint" role="status">{t('reviewNeedsReady')}</p>}
    {reviewReady && guest.guest && !guest.llm && <p className="bf-hint" role="status">{t('guestReviewUnavailable')}</p>}
    <p className="bf-hint">{t('monthlyTasksHelp')}</p>
    <Explain text={t('how_tasks')} />
    {error && <p role="alert" className="bf-error">{error}</p>}

    {/* A batch whose data was corrected afterwards is the one thing that invalidates everything
        below it, so it is stated before the steps rather than somewhere down the page. */}
    {!!summary.superseded_by?.length && <div className="bf-callout" data-tone="warn">
      <h3>{t('superseded')}</h3><p>{t('supersededHint')}</p>
    </div>}

    <div className="bf-tasks-split">
      <CloseChecklist period={summary.period} batchId={batchId} onImport={onImport}
        onFocus={view => setFocus(current => current === view ? '' : view)} focusView={focus} />
      <OpenItemInbox period={summary.period} batchId={batchId} focusView={focus} onClearFocus={() => setFocus('')} />
    </div>

    <details className="bf-tasks-workflow">
      <summary>{t('workflowProgress')}</summary>
      <WorkflowProgress kind={notebookKind} batchId={batchId} summary={summary} audit={audit} savedReportStatus={savedReportStatus} />
    </details>
  </section>
}
