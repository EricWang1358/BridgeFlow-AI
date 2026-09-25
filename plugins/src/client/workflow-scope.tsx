import { useEffect, useState } from 'react'
import { api, askCaptain, describeError, formatDateTime, navigate, route, useUI, useDataRevision } from './ui.ts'
import { useGuestMode } from './guest.tsx'

/**
 * Which approved MVP decision from discovery the workflow runs under (discovery → workflow).
 *
 * The page never accepts anything itself: acceptance is the captain's tool behind a person's
 * approval, and the host re-reads the decision every time. This card says which state the
 * link is in and offers the one next step for it.
 */
type Accepted = { project_id: string; decision_id: string; decision_seq: number; scope: string[]; exclusions: string[]; by?: string; accepted_at?: string }
type Waiting = { project_id: string; decision_id: string; decision_seq: number; scope: string[]; candidates: string[] }
export type ScopeState = { accepted: Accepted | null; current: boolean; stale_reasons: string[]; runnable_candidates: string[]; pending: Waiting[] }

export function WorkflowScopeCard({ revision, onChanged }: { revision: number; onChanged: () => void }) {
  const { t, language } = useUI()
  const dataRevision = useDataRevision()
  const guest = useGuestMode()
  const modelOff = guest.guest && !guest.llm
  const [state, setState] = useState<ScopeState | null>(null), [error, setError] = useState(''), [busy, setBusy] = useState(false)
  useEffect(() => {
    const controller = new AbortController()
    void api<ScopeState>('/workflow/scope', { signal: controller.signal }).then(setState)
      .catch(e => { if (!controller.signal.aborted) setError(describeError(e, t)) })
    return () => controller.abort()
  }, [revision, dataRevision])
  async function run(action: () => Promise<unknown>) {
    setBusy(true); setError('')
    try { await action(); onChanged() } catch (e) { setError(describeError(e, t)) } finally { setBusy(false) }
  }
  const acceptRequest = (w: Waiting) => t('requestAcceptScope').replaceAll('{project}', w.project_id)
    .replaceAll('{decision}', w.decision_id).replaceAll('{seq}', String(w.decision_seq))
  if (error) return <p role="alert" className="bf-error">{error}</p>
  if (!state) return null
  const list = (items: string[]) => <ul className="bf-scope-list">{items.map(item => <li key={item}>{item}</li>)}</ul>
  const waiting = state.pending.find(w => w.decision_id !== state.accepted?.decision_id || w.decision_seq !== state.accepted?.decision_seq)
  if (state.accepted && state.current) return <section data-tour-id="workflow-scope" className="bf-callout bf-scope" data-tone="ok" aria-label={t('scopeTitle')}>
    <h3>{t('scopeCurrent')}</h3>
    <p className="bf-hint">{t('scopeDecision')} <b>{state.accepted.project_id} / {state.accepted.decision_id}</b> v{state.accepted.decision_seq}
      {' · '}{t('scopeAcceptedBy')} {state.accepted.by || '—'}{state.accepted.accepted_at ? ` · ${formatDateTime(state.accepted.accepted_at, language)}` : ''}</p>
    {list(state.accepted.scope)}
    {state.accepted.exclusions.length > 0 && <p className="bf-hint">{t('scopeExclusions')}: {state.accepted.exclusions.join('；')}</p>}
  </section>
  if (state.accepted) return <section data-tour-id="workflow-scope" className="bf-callout bf-scope" data-tone="warn" aria-label={t('scopeTitle')}>
    <h3>{t('scopeStale')}</h3>
    <p>{t('scopeStaleHelp')} <span className="bf-hint">({state.stale_reasons.join(', ')})</span></p>
    {waiting && <><button className="bf-primary" disabled={busy || modelOff} onClick={() => void run(() => askCaptain(acceptRequest(waiting)))}>{t('askAcceptScope')}</button>
      {modelOff && <p className="bf-hint" role="status">{t('guestModelActionUnavailable')}</p>}</>}
  </section>
  if (waiting) return <section data-tour-id="workflow-scope" className="bf-callout bf-scope" data-tone="info" aria-label={t('scopeTitle')}>
    <h3>{t('scopeWaiting')}</h3>
    <p className="bf-hint">{t('scopeDecision')} <b>{waiting.project_id} / {waiting.decision_id}</b> v{waiting.decision_seq} · {waiting.candidates.join(', ')}</p>
    {list(waiting.scope)}
    <button className="bf-primary" disabled={busy || modelOff} onClick={() => void run(() => askCaptain(acceptRequest(waiting)))}>{t('askAcceptScope')}</button>
    {modelOff && <p className="bf-hint" role="status">{t('guestModelActionUnavailable')}</p>}
  </section>
  return <section data-tour-id="workflow-scope" className="bf-callout bf-scope" aria-label={t('scopeTitle')}>
    <h3>{t('scopeNone')}</h3>
    <p className="bf-hint">{t('scopeNoneHelp')}</p>
    <button disabled={busy} onClick={() => void run(() => api('/discovery/sample', { method: 'POST' }))}>{t('loadDiscoverySample')}</button>
  </section>
}

