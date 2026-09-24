import { notebookPurpose, type WorkflowId } from '../notebook-capabilities.ts'
import type { ComponentType } from 'react'
import { useEffect, useMemo, useState, useSyncExternalStore } from 'react'
import type { Context } from '@deepseek-ai/cordis'
import type { ISessions, SessionEventSource, SessionEventWindow } from '@deepseek-ai/dsh-api-session-controller/client'
import type { ConvViewProps } from '@deepseek-ai/dsh-client-ui-conversation/client'
import { api, claimActor, formatTime, labelText, navigate, route, useUI, type Summary, describeError } from './ui.ts'
import { QuotationProgress } from './quotation-progress.tsx'
import { Notebook } from './notebook.tsx'
import { BusinessReview, type Review } from './review.tsx'
import { Chip, BatchChip, type Limits } from './workspace.tsx'
import { NextStep } from './next-step.tsx'

type Injected = { source: SessionEventSource; loadOlder: () => Promise<void> }
import { projectAudit, selectReview, type AuditEvent } from './audit.ts'
function MonthlyState({ source, loadOlder, openView }: ConvViewProps & Injected) {
  const { t, language } = useUI()
  const snapshot = useSyncExternalStore<SessionEventWindow>(fn => source.subscribe(fn), () => source.getSnapshot())
  const audit = useMemo(() => projectAudit(snapshot.entries.filter(e => e.type === 'event').map(e => e.event) as AuditEvent[]), [snapshot])
  const eventBatch = String(audit.review?.batch_id ?? '')
  const [chosen, setChosen] = useState(() => route().view === 'state' ? route().batch ?? '' : '')
  const [input, setInput] = useState(chosen), [batch, setBatch] = useState<Summary | null>(null)
  const [report, setReport] = useState<Review | null>(null), [error, setError] = useState('')
  const [node, setNode] = useState(''), [revision, setRevision] = useState(0), [limits, setLimits] = useState<Limits | null>(null)
  const batchId = chosen || eventBatch
  const selected = selectReview(audit, batchId)
  const { reportId, waiting, runId } = selected
  useEffect(() => {
    const readRoute = () => {
      const value = route()
      if (value.view === 'state') { setChosen(value.batch ?? ''); setInput(value.batch ?? ''); setNode('') }
    }
    readRoute(); window.addEventListener('hashchange', readRoute)
    return () => window.removeEventListener('hashchange', readRoute)
  }, [source])
  useEffect(() => { const abort = new AbortController(); void api<Limits>('/config', { signal: abort.signal }).then(setLimits).catch(e => { if (!abort.signal.aborted) setError(describeError(e, t)) }); return () => abort.abort() }, [])
  useEffect(() => {
    setBatch(null); setReport(null); setError('')
    if (!/^[a-f0-9]{32}$/.test(batchId)) return
    const abort = new AbortController()
    void api<Summary>(`/batches/${batchId}`, { signal: abort.signal }).then(setBatch).catch(e => { if (!abort.signal.aborted) setError(describeError(e, t)) })
    if (!waiting) void api<Review>(`/batches/${batchId}/review${reportId ? `?report_id=${reportId}` : ''}`, { signal: abort.signal }).then(setReport).catch(e => { if (!abort.signal.aborted && !String(e).includes('no saved review')) setError(describeError(e, t)) })
    return () => abort.abort()
  }, [batchId, reportId, waiting, runId, revision])
  const approvalCounts = Object.fromEntries(['running', 'allowed-once', 'rejected', 'cancelled'].map(key => [key, audit.approvals.filter(a => a.outcome === key).length]))
  const currentApproval = audit.approvals.find(a => a.outcome === 'running')?.outcome ?? audit.approvals.at(-1)?.outcome
  const groups = [
    { title: t('import'), items: ['needs_configuration', 'needs_review', 'ready', 'empty'] },
    { title: t('captainFlow'), items: ['dispatching', 'validated', 'partial'] },
    { title: t('review'), items: ['attention', 'ok'] },
    { title: 'confirm_mapping', items: ['running', 'allowed-once', 'rejected', 'cancelled'] },
  ]
  const count = (id: string) => id === 'validated' ? `${report?.roles.filter(r => r.status === 'validated').length ?? 0}/4` : ['attention', 'ok'].includes(id) ? report?.roles.flatMap(r => r.checks).filter(c => c.expected_status === id).length ?? 0 : approvalCounts[id]
  const current = (id: string) => batch?.status === id || report?.status === id || id === 'dispatching' && audit.review?.status === id && batchId === eventBatch || ['attention', 'ok'].includes(id) && !!count(id) || currentApproval === id
  const isApproval = groups[3]!.items.includes(node)
  return <Notebook title={t('state')} description={t('stateHelp')}
    sources={<>
    <form className="bf-actions" onSubmit={e => { e.preventDefault(); setChosen(input); navigate({ batch: input, view: 'state' }) }}>
      <label>{t('batchId')} <input value={input} placeholder={eventBatch || t('batchId')} onChange={e => setInput(e.target.value)} /></label>
      <button disabled={!/^[a-f0-9]{32}$/.test(input)}>{t('open')}</button>
      <button type="button" onClick={() => setRevision(n => n + 1)}>{t('refresh')}</button>
      <button type="button" onClick={() => navigate({ view: 'state' })}>{t('followSession')}</button>
    </form>
    {error && <p role="alert" className="bf-error">{error}</p>}
    <p className="bf-band">{batch
      ? <><span className="bf-period">{batch.period}</span> <BatchChip status={batch.status} /> <span className="bf-hint">{batch.master_rows} {t('rows')} · <code className="bf-mono">{batch.batch_id}</code></span></>
      : <span className="bf-hint">{t('unknown')}</span>}</p>
    {batch && <NextStep batch={batch} />}
    <nav><button disabled={!batch} onClick={() => navigate({ batch: batchId, view: node === 'needs_review' ? 'mappings' : node === 'needs_configuration' ? 'corrections' : 'master' })}>{t('batchTables')} ↗</button>
      <button onClick={() => openView('trajectory', '')}>{t('inspect')} ↗</button>
      {report && <button onClick={() => navigate({ batch: batchId, view: 'review', report: report.report_id })}>{t('review')} ↗</button>}</nav>
    </>}
    studio={<>
    <p className="bf-hint">{t('sessionApprovals')}</p>
    <div className="bf-state-map">{groups.map(group => <section key={group.title}><h3>{group.title}</h3>{group.items.map(id => <button key={id} data-current={current(id)} aria-pressed={node === id} onClick={() => setNode(id)}>{id === 'ready' ? <BatchChip status={id} /> : <Chip status={id} />} {count(id) !== undefined && <span className="bf-badge">{count(id)}</span>}</button>)}</section>)}</div>
    <p className="bf-hint">{t('approval')} · {t('timeout')}: {limits ? limits.decisionTimeoutMs / 1000 : '—'} {t('seconds')}</p>
    <p className="bf-hint">{t('mappingHelp')} {t('quarantineHelp')}</p>
    <details><summary>{t('batchAudit')} · {selected.calls.length} Spawn · {t('dispatchCount')}</summary><p>{t('loadedWindow')}</p><ul>{selected.calls.map((e, i) => <li key={i}>{String(e.data.callId)} · {formatTime(e.time, language)}</li>)}</ul>{snapshot.hasMore && <button onClick={() => void loadOlder().catch(e => setError(describeError(e, t)))}>{t('loadOlder')}</button>}</details>
    </>}>
    {isApproval ? <section aria-label={t('approval')}><h3>{t('approval')}</h3>{audit.approvals.filter(a => a.outcome === node).map(a => <article className="bf-card" key={a.id}><Chip status={a.outcome} /><p>{a.id}</p><p>{a.note}</p><small>{a.call}</small></article>)}{!approvalCounts[node] && <p>{t('unknown')}</p>}</section>
      : report && !['needs_configuration', 'needs_review', 'ready', 'empty'].includes(node) ? <BusinessReview report={{ ...report, roles: ['attention', 'ok'].includes(node) ? report.roles.map(r => ({ ...r, checks: r.checks.filter(c => c.expected_status === node) })) : report.roles }} /> : <p>{batch?.refusal || (waiting ? t('waitingReview') : report ? t('batchHint') : batch ? t('noReport') : t('batchHint'))}</p>}
  </Notebook>
}
const stateViews: Record<WorkflowId, ComponentType<ConvViewProps & Injected>> = {
  monthly: MonthlyState,
  quotation: QuotationProgress,
}
const subscribeRoute = (changed: () => void) => {
  window.addEventListener('hashchange', changed)
  return () => window.removeEventListener('hashchange', changed)
}

function BusinessState(props: ConvViewProps & Injected) {
  const { t } = useUI()
  const kind = useSyncExternalStore(subscribeRoute, () => route().kind)
  return <section className="bf-state bf-business-state" aria-label={t('state')}>
    {notebookPurpose(kind).workflows.map(id => {
      const View = stateViews[id]
      return <View key={id} {...props}/>
    })}
  </section>
}

export function mountState(ctx: Context) {
  const sessions = ctx.sessions as unknown as ISessions
  ctx.slots.inject('conversation.view', () => ctx.slots.register({
    name: 'conversation.view', id: 'bridgeflow-state', order: 20,
    label: () => labelText('state'),
    inject: sessionId => {
      const binding = sessions.binding(sessionId)
      if (!binding) throw new Error('Native session binding unavailable')
      // Opening a session's view is the moment this browser starts driving it, and the
      // only place the client holds both the session id and its portal token (#231).
      void claimActor(sessionId)
      return { source: binding.eventSource, loadOlder: () => binding.session.loadOlder() }
    },
  }, BusinessState))
}
