import type { ComponentType } from 'react'
import { notebookPurpose, type WorkflowId } from '../notebook-capabilities.ts'
import type { projectAudit } from './audit.ts'
import { QuotationProgress } from './quotation-progress.tsx'
import { Chip, BatchChip } from './workspace.tsx'
import { useUI, type Summary } from './ui.ts'

type ProgressProps = {
  batchId: string
  summary: Summary | null
  audit: ReturnType<typeof projectAudit>
  savedReportStatus: string | undefined
}

function MonthlyProgress({ batchId, summary, audit, savedReportStatus }: ProgressProps) {
  const { t } = useUI()
  return <section className="bf-state-map" aria-label={t('monthlyProgress')}>
    <section><h3>{t('import')}</h3>{summary ? <BatchChip status={summary.status}/> : <p>{t('emptySourcesHelp')}</p>}</section>
    <section><h3>{t('review')}</h3><Chip status={audit.review?.batch_id === batchId ? String(audit.review.status) : savedReportStatus ?? 'notStarted'}/></section>
    <section><h3>{t('approval')}</h3>{audit.approvals.length ? audit.approvals.map(a => <div key={a.id}><Chip status={a.outcome}/>{a.note && <p>{a.note}</p>}</div>) : <p>{t('noPendingApproval')}</p>}</section>
  </section>
}

const progressViews: Record<WorkflowId, ComponentType<ProgressProps>> = {
  monthly: MonthlyProgress,
  quotation: QuotationProgress,
}

export function WorkflowProgress({ kind, ...props }: ProgressProps & { kind: unknown }) {
  return <>{notebookPurpose(kind).workflows.map(id => {
    const View = progressViews[id]
    return <View key={id} {...props}/>
  })}</>
}