type Step = { seq: number; type: string; at: string; by: string; reason: string; detail: string }

/** One record's steps, read from its append-only stream: what, when, who and why. */
export function WorkflowTimeline({ kind, id }: { kind: 'artifact' | 'handoff'; id: string }) {
  const { t, language } = useUI()
  const dataRevision = useDataRevision()
  const [steps, setSteps] = useState<Step[] | null>(null), [error, setError] = useState('')
  useEffect(() => {
    const controller = new AbortController()
    void api<{ steps: Step[] }>(`/workflow/history/${kind}/${id}`, { signal: controller.signal }).then(value => setSteps(value.steps))
      .catch(e => { if (!controller.signal.aborted) setError(describeError(e, t)) })
    return () => controller.abort()
  }, [kind, id, dataRevision])
  if (error) return <p role="alert" className="bf-error">{error}</p>
  if (!steps) return <p className="bf-hint bf-loading">{t('loading')}</p>
  return <ol className="bf-timeline">{steps.map(step => <li key={step.seq}>
    <time>{formatDateTime(step.at, language)}</time>
    <b>{t(`event_${step.type}`) === `event_${step.type}` ? step.type : t(`event_${step.type}`)}</b>
    {step.detail && <span className="bf-hint"> · {step.detail}</span>}
    {step.by && <span className="bf-hint"> · {t('timelineBy')} {step.by}</span>}
    {step.reason && <p className="bf-hint">{step.reason}</p>}
  </li>)}</ol>
}

/** On the discovery side: whether the filling workflow has taken this approved decision on. */
export function DecisionScopeLink({ project, decision, seq }: { project: string; decision: string; seq: number }) {
  const { t } = useUI()
  const dataRevision = useDataRevision()
  const [state, setState] = useState<ScopeState | null>(null)
  useEffect(() => {
    const controller = new AbortController()
    void api<ScopeState>('/workflow/scope', { signal: controller.signal }).then(setState).catch(() => undefined)
    return () => controller.abort()
  }, [project, decision, seq, dataRevision])
  if (!state) return null
  const a = state.accepted
  const same = a?.project_id === project && a.decision_id === decision
  const key = same && a.decision_seq === seq && state.current ? 'linkAccepted' : same ? 'linkOutdated' : 'linkWaiting'
  return <p className="bf-callout" data-tone={key === 'linkAccepted' ? 'ok' : 'info'}>{t(key)}{' '}
    {/* Keep the notebook's batch in the route: dropping it would unbind the open notebook. */}
    <button onClick={() => { const batch = route().batch; navigate({ ...(batch ? { batch } : {}), view: 'handoff' }) }}>{t('openHandoff')}</button></p>
}
