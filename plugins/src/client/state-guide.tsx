import { askCaptain, describeError, diagnoseRequest, navigate, useUI, type Summary } from './ui.ts'
import { useState } from 'react'

/**
 * "Where am I, and what do I click next?" for the Business state tab.
 *
 * One stage out of five (files, clean-up, review, decide, close) is read from the same facts the
 * rest of the tab shows: the batch status, whether this session's review is running, the saved
 * report and a pending approval. The stage names its clicks in order and offers the one button
 * that opens where the work happens. It never acts on anything itself; starting a review or
 * asking the captain stays a person's click on the page that owns it.
 */
export type GuideInput = {
  batch: Summary | null
  running: boolean
  report: { id: string; status: string; attention: number } | null
  approvalWaiting: boolean
}
type Stage = 'approval' | 'empty' | 'configure' | 'settle' | 'review' | 'running' | 'partial' | 'decide' | 'close'
const strip = ['stageFiles', 'stageClean', 'stageReview', 'stageDecide', 'stageClose'] as const
const position: Record<Stage, number> = { approval: -1, empty: 0, configure: 1, settle: 1, review: 2, running: 2, partial: 2, decide: 3, close: 4 }

export function stageOf({ batch, running, report, approvalWaiting }: GuideInput): Stage {
  if (approvalWaiting) return 'approval'
  if (!batch || batch.status === 'empty') return 'empty'
  if (batch.status === 'needs_configuration') return 'configure'
  if (batch.status === 'needs_review') return 'settle'
  if (running) return 'running'
  if (!report) return 'review'
  if (report.status === 'partial') return 'partial'
  return report.attention > 0 ? 'decide' : 'close'
}

export function StateGuide(input: GuideInput) {
  const { t, colon } = useUI()
  const [error, setError] = useState(''), [asked, setAsked] = useState(false)
  const stage = stageOf(input)
  // A waiting approval interrupts the month; the strip still shows where the month is.
  const at = position[stageOf({ ...input, approvalWaiting: false })]
  const batch = input.batch
  const fill = (text: string) => text.replaceAll('{attention}', String(input.report?.attention ?? 0))
  const steps = fill(t(`guide_${stage}_steps`)).split('\n').filter(Boolean)
  const open = (view: string) => batch && navigate({ batch: batch.batch_id, view })
  const action = stage === 'empty' ? <button className="bf-primary" onClick={() => window.dispatchEvent(new Event('bridgeflow:add-sources'))}>{t('addSources')}</button>
    : stage === 'configure' ? <>
      <button className="bf-primary" onClick={() => open('columns')}>{t('guideOpenColumns')}</button>
      <button disabled={asked} onClick={() => { setError(''); void askCaptain(diagnoseRequest(batch!.batch_id, batch!.period)).then(() => setAsked(true)).catch(e => setError(describeError(e, t))) }}>{t('guideAskMatches')}</button>
    </>
    : stage === 'settle' || stage === 'review' || stage === 'close' ? <button className="bf-primary" onClick={() => open('tasks')}>{t('monthlyTasks')}</button>
    : stage === 'partial' ? <button className="bf-primary" onClick={() => batch && navigate({ batch: batch.batch_id, view: 'review', report: input.report!.id })}>{t('guideOpenReport')}</button>
    : stage === 'decide' ? <button className="bf-primary" onClick={() => open('brief')}>{t('monthlyBrief')}</button>
    : null
  return <section className="bf-state-guide" aria-label={t('guideTitle')}>
    <ol className="bf-stage-strip" aria-label={t('guideStages')}>
      {strip.map((key, i) => <li key={key} data-state={i < at ? 'done' : i === at ? 'current' : 'todo'}>{t(key)}</li>)}
    </ol>
    <h3>{t('guideTitle')}{colon}{t(`guide_${stage}_title`)}</h3>
    <ol className="bf-guide-steps">{steps.map((step, i) => <li key={i}>{step}</li>)}</ol>
    <p className="bf-hint">{fill(t(`guide_${stage}_after`))}</p>
    {action && <div className="bf-actions" style={{ margin: '8px 0 0' }}>{action}</div>}
    {asked && <p className="bf-hint" role="status">{t('settleAsked')}</p>}
    {error && <p role="alert" className="bf-error">{error}</p>}
  </section>
}
