import { useEffect, useState } from 'react'
import { api, describeError, navigate, useUI } from './ui.ts'

/**
 * This month's close checklist (E14-UC01).
 *
 * Read-only: every step's state is read from the module that owns it, so the list cannot
 * disagree with the page its button opens. A step whose state could not be read says
 * "unknown" and keeps the month from reading as ready — the page exists so that nobody has
 * to assume.
 */
type Step = { id: string; kind: string; owner_role: string; required: boolean; state: string
  count: number; outstanding: string[]; next_view: string; reason: string }
type Checklist = { period: string; batch_id: string; steps: Step[]; ready_to_close: boolean; refusal: string }

export function CloseChecklist({ period, batchId, onImport }: { period: string; batchId: string; onImport: () => void }) {
  const { t } = useUI()
  const [list, setList] = useState<Checklist | null>(null), [error, setError] = useState('')
  useEffect(() => {
    if (!period) return
    const controller = new AbortController()
    setList(null); setError('')
    void api<Checklist>(`/monthly/checklist?period=${encodeURIComponent(period)}`, { signal: controller.signal })
      .then(setList).catch(e => { if (!controller.signal.aborted) setError(describeError(e, t)) })
    return () => controller.abort()
  }, [period, batchId])
  if (!period) return null
  if (error) return <p role="alert" className="bf-error">{error}</p>
  if (!list) return <p role="status" className="bf-loading">{t('loading')}</p>
  if (list.refusal) return <p className="bf-hint">{list.refusal}</p>
  return <section className="bf-checklist" aria-label={t('closeChecklist')}>
    <h3>{t('closeChecklist')} · {list.period}</h3>
    {list.ready_to_close
      ? <div className="bf-callout" data-tone="ok"><h3>{t('readyToClose')}</h3><p>{t('readyToCloseHint')}</p></div>
      : <p className="bf-hint">{t('checklistHint')}</p>}
    <ol>{list.steps.map(step => <li key={step.id} data-state={step.state}>
      <span className="bf-step-state" data-state={step.state}>{t(`stepState_${step.state}`)}</span>
      <b>{t(`step_${step.id}`)}</b>
      {step.owner_role && <span className="bf-hint"> · {t('stepOwner')} {step.owner_role}</span>}
      {step.state !== 'done' && <>
        {step.outstanding.length > 0 && <div className="bf-hint">{t('stepOutstanding')}：{step.outstanding.map(name => t(name) === name ? name : t(name)).join('、')}</div>}
        {step.reason && <div className="bf-hint">{step.reason}</div>}
        {step.next_view && <button onClick={() => {
          if (step.next_view === 'import') onImport()
          else navigate({ ...(batchId ? { batch: batchId } : {}), view: step.next_view })
        }}>{t(`stepGo_${step.next_view}`)}</button>}
      </>}
    </li>)}</ol>
  </section>
}
