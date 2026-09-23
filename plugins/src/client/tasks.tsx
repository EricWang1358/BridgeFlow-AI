import { useState } from 'react'
import { CloseChecklist, OpenItemInbox } from './checklist.tsx'
import { WorkflowProgress } from './workflow-progress.tsx'
import { describeError, startReview, useUI, type Summary } from './ui.ts'
import { Explain } from './explain.tsx'
import type { projectAudit } from './audit.ts'

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
  const [focus, setFocus] = useState('')
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  if (!summary) return <p className="bf-hint">{t('studioStartHelp')}</p>
  return <section className="bf-tasks" aria-label={t('closeChecklist')}>
    <div className="bf-card-head">
      <h3>{t('monthlyTasks')} · {summary.period}</h3>
      <button className="bf-primary" disabled={busy} onClick={async () => {
        setError(''); setBusy(true)
        try { await startReview(batchId, summary.period); onRefresh() }
        catch (e) { setError(describeError(e, t)) } finally { setBusy(false) }
      }} data-tour-id="review-start">{t(busy ? 'busy' : 'startReview')}</button>
    </div>
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
