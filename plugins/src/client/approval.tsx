import { useEffect, useRef, useState } from 'react'
import { api, useUI, describeError } from './ui.ts'
import type { Limits } from './workspace.tsx'
import type { PendingApproval } from '@deepseek-ai/dsh-client-ui-approval/client'

/** One label/value pair, matching the plugin's ApprovalDetail. */
type Detail = { label: string; value: string }

/** Presentation override only: the official pending request owns settlement. */
export function MappingApproval({ matched }: { matched: PendingApproval }) {
  return <MappingApprovalForm key={matched.key} pending={matched} />
}
function MappingApprovalForm({ pending }: { pending: PendingApproval }) {
  const { t } = useUI()
  const [timeout, setTimeoutValue] = useState<number | null>(null)
  const [note, setNote] = useState('')
  const [ticket, setTicket] = useState('')
  const [details, setDetails] = useState<Detail[] | null>(null)
  const [detailFailed, setDetailFailed] = useState(false), [attempt, setAttempt] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const card = useRef<HTMLElement>(null)
  // A decision that appears must be reachable without a mouse: focus lands on the card,
  // then Tab reaches the reason, Reject and Allow in that order.
  useEffect(() => { card.current?.focus() }, [pending])
  useEffect(() => {
    const abort = new AbortController()
    void api<Limits>('/config', { signal: abort.signal }).then(v => setTimeoutValue(v.decisionTimeoutMs / 1000)).catch(() => {})
    const query = new URLSearchParams({ session_id: pending.sessionId, call_id: pending.callId ?? '' })
    void fetch(`/bridgeflow/approval-notes?${query}`, { signal: abort.signal })
      .then(async response => { if (!response.ok) throw new Error(t('expired')); return response.json() })
      .then(value => setTicket(value.ticket))
      .catch(e => { if (!abort.signal.aborted) setError(describeError(e, t)) })
    setDetailFailed(false)
    void fetch(`/bridgeflow/approval-detail?${query}`, { signal: abort.signal })
      .then(async response => { if (!response.ok) throw new Error(String(response.status)); return response.json() })
      .then(value => { if (!abort.signal.aborted) setDetails(value.details ?? []) })
      // A summary that failed to load is not "no summary": say so and offer a retry,
      // rather than silently falling back to the raw reason (#96).
      .catch(() => { if (!abort.signal.aborted) { setDetails(null); setDetailFailed(true) } })
    return () => abort.abort()
  }, [pending, attempt])
  // Argument names are this plugin's own closed set (tools/confirm-mapping.ts), so
  // they translate; a name outside the set shows verbatim rather than as arg_foo.
  // Values are the operator's evidence — shown exactly as declared, never rewritten.
  const argLabel = (label: string): string => {
    const translated = t(`arg_${label}`)
    return translated === `arg_${label}` ? label : translated
  }
  const argValue = (detail: Detail): string =>
    detail.label === 'accepted'
      ? (detail.value === 'true' ? t('acceptMapping') : detail.value === 'false' ? t('rejectMapping') : detail.value)
      : detail.value
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
    } catch (e) { setError(describeError(e, t)); setBusy(false) }
  }
  // Each tool's decision is named for what it decides; the mapping wording is kept for mappings.
  const kind = pending.toolName === 'confirm_mapping' ? '' : `_${pending.toolName}`
  return <section ref={card} tabIndex={-1} className="bf-card bf-decision" aria-label={t(`approval${kind}`)}>
    <header>
      <strong>{t(`approvalTitle${kind}`)}</strong>
      <span className="bf-hint">{t('timeout')} {timeout ?? '—'} {t('seconds')}</span>
    </header>
    {/* The reason is the whole basis of the decision. Rendered as localized prose
        plus the structured summary from /approval-detail (#96 pairs, #110 locale);
        the raw reason string is the fallback for a call whose summary is gone and
        remains what the native console dialog shows. */}
    <div className="bf-callout" data-tone="info">
      <p>{t('approvalIntro')}</p>
      {detailFailed
        ? <div role="alert"><p className="bf-error">{t('approvalDetailFailed')}</p><p>{pending.reason}</p>
            <button onClick={() => setAttempt(n => n + 1)}>{t('retry')}</button></div>
        : details === null
        ? <p className="bf-hint">{t('loading')}</p>
        : details.length
          ? <dl className="bf-approval-detail">
              <dt>{t('approvalTool')}</dt><dd><code className="bf-mono">{pending.toolName}</code></dd>
              {details.map((detail, i) => <span key={i} style={{ display: 'contents' }}><dt>{argLabel(detail.label)}</dt><dd>{argValue(detail)}</dd></span>)}
            </dl>
          : <p>{pending.reason}</p>}
    </div>
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
