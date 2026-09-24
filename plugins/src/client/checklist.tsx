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

type Item = { id: string; kind: string; source: string; batch_id: string; period: string
  departments: string[]; subject: string; detail: string; next_view: string }
type Inbox = { total: number; items: Item[]; by_kind: Record<string, number>; by_department: Record<string, number>; unreadable: string[] }

/**
 * What is still waiting on someone (E14-UC05).
 *
 * Every row ends in one button: open the module that settles it. There is deliberately no
 * approve or reject here — the evidence and the approval live where the item came from.
 */
export function OpenItemInbox({ period, batchId, focusView = '', onClearFocus }:
  { period: string; batchId: string; focusView?: string; onClearFocus?: () => void }) {
  const { t, colon } = useUI()
  const [inbox, setInbox] = useState<Inbox | null>(null), [error, setError] = useState(''), [department, setDepartment] = useState('')
  useEffect(() => {
    if (!period) return
    const controller = new AbortController()
    setInbox(null); setError('')
    const query = `period=${encodeURIComponent(period)}&batch_id=${encodeURIComponent(batchId)}${department ? `&department=${encodeURIComponent(department)}` : ''}`
    void api<Inbox>(`/monthly/inbox?${query}`, { signal: controller.signal })
      .then(setInbox).catch(e => { if (!controller.signal.aborted) setError(describeError(e, t)) })
    return () => controller.abort()
  }, [period, batchId, department])
  if (!period) return null
  if (error) return <p role="alert" className="bf-error">{error}</p>
  if (!inbox) return <p role="status" className="bf-loading">{t('loading')}</p>
  // A step in the checklist and the items behind it are the same facts read twice; focusing
  // a step narrows this list instead of showing the person a second, separate count.
  const shown = focusView ? inbox.items.filter(item => item.next_view === focusView) : inbox.items
  return <section className="bf-inbox" aria-label={t('openItems')}>
    <h3>{t('openItems')} <span className="bf-badge">{inbox.total}</span></h3>
    {focusView
      ? <p className="bf-hint" role="status">{t('inboxFocused')} <button onClick={() => onClearFocus?.()}>{t('inboxClearFocus')}</button></p>
      : <p className="bf-hint">{t('openItemsHint')}</p>}
    <label>{t('department')} <select value={department} onChange={e => setDepartment(e.target.value)}>
      <option value="">{t('allDepartments')}</option>
      {Object.keys(inbox.by_department).map(name => <option key={name} value={name}>{t(name)} · {inbox.by_department[name]}</option>)}
    </select></label>
    {inbox.unreadable.map(reason => <p key={reason} className="bf-hint">{t('inboxUnreadable')}{colon}{reason}</p>)}
    {!shown.length && <p className="bf-hint">{t('inboxEmpty')}</p>}
    <ul>{shown.map(item => <li key={item.id}>
      <b>{t(`item_${item.kind}`) === `item_${item.kind}` ? item.kind : t(`item_${item.kind}`)}</b>
      {item.subject && <span className="bf-mono"> · {item.subject}</span>}
      <span className="bf-hint"> · {item.departments.map(d => t(d)).join('、')}</span>
      {item.detail && <div className="bf-hint">{item.detail}</div>}
      <button onClick={() => navigate({ ...(item.batch_id ? { batch: item.batch_id } : {}), view: item.next_view })}>{t('openToSettle')}</button>
    </li>)}</ul>
  </section>
}

export function CloseChecklist({ period, batchId, onImport, onFocus, focusView = '' }:
  { period: string; batchId: string; onImport: () => void; onFocus?: (nextView: string) => void; focusView?: string }) {
  const { t, colon, list: joined } = useUI()
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
  return <section className="bf-checklist" aria-label={t('closeChecklist')}>
    <h3>{t('closeChecklist')} · {list.period}</h3>
    {list.ready_to_close
      ? <div className="bf-callout" data-tone="ok"><h3>{t('readyToClose')}</h3><p>{t('readyToCloseHint')}</p></div>
      : <p className="bf-hint">{t('checklistHint')}</p>}
    <ol>{list.steps.map(step => <li key={step.id} data-state={step.state} data-focused={step.next_view === focusView}>
      <span className="bf-step-state" data-state={step.state}>{t(`stepState_${step.state}`)}</span>
      <b>{t(`step_${step.id}`)}</b>
      {step.owner_role && <span className="bf-hint bf-step-owner">{t('stepOwner')}{colon}{step.owner_role}</span>}
      {step.state !== 'done' && <>
        {step.outstanding.length > 0 && <div className="bf-hint">{t('stepOutstanding')}{colon}{joined(step.outstanding.map((name: string) => name.replace(/^([a-z_]+)(×\d+)?$/, (whole, kind: string, count = '') => t(`issue_${kind}`) === `issue_${kind}` ? whole : `${t(`issue_${kind}`)}${count}`)))}</div>}
        {step.reason && <div className="bf-hint">{step.reason}</div>}
        <div className="bf-actions" style={{ marginBottom: 0 }}>
          {step.count > 0 && onFocus && <button onClick={() => onFocus(step.next_view)}>{t('stepShowItems')}</button>}
          {step.next_view && <button onClick={() => {
            if (step.next_view === 'import') onImport()
            else navigate({ ...(batchId ? { batch: batchId } : {}), view: step.next_view })
          }}>{t(`stepGo_${step.next_view}`)}</button>}
        </div>
      </>}
    </li>)}</ol>
  </section>
}
