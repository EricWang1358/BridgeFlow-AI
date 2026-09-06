import { useEffect, useState } from 'react'
import { api, useUI } from './ui.ts'
import type { Limits } from './workspace.tsx'
import type { PendingApproval } from '@deepseek-ai/dsh-client-ui-approval/client'

/** Presentation override only: the official pending request owns settlement. */
export function MappingApproval({ matched }: { matched: PendingApproval }) {
  return <MappingApprovalForm key={matched.key} pending={matched} />
}
function MappingApprovalForm({ pending }: { pending: PendingApproval }) {
  const { t } = useUI()
  const [timeout, setTimeoutValue] = useState<number | null>(null)
  const [note, setNote] = useState('')
  const [ticket, setTicket] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    const abort = new AbortController()
    void api<Limits>('/config', { signal: abort.signal }).then(v => setTimeoutValue(v.decisionTimeoutMs / 1000)).catch(() => {})
    const query = new URLSearchParams({ session_id: pending.sessionId, call_id: pending.callId ?? '' })
    void fetch(`/bridgeflow/approval-notes?${query}`, { signal: abort.signal })
      .then(async response => { if (!response.ok) throw new Error(t('expired')); return response.json() })
      .then(value => setTicket(value.ticket))
      .catch(e => { if (!abort.signal.aborted) setError(String(e)) })
    return () => abort.abort()
  }, [pending])
  async function answer(outcome: 'allowed-once' | 'rejected') {
    setBusy(true); setError('')
    try {
      if (outcome === 'rejected' && note.trim()) {
        const response = await fetch('/bridgeflow/approval-notes', {
          method: 'POST', headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ session_id: pending.sessionId, call_id: pending.callId, ticket, note }),
        })
        if (!response.ok) throw new Error(t('noteFail'))
      }
      await pending.answer(outcome)
    } catch (e) { setError(String(e)); setBusy(false) }
  }
  return <section className="bf-card bf-decision" aria-label={t('approval')}>
    <header>
      <strong>{t('approvalTitle')}</strong>
      <span className="bf-hint">{t('timeout')} {timeout ?? '—'} {t('seconds')}</span>
    </header>
    {/* The reason is the whole basis of the decision, so it reads as prose rather
        than as the monospace dump of a machine value it used to be. */}
    <div className="bf-callout" data-tone="info"><p>{pending.reason}</p></div>
    <label className="bf-field">
      <span>{t('optionalReason')}</span>
      <textarea aria-label={t('reason')} value={note} maxLength={240} disabled={busy}
        onChange={e => setNote(e.target.value)} />
      <span className="bf-hint">{note.length}/240</span>
    </label>
    <p className="bf-hint">{t('noteHelp')}</p>
    {error && <p role="alert" className="bf-error">{error}</p>}
    {/* Reject sits first and is never the primary. A decision surface that makes
        approving the easy default trains people to approve without reading. */}
    <div className="bf-actions">
      <button className="bf-danger-btn" disabled={busy || (!!note.trim() && !ticket)} onClick={() => void answer('rejected')}>{t('reject')}</button>
      <button className="bf-primary" disabled={busy} onClick={() => void answer('allowed-once')}>{t('allow')}</button>
    </div>
  </section>
}
