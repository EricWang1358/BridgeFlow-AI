import { useRef, useState } from 'react'
import { formatNumber, navigate, openSession, sendHumanNote, useUI, describeError, useGloss } from './ui.ts'
import { Chip } from './workspace.tsx'
import { translate as zhMessage } from './zh-messages.ts'
type Source = { department: string; filename: string; sheet: string; source_row: number | null; original_column: string; column: string }
type Check = { check_id: string; title: string; value: number; unit: string; expected_status: string; threshold: number; attention_when: string; formula: string; action: string; explanation: string; sources: Source[]; source_count: number; truncated: boolean }
export type Review = { report_id: string; batch_id: string; parent_session_id: string; period: string; status: string; manager_decision: string; limitations: string[]; terminal_reason?: string;
  usage?: { orchestration?: Record<string, number>; departments?: Record<string, Record<string, number>>; step_limit_per_department?: number };
  roles: { role: string; status: string; responsibility: string; decision_owner: string; session_id: string; error?: string; checks: Check[] }[] }
export function BusinessReview({ report }: { report: Review }) {
  const { t, language } = useUI(), gloss = useGloss()
  const root = useRef<HTMLElement>(null)
  const [note, setNote] = useState(''), [message, setMessage] = useState(''), [busy, setBusy] = useState(false)
  const roles = [...report.roles].sort((a, b) => Number(b.status !== 'validated' || b.checks.some(c => c.expected_status === 'attention')) - Number(a.status !== 'validated' || a.checks.some(c => c.expected_status === 'attention')))
  async function session(child?: string) { const dialog = root.current?.closest('dialog'); try { navigate({ parent: report.parent_session_id, ...(child ? { child } : {}) }); await openSession(report.parent_session_id, child); dialog?.close() } catch (e) { setMessage(describeError(e, t)) } }
  return <section ref={root} aria-label={t('reportRegion')} className="bf-report">
    <h3>{report.period} · <Chip status={report.status} /> <span className="bf-badge">{report.roles.filter(r => r.status === 'validated').length}/4</span></h3>
    <p>{t('proposals')}</p><p className="bf-hint">{t('evidenceHint')}</p>
    {report.terminal_reason && report.terminal_reason !== 'completed' && <div className="bf-callout" data-tone="warn"><h3>{t('reviewEnded')}</h3><p>{t(`ended_${report.terminal_reason}`)}</p></div>}
    <p className="bf-attention">{gloss.text(report.manager_decision)}</p>
    {report.status === 'partial' && <div className="bf-card">
      <p>{t('partialHelp')}</p><label>{t('humanNote')}<textarea value={note} maxLength={240} onChange={e => setNote(e.target.value)} /></label>
      <button disabled={busy || !note.trim()} onClick={async () => { const dialog = root.current?.closest('dialog'); setBusy(true); try { await sendHumanNote(report.parent_session_id, report.batch_id, report.report_id, note); setNote(''); setMessage(t('submitted')); dialog?.close() } catch (e) { setMessage(describeError(e, t)) } finally { setBusy(false) } }}>{t('sendNote')}</button>
    </div>}
    {message && <p role="status">{message}</p>}
    <div className="bf-report-roles">{roles.map(role => <article key={role.role} aria-label={`${t(role.role)}${t('roleReview')}`} className="bf-card">
      <h4>{t(role.role)} · <Chip status={role.status} /></h4>
      <p>{t('responsibility')}: {gloss.text(role.responsibility)}<br />{t('owner')}: {t(role.decision_owner)}</p>
      {role.error && <p role="alert" className="bf-error">{role.error.slice(0, 300)}</p>}
      {[...role.checks].sort((a, b) => Number(b.expected_status === 'attention') - Number(a.expected_status === 'attention')).map(check => <section key={check.check_id} className={check.expected_status === 'attention' ? 'bf-attention' : ''}>
        <div className="bf-check">
          <span className="bf-check-title">{gloss.text(check.title)}</span>
          <b>{formatNumber(check.value, language, { maximumFractionDigits: 4 })} <small>{gloss.text(check.unit)}</small></b>
          <Chip status={check.expected_status} />
        </div>
        <p>{t('action')}: {gloss.text(check.action)}</p>
        <p className="bf-hint"><span title={check.formula}>{t('formula')}: {gloss.formula(check.formula)}</span><br />{t('threshold')}: {check.attention_when === 'above' ? '>' : '<'} {check.threshold} {gloss.text(check.unit)}</p>
        <details><summary>{t('evidence')}</summary>
          <p>{t('modelAdvice')}: {check.explanation}</p>
          <p>{t('refs')}: {check.source_count} · {t('shown')}: {check.sources.length}{check.truncated ? ' (cap)' : ''}</p>
          <p className="bf-hint">{t('evidenceHint')}</p>
          <ul>{check.sources.map((source, i) => <li key={i}><button className="bf-quiet" title={t('openSource')} onClick={() => { root.current?.closest('dialog')?.close(); navigate({ batch: report.batch_id, view: 'source', source: source.department }) }}>{t(source.department)} · {source.filename}{source.sheet ? ` / ${source.sheet}` : ''} · {t('sourceRow')} {source.source_row ?? '—'} · {source.original_column || source.column} ↗</button></li>)}</ul>
        </details>
      </section>)}
      {role.session_id && <button onClick={() => void session(role.session_id)} title={role.session_id}>{t('child')} ↗</button>}
    </article>)}</div>
    {report.usage?.orchestration && <details className="bf-formulas"><summary>{t('reviewUsage')}</summary>
      <p className="bf-hint">{t('orchestration')}: {report.usage.orchestration.steps ?? 0} {t('steps')} · {report.usage.orchestration.total_tokens ?? 0} tokens</p>
      {Object.entries(report.usage.departments ?? {}).map(([role, u]) => <p className="bf-hint" key={role}>{t(role)}: {u.steps ?? 0}/{report.usage?.step_limit_per_department ?? '—'} {t('steps')} · {u.total_tokens ?? 0} tokens</p>)}
    </details>}
    <div className="bf-actions"><button onClick={() => void session()}>{t('parent')} ↗</button><button onClick={() => navigate({ batch: report.batch_id, view: 'review', report: report.report_id })}>{t('reportId')}: {report.report_id.slice(0, 8)} ↗</button></div>
    <details><summary>{t('scope')}</summary><ul>{report.limitations.map((item, i) => <li key={i}>{language === 'zh' ? zhMessage(item) : gloss.text(item)}</li>)}</ul><p>{t('reportId')}: {report.report_id}</p></details>
  </section>
}
