import { useEffect, useState } from 'react'
import { api, describeError, navigate, useUI, useGloss } from './ui.ts'

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

type Item = { id: string; kind: string; source: string; batch_id: string; period: string
  departments: string[]; subject: string; detail: string; next_view: string }
type Inbox = { total: number; items: Item[]; by_kind: Record<string, number>; by_department: Record<string, number>; unreadable: string[] }

/**
 * What is still waiting on someone (E14-UC05).
 *
 * Every row ends in one button: open the module that settles it. There is deliberately no
 * approve or reject here — the evidence and the approval live where the item came from.
 */
export function OpenItemInbox({ period, batchId, focusSource = '', onClearFocus }:
  { period: string; batchId: string; focusSource?: string; onClearFocus?: () => void }) {
  const { t, colon } = useUI(), gloss = useGloss()
  const [inbox, setInbox] = useState<Inbox | null>(null), [error, setError] = useState(''), [department, setDepartment] = useState('')
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    if (!period) return
    const controller = new AbortController()
    setInbox(null); setError('')
    const query = `period=${encodeURIComponent(period)}&batch_id=${encodeURIComponent(batchId)}${department ? `&department=${encodeURIComponent(department)}` : ''}`
    void api<Inbox>(`/monthly/inbox?${query}`, { signal: controller.signal })
      .then(setInbox).catch(e => { if (!controller.signal.aborted) setError(describeError(e, t)) })
    return () => controller.abort()
  }, [period, batchId, department, retry])
  if (!period) return null
  if (error) return <section className="bf-inbox" aria-label={t('openItems')}>
    <h3>{t('openItems')}</h3>
    <p role="alert" className="bf-error">{t('inboxUnavailable')}</p>
    <p className="bf-hint">{error}</p>
    <button onClick={() => setRetry(value => value + 1)}>{t('refresh')}</button>
  </section>
  if (!inbox) return <p role="status" className="bf-loading">{t('loading')}</p>
  // Only steps backed by an inbox source offer a focus action. A shared destination such as
  // "state" can cover unrelated facts and is not a safe filter key.
  const shown = focusSource ? inbox.items.filter(item => item.source === focusSource) : inbox.items
  const filtered = Boolean(focusSource || department)
  const clearFilters = () => { setDepartment(''); onClearFocus?.() }
  return <section className="bf-inbox" aria-label={t('openItems')}>
    <h3>{t('openItems')} <span className="bf-badge">{shown.length}</span></h3>
    {filtered && <p className="bf-hint" role="status">{t('inboxShowingOf').replace('{shown}', String(shown.length)).replace('{total}', String(inbox.total))} <button onClick={clearFilters}>{t('inboxClearFocus')}</button></p>}
    {focusSource
      ? <p className="bf-hint" role="status">{t('inboxFocused')}</p>
      : <p className="bf-hint">{t('openItemsHint')}</p>}
    <label>{t('inboxDepartmentFilter')} <select value={department} onChange={e => setDepartment(e.target.value)}>
      <option value="">{t('allDepartments')}</option>
      {Object.keys(inbox.by_department).map(name => <option key={name} value={name}>{t(name)} · {inbox.by_department[name]}</option>)}
    </select></label>
    {inbox.unreadable.map(reason => <p key={reason} className="bf-hint">{t('inboxUnreadable')}{colon}{reason}</p>)}
    {!shown.length && <p className="bf-hint">{filtered && inbox.total > 0 ? t('inboxNoMatches') : t('inboxEmpty')}</p>}
    <ul>{shown.map(item => <li key={item.id}>
      <b>{t(`item_${item.kind}`) === `item_${item.kind}` ? item.kind : t(`item_${item.kind}`)}</b>
      {item.subject && <span className="bf-mono"> · {gloss.label(item.subject)}</span>}
      <span className="bf-hint"> · {item.departments.map(d => t(d)).join('、')}</span>
      {item.detail && <div className="bf-hint">{gloss.message(item.detail)}</div>}
      <button onClick={() => navigate({ ...(item.batch_id ? { batch: item.batch_id } : {}), view: item.next_view })}>{t('openToSettle')}</button>
    </li>)}</ul>
  </section>
}

export function CloseChecklist({ period, batchId, onImport, onFocus, focusSource = '' }:
  { period: string; batchId: string; onImport: () => void; onFocus?: (source: string) => void; focusSource?: string }) {
  const { t, colon, list: joined } = useUI(), gloss = useGloss()
  const [list, setList] = useState<Checklist | null>(null), [error, setError] = useState('')
  useEffect(() => {
    if (!period) return
    const controller = new AbortController()
    setList(null); setError('')
    void api<Checklist>(`/monthly/checklist?period=${encodeURIComponent(period)}&batch_id=${encodeURIComponent(batchId)}`, { signal: controller.signal })
      .then(setList).catch(e => { if (!controller.signal.aborted) setError(describeError(e, t)) })
    return () => controller.abort()
  }, [period, batchId])
  if (!period) return null
  if (error) return <p role="alert" className="bf-error">{error}</p>
  if (!list) return <p role="status" className="bf-loading">{t('loading')}</p>
  if (list.refusal) return <p className="bf-hint">{list.refusal}</p>
  const inboxSource = (kind: string) => kind === 'quarantine_cleared' ? 'quarantine' : kind === 'master_open_items' ? 'integration' : ''
  return <section className="bf-checklist" aria-label={t('closeChecklist')}>
    <h3>{t('closeChecklist')} · {list.period}</h3>
    {list.ready_to_close
      ? <div className="bf-callout" data-tone="ok"><h3>{t('readyToClose')}</h3><p>{t('readyToCloseHint')}</p></div>
      : <p className="bf-hint">{t('checklistHint')}</p>}
    <ol>{list.steps.map(step => <li key={step.id} data-state={step.state} data-focused={!!inboxSource(step.kind) && inboxSource(step.kind) === focusSource}>
      <span className="bf-step-state" data-state={step.state}>{t(`stepState_${step.state}`)}</span>
      <b>{t(`step_${step.id}`)}</b>
      {step.owner_role && <span className="bf-hint bf-step-owner">{t('stepOwner')}{colon}{gloss.text(step.owner_role)}</span>}
      {step.state !== 'done' && <>
        {step.outstanding.length > 0 && <div className="bf-hint">{t('stepOutstanding')}{colon}{joined(step.outstanding.map((name: string) => name.replace(/^([a-z_]+)(×\d+)?$/, (whole, kind: string, count = '') => t(`issue_${kind}`) === `issue_${kind}` ? whole : `${t(`issue_${kind}`)}${count}`)))}</div>}
        {step.reason && <div className="bf-hint">{gloss.message(step.reason)}</div>}
        <div className="bf-actions" style={{ marginBottom: 0 }}>
          {step.count > 0 && inboxSource(step.kind) && onFocus && <button onClick={() => onFocus(inboxSource(step.kind))}>{t('stepShowItems')}</button>}
          {step.next_view && <button onClick={() => {
            if (step.next_view === 'import') onImport()
            else navigate({ ...(batchId ? { batch: batchId } : {}), view: step.next_view })
          }}>{t(`stepGo_${step.next_view}`)}</button>}
        </div>
      </>}
    </li>)}</ol>
  </section>
}
