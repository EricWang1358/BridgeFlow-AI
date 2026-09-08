import { useRef, useState } from 'react'
import { formatNumber, navigate, openSession, sendHumanNote, useUI } from './ui.ts'
import { Chip } from './workspace.tsx'
type Source = { department: string; filename: string; sheet: string; source_row: number | null; original_column: string; column: string }
type Check = { check_id: string; title: string; value: number; unit: string; expected_status: string; threshold: number; attention_when: string; formula: string; action: string; explanation: string; sources: Source[]; source_count: number; truncated: boolean }
export type Review = { report_id: string; batch_id: string; parent_session_id: string; period: string; status: string; manager_decision: string; limitations: string[];
  roles: { role: string; status: string; responsibility: string; decision_owner: string; session_id: string; error?: string; checks: Check[] }[] }
export function BusinessReview({ report }: { report: Review }) {
  const { t, language } = useUI()
  const root = useRef<HTMLElement>(null)
  const [note, setNote] = useState(''), [message, setMessage] = useState(''), [busy, setBusy] = useState(false)
  const roles = [...report.roles].sort((a, b) => Number(b.status !== 'validated' || b.checks.some(c => c.expected_status === 'attention')) - Number(a.status !== 'validated' || a.checks.some(c => c.expected_status === 'attention')))
  async function session(child?: string) { const dialog = root.current?.closest('dialog'); try { navigate({ parent: report.parent_session_id, ...(child ? { child } : {}) }); await openSession(report.parent_session_id, child); dialog?.close() } catch (e) { setMessage(String(e)) } }
  return <section ref={root} aria-label={t('reportRegion')} className="bf-report">
    <h3>{report.period} · <Chip status={report.status} /> <span className="bf-badge">{report.roles.filter(r => r.status === 'validated').length}/4</span></h3>
    <p>{t('proposals')}</p><p className="bf-hint">{t('evidenceHint')}</p>
    <p className="bf-attention">{report.manager_decision}</p>
    {report.status === 'partial' && <div className="bf-card">
      <p>{t('partialHelp')}</p><label>{t('humanNote')}<textarea value={note} maxLength={240} onChange={e => setNote(e.target.value)} /></label>
      <button disabled={busy || !note.trim()} onClick={async () => { const dialog = root.current?.closest('dialog'); setBusy(true); try { await sendHumanNote(report.parent_session_id, report.report_id, note); setNote(''); setMessage(t('submitted')); dialog?.close() } catch (e) { setMessage(String(e)) } finally { setBusy(false) } }}>{t('sendNote')}</button>
    </div>}
    {message && <p role="status">{message}</p>}
    <div className="bf-report-roles">{roles.map(role => <article key={role.role} aria-label={`${t(role.role)}${t('roleReview')}`} className="bf-card">
      <h4>{t(role.role)} · <Chip status={role.status} /></h4>
      <p>{t('responsibility')}: {role.responsibility}<br />{t('owner')}: {t(role.decision_owner)}</p>
      {role.error && <p role="alert" className="bf-error">{role.error.slice(0, 300)}</p>}
      {[...role.checks].sort((a, b) => Number(b.expected_status === 'attention') - Number(a.expected_status === 'attention')).map(check => <section key={check.check_id} className={check.expected_status === 'attention' ? 'bf-attention' : ''}>
        <div className="bf-check">
          <span className="bf-check-title">{check.title}</span>
          <b>{formatNumber(check.value, language, { maximumFractionDigits: 4 })} <small>{check.unit}</small></b>
          <Chip status={check.expected_status} />
        </div>
        <p>{t('action')}: {check.action}</p>
        <p className="bf-hint">{t('formula')}: {check.formula}<br />{t('threshold')}: {check.attention_when === 'above' ? '>' : '<'} {check.threshold} {check.unit}</p>
        <details><summary>{t('evidence')}</summary>
          <p>{t('modelAdvice')}: {check.explanation}</p>
          <p>{t('refs')}: {check.source_count} · {t('shown')}: {check.sources.length}{check.truncated ? ' (cap)' : ''}</p>
          <p className="bf-hint">{t('evidenceHint')}</p>
          <ul>{check.sources.map((source, i) => <li key={i}>{t(source.department)} · {source.filename}{source.sheet ? ` / ${source.sheet}` : ''} · {t('sourceRow')} {source.source_row ?? '—'} · {source.original_column || source.column}</li>)}</ul>
        </details>
      </section>)}
      {role.session_id && <button onClick={() => void session(role.session_id)} title={role.session_id}>{t('child')} ↗</button>}
    </article>)}</div>
    <div className="bf-actions"><button onClick={() => void session()}>{t('parent')} ↗</button><button onClick={() => navigate({ batch: report.batch_id, view: 'review', report: report.report_id })}>{t('reportId')}: {report.report_id.slice(0, 8)} ↗</button></div>
    <details><summary>{t('scope')}</summary><ul>{report.limitations.map((item, i) => <li key={i}>{item}</li>)}</ul><p>{t('reportId')}: {report.report_id}</p></details>
  </section>
}
