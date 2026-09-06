import { useEffect, useRef, useState, type FormEvent } from 'react'
import { BusinessReview, type Review } from './review.tsx'
import { api, cellText, columnLabel, navigate, route, reviewRequest, useUI, type Summary } from './ui.ts'
export const departments = ['production', 'procurement', 'finance', 'marketing'] as const
export const sections = ['master', 'corrections', 'mappings', 'quarantine', 'review'] as const
export function Chip({ status }: { status: string }) { const { t } = useUI(); return <span className="bf-chip" data-status={status}>{t(status.replaceAll('-', '_'))}</span> }
export type Limits = { maxUploadBytes: number; maxRequestBytes: number; noteLimit: number; decisionTimeoutMs: number }
export function ImportForm({ onSaved }: { onSaved: (batch: Summary) => void }) {
  const { t } = useUI()
  const [limits, setLimits] = useState<Limits | null>(null)
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  useEffect(() => { const controller = new AbortController(); void api<Limits>('/config', { signal: controller.signal }).then(setLimits).catch(e => { if (!controller.signal.aborted) setError(String(e)) }); return () => controller.abort() }, [])
  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError('')
    const form = new FormData(event.currentTarget), body = new FormData()
    body.set('period', String(form.get('period')))
    let total = 0, count = 0
    for (const name of departments) {
      const file = form.get(name)
      if (file instanceof File && file.size) {
        if (!/\.(csv|xlsx)$/i.test(file.name)) { setError(t('invalidUpload')); return }
        total += file.size; count++; body.append('departments', name); body.append('files', file)
      }
    }
    if (!count || !limits || total > limits.maxUploadBytes) { setError(t('invalidUpload')); return }
    setBusy(true)
    try { onSaved(await api<Summary>('/batches', { method: 'POST', body })) }
    catch (e) { setError(String(e)) } finally { setBusy(false) }
  }
  return <form onSubmit={upload} className="bf-steps">
    <div className="bf-step">
      <h3>{t('stepMonth')}</h3>
      <input type="month" name="period" aria-label={t('month')} required />
    </div>
    <div className="bf-step">
      <h3>{t('stepFiles')}</h3>
      <p className="bf-hint">{t('stepFilesHint')} {t('uploadHelp')}</p>
      <div className="bf-files">{departments.map(name => <FileRow key={name} name={name} />)}</div>
    </div>
    <div className="bf-step">
      <h3>{t('stepGo')}</h3>
      <p className="bf-hint">{t('stepGoHint')} {limits ? `${t('limits')}: ${limits.maxUploadBytes / 1048576} MiB · ${t('transport')}: ${limits.maxRequestBytes / 1048576} MiB` : t('loading')}</p>
      {error && <p role="alert" className="bf-error">{error}</p>}
      <button className="bf-primary" disabled={busy || !limits} type="submit">{t(busy ? 'busy' : 'import')}</button>
    </div>
  </form>
}

/** One department's file, showing what was actually chosen.
 *
 * The browser's own control renders "Choose File / No file chosen" in English
 * regardless of locale, and gives no sign that a file landed. Wrapping the real
 * input in a label keeps the native picker, keyboard behaviour and form semantics
 * — this is presentation, not a re-implementation.
 */
function FileRow({ name }: { name: string }) {
  const { t } = useUI()
  const [chosen, setChosen] = useState('')
  return <label className="bf-file" data-filled={Boolean(chosen)}>
    <input type="file" name={name} accept=".csv,.xlsx" aria-label={t(name)}
      onChange={e => setChosen(e.target.files?.[0]?.name ?? '')} />
    <span style={{ minWidth: 0 }}>
      <b>{t(name)}</b>
      <span className="bf-file-name">{chosen || t('noFile')}</span>
    </span>
  </label>
}
type View = { total: number; offset: number; rows: Record<string, unknown>[] }

/** Which action the batch's own status implies. A state with no next step leaves
 *  the reader stuck holding a label. */
const NEXT_STEP: Record<string, string> = {
  needs_configuration: 'next_needs_configuration',
  needs_review: 'next_needs_review',
  ready: 'next_ready',
  empty: 'next_empty',
}
const NEXT_TONE: Record<string, string> = {
  needs_configuration: 'danger', needs_review: 'warn', ready: 'info', empty: 'warn',
}
export function DataWorkspace({ wide }: { wide: boolean }) {
  const { t } = useUI(), dialog = useRef<HTMLDialogElement>(null)
  const [batch, setBatch] = useState<Summary | null>(null), [batchId, setBatchId] = useState('')
  const [section, setSection] = useState('master'), [offset, setOffset] = useState(0)
  const [view, setView] = useState<View | null>(null), [review, setReview] = useState<Review | null>(null)
  const [reportId, setReportId] = useState(''), [revision, setRevision] = useState(0)
  const [error, setError] = useState(''), [busy, setBusy] = useState(false), [notice, setNotice] = useState('')
  const currentBatch = useRef(batch); currentBatch.current = batch
  const pendingBatch = useRef<AbortController | null>(null)
  function selectBatch(id: string, selectedSection = 'master', selectedReport = '') {
    navigate({ batch: id, view: selectedSection, ...(selectedReport ? { report: selectedReport } : {}) })
  }
  function close() {
    dialog.current?.close()
    const value = route()
    if (value.batch && value.view !== 'state') navigate({ batch: value.batch, view: 'state' })
  }
  useEffect(() => {
    let abort: AbortController | undefined
    const readRoute = () => {
      const value = route()
      abort?.abort(); setBusy(false)
      if (!value.batch || value.view === 'state' || !/^[a-f0-9]{32}$/.test(value.batch)) return
      pendingBatch.current?.abort(); abort = new AbortController(); pendingBatch.current = abort; const signal = abort.signal
      dialog.current?.showModal(); setBatchId(value.batch); setReportId(value.report ?? '')
      setSection(sections.includes(value.view as typeof sections[number]) ? value.view! : 'master'); setOffset(0)
      setError('')
      if (currentBatch.current?.batch_id === value.batch) return
      setNotice(''); setBatch(null); setView(null); setReview(null); setBusy(true)
      void api<Summary>(`/batches/${value.batch}`, { signal }).then(result => { if (!signal.aborted) setBatch(result) }).catch(e => { if (!signal.aborted) setError(String(e)) }).finally(() => { if (!signal.aborted) setBusy(false) })
    }
    readRoute(); window.addEventListener('hashchange', readRoute)
    return () => { abort?.abort(); pendingBatch.current?.abort(); window.removeEventListener('hashchange', readRoute) }
  }, [])
  useEffect(() => {
    if (!batch) return
    const abort = new AbortController(); setView(null); setReview(null); setError('')
    if (section === 'review') {
      void api<Review>(`/batches/${batch.batch_id}/review${reportId ? `?report_id=${encodeURIComponent(reportId)}` : ''}`, { signal: abort.signal }).then(setReview)
        .catch(e => { if (!abort.signal.aborted) setError(String(e).includes('no saved review') ? t('noReport') : String(e)) })
    } else void api<View>(`/batches/${batch.batch_id}/view?section=${section}&offset=${offset}`, { signal: abort.signal }).then(setView).catch(e => { if (!abort.signal.aborted) setError(String(e)) })
    return () => abort.abort()
  }, [batch, section, offset, reportId, revision])
  async function copy(text: string, message: string) { try { await navigator.clipboard.writeText(text); setNotice(message) } catch (e) { setError(String(e)) } }
  const columns = Array.from(new Set(view?.rows.flatMap(row => Object.keys(row)) ?? []))
  const counts: Record<string, number | string> = batch ? { master: batch.master_rows, mappings: batch.unresolved,
    corrections: batch.departments.reduce((n, d) => n + d.corrections, 0), quarantine: batch.departments.reduce((n, d) => n + d.quarantined, 0), review: review ? `${review.roles.filter(r => r.status === 'validated').length}/4` : '—' } : {}
  function tab(key: string) { setSection(key); setOffset(0); if (batch) navigate({ batch: batch.batch_id, view: key, ...(key === 'review' && reportId ? { report: reportId } : {}) }) }
  return <>
    <button className="bf-open" onClick={() => dialog.current?.showModal()} title={t('data')}>{wide ? t('data') : t('master')}</button>
    <dialog className="bf-panel" ref={dialog} onCancel={close} aria-label={t('workspace')}>
      <header className="bf-panel-head">
        <div>
          <h2>{t(batch ? 'title' : 'intro')}</h2>
          {batch
            ? <p className="bf-lead bf-hint">{t('batchIdShort')} <code className="bf-mono">{batch.batch_id.slice(0, 12)}…</code>{' '}
                <button className="bf-quiet" onClick={() => void copy(batch.batch_id, t('copied'))}>{t('copyId')}</button></p>
            : <p className="bf-lead">{t('heroLead')}</p>}
        </div>
        <button className="bf-quiet" onClick={close}>{t('close')}</button>
      </header>
      <div className="bf-panel-body">
      <details open={!batch}><summary>{t('newBatch')}</summary><ImportForm onSaved={result => { pendingBatch.current?.abort(); setReportId(''); setView(null); setReview(null); currentBatch.current = result; setBatch(result); setBatchId(result.batch_id); setOffset(0); setSection('master'); setNotice(t('saved')); selectBatch(result.batch_id) }} /></details>
      <details><summary>{t('existing')}</summary><label>{t('batchId')} <input value={batchId} onChange={e => setBatchId(e.target.value)} /></label>
        <button disabled={busy || !/^[a-f0-9]{32}$/.test(batchId)} onClick={() => selectBatch(batchId)}>{t('open')}</button></details>
      <p role="status">{notice}</p>{error && <p role="alert" className="bf-error">{error}</p>}
      {batch && <section>
        <div className="bf-band">
          <span className="bf-period">{batch.period}</span> <Chip status={batch.status} />
        </div>
        <p className="bf-hint" style={{ margin: 0 }}>{t('master')} {batch.master_rows} {t('rows')} · {t('mappings')} {batch.unresolved}{t('total') === '共' ? ' 条' : ''}</p>

        {/* A status is only actionable next to the step it implies. */}
        {NEXT_STEP[batch.status] && <div className="bf-callout" data-tone={NEXT_TONE[batch.status] ?? 'info'}>
          <h3>{t('nextTitle')}</h3><p>{t(NEXT_STEP[batch.status]!)}</p>
        </div>}
        {/* The refusal is the most important sentence on the panel; it used to be
            ordinary red body copy sandwiched between two counts. */}
        {batch.refusal && <div className="bf-callout" data-tone="danger">
          <h3>{t(batch.master_rows ? 'whyRefused' : 'whyEmpty')}</h3><p>{batch.refusal}</p>
        </div>}

        <div className="bf-stats">{batch.departments.map(d => <div className="bf-stat" key={d.department}>
          <b>{d.rows}</b><span>{t(d.department)} · {d.corrections} {t('corrections')} / {d.quarantined} {t('quarantine')}</span>
        </div>)}</div>

        <div className="bf-actions">
          <button className="bf-primary" onClick={() => void copy(reviewRequest(batch.batch_id, batch.period), t('copiedRequest'))}>{t('copy')}</button>
          <button onClick={() => setRevision(r => r + 1)}>{t('refresh')}</button>
        </div>
        <nav className="bf-tabs" aria-label={t('tabs')}>{sections.map(key => <button key={key} aria-label={t(key)} aria-pressed={section === key} onClick={() => tab(key)}>{t(key)} <span className="bf-badge">{counts[key]}</span></button>)}</nav>
        {section === 'mappings' && <p className="bf-hint">{t('mappingHelp')}</p>}{section === 'quarantine' && <p className="bf-hint">{t('quarantineHelp')}</p>}
        {section === 'review' ? review ? <BusinessReview report={review} /> : !error && <p role="status">{t('loading')}</p> : view ? <>
          {view.rows.length > 0 && <div className="bf-scroll"><table><thead><tr>{columns.map(c => {
            const { group, label } = columnLabel(c, t)
            return <th scope="col" key={c}>{group && <small>{group}</small>}{label}</th>
          })}</tr></thead><tbody>{view.rows.map((row, i) => <tr key={i}>{columns.map(c => {
            const { text, note, full, numeric, empty } = cellText(row[c])
            // The clipped form is what fits; the whole value stays one hover away,
            // because a table that silently shortens a business value is lying.
            return <td key={c} data-numeric={numeric} data-empty={empty} {...(full ? { title: full } : {})}>{text}{note && <span className="bf-cellnote">{note}</span>}</td>
          })}</tr>)}</tbody></table></div>}
          {!view.rows.length && <div className="bf-empty"><strong>{t('empty')}</strong>{t('noRows')}</div>}
          <div className="bf-pager">
            <span className="bf-hint">{t('total')} {view.total} · {offset + (view.rows.length ? 1 : 0)}–{offset + view.rows.length}</span>
            <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 50))}>{t('previous')}</button>
            <button disabled={offset + 50 >= view.total} onClick={() => setOffset(offset + 50)}>{t('next')}</button>
          </div>
        </> : !error && <p role="status">{t('loading')}</p>}
      </section>}
      </div>
    </dialog>
  </>
}
