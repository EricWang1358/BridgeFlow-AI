import { useEffect, useRef, useState, type FormEvent } from 'react'
import { BusinessReview, type Review } from './review.tsx'
import { api, cellText, columnLabel, navigate, route, reviewRequest, startDiagnosis, startReview, useUI, type Summary, describeError } from './ui.ts'
export const departments = ['production', 'procurement', 'finance', 'marketing'] as const
export const sections = ['master', 'corrections', 'mappings', 'columns', 'quarantine', 'review'] as const
export function Chip({ status }: { status: string }) { const { t } = useUI(); return <span className="bf-chip" data-status={status}>{t(status.replaceAll('-', '_'))}</span> }
export type Limits = { maxUploadBytes: number; maxRequestBytes: number; noteLimit: number; decisionTimeoutMs: number }
type Finding = { check: string; message: string; row: number | null; column: string; count: number }
type CheckReport = { department: string; filename: string; must_fix: Finding[]; review: Finding[]; passed: string[]; accepts: boolean }
export function ImportForm({ onSaved }: { onSaved: (batch: Summary) => void }) {
  const { t } = useUI()
  const [limits, setLimits] = useState<Limits | null>(null)
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [reports, setReports] = useState<CheckReport[]>([])
  const formRef = useRef<HTMLFormElement>(null)
  useEffect(() => { const controller = new AbortController(); void api<Limits>('/config', { signal: controller.signal }).then(setLimits).catch(e => { if (!controller.signal.aborted) setError(describeError(e, t)) }); return () => controller.abort() }, [])
  async function selfCheck() {
    if (!formRef.current) return
    const form = new FormData(formRef.current)
    setError(''); setReports([])
    if (!form.get('period')) { setError(t('selfCheckNeedsPeriod')); return }
    setBusy(true)
    try {
      const found: CheckReport[] = []
      for (const name of departments) {
        const file = form.get(name)
        if (!(file instanceof File) || !file.size) continue
        const body = new FormData()
        body.set('period', String(form.get('period'))); body.set('department', name); body.set('file', file)
        body.set('sheet', String(form.get(`${name}-sheet`) ?? '')); body.set('header_row', String(form.get(`${name}-header`) ?? ''))
        found.push(await api<CheckReport>('/batches/self-check', { method: 'POST', body }))
      }
      if (!found.length) setError(t('invalidUpload'))
      setReports(found)
    } catch (e) { setError(describeError(e, t)) } finally { setBusy(false) }
  }
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
        body.append('sheets', String(form.get(`${name}-sheet`) ?? '')); body.append('header_rows', String(form.get(`${name}-header`) ?? ''))
      }
    }
    if (!count || !limits || total > limits.maxUploadBytes) { setError(t('invalidUpload')); return }
    setBusy(true)
    try { onSaved(await api<Summary>('/batches', { method: 'POST', body })) }
    catch (e) { setError(describeError(e, t)) } finally { setBusy(false) }
  }
  return <form ref={formRef} onSubmit={upload} className="bf-steps">
    <div className="bf-step">
      <h3>{t('stepMonth')}</h3>
      <input type="month" name="period" aria-label={t('month')} required />
    </div>
    <div className="bf-step">
      <h3>{t('stepFiles')}</h3>
      <p className="bf-hint">{t('stepFilesHint')} {t('uploadHelp')}</p>
      <div className="bf-files">{departments.map(name => <FileRow key={name} name={name} />)}</div>
      <p className="bf-hint">{t('selfCheckHelp')}</p>
      <button type="button" disabled={busy} onClick={() => void selfCheck()}>{t('selfCheck')}</button>
      {reports.map(report => <div key={report.department} className="bf-callout" data-tone={report.accepts ? 'ok' : 'warn'} role="status">
        <h3>{t(report.department)} · {report.filename} · {report.accepts ? t('selfCheckAccepted') : `${t('selfCheckMustFix')} ${report.must_fix.length}`}</h3>
        {report.must_fix.length > 0 && <ul>{report.must_fix.map((f, i) => <li key={i}>{f.row ? `row ${f.row} · ` : ''}{f.column && !f.message.startsWith(f.column) ? `${f.column} · ` : ''}{f.message}{f.count > 1 ? ` ×${f.count}` : ''}</li>)}</ul>}
        {report.review.length > 0 && <details><summary>{t('selfCheckReview')} {report.review.length}</summary><ul>{report.review.map((f, i) => <li key={i}>{f.column ? `${f.column} · ` : ''}{f.message} ×{f.count}</li>)}</ul></details>}
      </div>)}
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
  return <div>
  <label className="bf-file" data-filled={Boolean(chosen)}>
    <input type="file" name={name} accept=".csv,.xlsx" aria-label={t(name)}
      onChange={e => setChosen(e.target.files?.[0]?.name ?? '')} />
    <span style={{ minWidth: 0 }}>
      <b>{t(name)}</b>
      <span className="bf-file-name">{chosen || t('noFile')}</span>
    </span>
  </label>
  {/\.xlsx$/i.test(chosen) && <details className="bf-hint">
    <summary>{t('sheetLayout')}</summary>
    <input name={`${name}-sheet`} aria-label={`${t(name)} · ${t('sheetName')}`} placeholder={t('sheetName')} />
    <input name={`${name}-header`} type="number" min={1} aria-label={`${t(name)} · ${t('headerRow')}`} placeholder={t('headerRow')} />
  </details>}
  </div>
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
export function DataWorkspaceButton({ wide }: { wide: boolean }) {
  const { t } = useUI()
  return <button className="bf-open" onClick={() => window.dispatchEvent(new Event('bridgeflow:open-data'))} title={t('data')}>{wide ? t('data') : t('master')}</button>
}

/** Keep the modal in shell.overlay: a collapsed sidebar must never hide a modal that makes the page inert. */
export function DataWorkspace() {
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
      if (['discovery', 'quotation', 'handoff', 'integration', 'brief', 'source', 'artifact'].includes(value.view ?? '')) { dialog.current?.close(); return }
      if (!value.batch || value.view === 'state' || !/^[a-f0-9]{32}$/.test(value.batch)) return
      pendingBatch.current?.abort(); abort = new AbortController(); pendingBatch.current = abort; const signal = abort.signal
      dialog.current?.showModal(); setBatchId(value.batch); setReportId(value.report ?? '')
      setSection(sections.includes(value.view as typeof sections[number]) ? value.view! : 'master'); setOffset(0)
      setError('')
      if (currentBatch.current?.batch_id === value.batch) return
      setNotice(''); setBatch(null); setView(null); setReview(null); setBusy(true)
      void api<Summary>(`/batches/${value.batch}`, { signal }).then(result => { if (!signal.aborted) setBatch(result) }).catch(e => { if (!signal.aborted) setError(describeError(e, t)) }).finally(() => { if (!signal.aborted) setBusy(false) })
    }
    const open = () => { if (!dialog.current?.open) dialog.current?.showModal() }
    window.addEventListener('bridgeflow:open-data', open)
    readRoute(); window.addEventListener('hashchange', readRoute)
    return () => { abort?.abort(); pendingBatch.current?.abort(); window.removeEventListener('hashchange', readRoute); window.removeEventListener('bridgeflow:open-data', open) }
  }, [])
  useEffect(() => {
    if (!batch) return
    const abort = new AbortController(); setView(null); setReview(null); setError('')
    if (section === 'review') {
      void api<Review>(`/batches/${batch.batch_id}/review${reportId ? `?report_id=${encodeURIComponent(reportId)}` : ''}`, { signal: abort.signal }).then(setReview)
        .catch(e => { if (!abort.signal.aborted) setError(String(e).includes('no saved review') ? t('noReport') : describeError(e, t)) })
    } else void api<View>(`/batches/${batch.batch_id}/view?section=${section}&offset=${offset}`, { signal: abort.signal }).then(setView).catch(e => { if (!abort.signal.aborted) setError(describeError(e, t)) })
    return () => abort.abort()
  }, [batch, section, offset, reportId, revision])
  async function copy(text: string, message: string) { try { await navigator.clipboard.writeText(text); setNotice(message) } catch (e) { setError(describeError(e, t)) } }
  const columns = Array.from(new Set(view?.rows.flatMap(row => Object.keys(row)) ?? []))
  const counts: Record<string, number | string> = batch ? { master: batch.master_rows, mappings: batch.unresolved,
    corrections: batch.departments.reduce((n, d) => n + d.corrections, 0), columns: batch.column_questions ?? 0, quarantine: batch.departments.reduce((n, d) => n + d.quarantined, 0), review: review ? `${review.roles.filter(r => r.status === 'validated').length}/4` : '—' } : {}
  function tab(key: string) { setSection(key); setOffset(0); if (batch) navigate({ batch: batch.batch_id, view: key, ...(key === 'review' && reportId ? { report: reportId } : {}) }) }
  return <>
    <dialog className="bf-panel" ref={dialog} onCancel={close} aria-label={t('workspace')}>
      <header className="bf-panel-head">
        <div>
          <h2>{t(batch ? 'title' : 'intro')}</h2>
          {batch
            ? <p className="bf-lead bf-hint">{t('batchIdShort')} <code className="bf-mono">{batch.batch_id}</code>{' '}
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
        <p className="bf-hint" style={{ margin: 0 }}>{t('master')} {batch.master_rows} {t('rows')} · {t('mappings')} {batch.unresolved}{t('countSuffix')}</p>

        {/* A status is only actionable next to the step it implies. */}
        {NEXT_STEP[batch.status] && <div className="bf-callout" data-tone={NEXT_TONE[batch.status] ?? 'info'}>
          <h3>{t('nextTitle')}</h3><p>{t(NEXT_STEP[batch.status]!)}</p>
          {/* A blocked batch must not end in a sentence. The operator is holding four
              sheets and the same question the machine could not answer; leaving them
              to work it out alone is the thing this product exists to remove. */}
          {batch.status === 'needs_configuration' && <>
            <p className="bf-hint" style={{ marginTop: 8 }}>
              {batch.column_questions ? <><b>{batch.column_questions}</b> {t('columnQuestions')}。</> : null}{t('askCaptainHint')}
            </p>
            <div className="bf-actions" style={{ marginBottom: 0 }}>
              <button className="bf-primary" disabled={busy} onClick={async () => {
                setError(''); setBusy(true)
                try { await startDiagnosis(batch.batch_id, batch.period); close() }
                catch (e) { setError(describeError(e, t)) } finally { setBusy(false) }
              }}>{t(busy ? 'busy' : 'askCaptain')}</button>
            </div>
          </>}
        </div>}
        {/* The refusal is the most important sentence on the panel; it used to be
            ordinary red body copy sandwiched between two counts. */}
        {batch.refusal && <div className="bf-callout" data-tone="danger">
          <h3>{t(batch.master_rows ? 'whyRefused' : 'whyEmpty')}</h3><p>{batch.refusal}</p>
          {/* The refusal names the department. It cannot say whether the dictionary
              is incomplete or simply not the one the operator meant to use, and that
              is the difference between a five-second fix and a dead end. */}
          {batch.dictionary && <p className="bf-hint" style={{ marginTop: 8 }}>
            {t('dictionaryInForce')}: <code className="bf-mono">{batch.dictionary}</code>
          </p>}
          {batch.declared_entities && <p className="bf-hint">{t('declaresEntities')}: {departments.map(name =>
            `${t(name)} → ${batch.declared_entities?.[name]?.join('、') || t('declaresNothing')}`).join(' · ')}</p>}
        </div>}

        {/* A match that changed how this batch was read must be visible on it, and so
            must a decision that was deliberately not reused. */}
        {!!batch.matched_columns?.length && <div className="bf-callout" data-tone="ok">
          <h3>{t('matchedColumns')}</h3><p className="bf-mono">{batch.matched_columns.join(' · ')}</p>
        </div>}
        {!!batch.stale_matches?.length && <div className="bf-callout" data-tone="warn">
          <h3>{t('staleMatches')}</h3><p className="bf-mono">{batch.stale_matches.join(' · ')}</p>
        </div>}
        {!!batch.dropped_columns?.length && <div className="bf-callout" data-tone="warn">
          <h3>{t('droppedColumns')}</h3>
          <p className="bf-mono">{batch.dropped_columns.map(c => `${t(c.department)}.${c.column}（${c.field_type}）`).join(' · ')}</p>
        </div>}

        {!!batch.superseded_by?.length && <div className="bf-callout" data-tone="warn">
          <h3>{t('superseded')}</h3><p>{t('supersededHint')}</p>
          <div className="bf-actions" style={{ marginBottom: 0 }}>
            <button onClick={() => selectBatch(batch.superseded_by!.at(-1)!)}>{t('openNewest')}</button>
          </div>
        </div>}
        {batch.derived_from && <p className="bf-hint">{t('derivedFrom')}: <code className="bf-mono">{batch.derived_from}</code></p>}
        <ResupplyForm batch={batch} onDerived={id => selectBatch(id)} />
        <div className="bf-stats">{batch.departments.map(d => <div className="bf-stat" key={d.department}>
          <b>{d.rows}</b><span>{t(d.department)} · {d.corrections} {t('corrections')} / {d.quarantined} {t('quarantine')}</span>
        </div>)}</div>

        <div className="bf-actions">
          {/* One button, doing the thing. Copy stays as the escape hatch for a
              reviewer who wants to edit the request before sending it. */}
          <button className="bf-primary" disabled={busy} onClick={async () => {
            setError(''); setBusy(true)
            try { await startReview(batch.batch_id, batch.period); close() }
            catch (e) { setError(describeError(e, t)) } finally { setBusy(false) }
          }}>{t(busy ? 'busy' : 'startReview')}</button>
          <button onClick={() => void copy(reviewRequest(batch.batch_id, batch.period), t('copiedRequest'))}>{t('copy')}</button>
          <button onClick={() => setRevision(r => r + 1)}>{t('refresh')}</button>
        </div>
        <p className="bf-hint">{t('startReviewHint')}</p>
        <nav className="bf-tabs" aria-label={t('tabs')}>{sections.map(key => <button key={key} aria-label={t(key)} aria-pressed={section === key} onClick={() => tab(key)}>{t(key)} <span className="bf-badge">{counts[key]}</span></button>)}</nav>
        {section === 'mappings' && <p className="bf-hint">{t('mappingHelp')}</p>}{section === 'columns' && <p className="bf-hint">{t('columnsHelp')}</p>}{section === 'quarantine' && <p className="bf-hint">{t('quarantineHelp')}</p>}
        {section === 'review' ? review ? <BusinessReview report={review} /> : !error && <p role="status" className="bf-loading">{t('loading')}</p> : view ? <>
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
            {view.total > 50 ? <>
              <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 50))}>{t('previous')}</button>
              <button disabled={offset + 50 >= view.total} onClick={() => setOffset(offset + 50)}>{t('next')}</button>
            </> : <span className="bf-hint">{t('allRowsShown')}</span>}
          </div>
        </> : !error && <p role="status" className="bf-loading">{t('loading')}</p>}
      </section>}
      </div>
    </dialog>
  </>
}


/** Correct one department's file, deriving a new batch (E14-UC04).
 *
 * Deliberately not a second import form: the period and the other departments come from the
 * batch being corrected, so the only things to say are which department, which file and why.
 */
export function ResupplyForm({ batch, onDerived }: { batch: Summary; onDerived: (batchId: string) => void }) {
  const { t } = useUI()
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [result, setResult] = useState<Resupply | null>(null)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(''); setResult(null)
    const form = new FormData(event.currentTarget), body = new FormData()
    const file = form.get('file')
    if (!(file instanceof File) || !file.size || !/\.(csv|xlsx)$/i.test(file.name)) { setError(t('invalidUpload')); return }
    body.set('period', batch.period); body.set('reason', String(form.get('reason') ?? ''))
    body.set('file', file); body.set('sheet', String(form.get('sheet') ?? '')); body.set('header_row', String(form.get('header_row') ?? ''))
    setBusy(true)
    try {
      const derived = await api<Resupply>(`/batches/${batch.batch_id}/departments/${String(form.get('department'))}`, { method: 'POST', body })
      setResult(derived)
      onDerived(derived.batch.batch_id)
    } catch (e) { setError(describeError(e, t)) } finally { setBusy(false) }
  }
  return <details className="bf-resupply">
    <summary>{t('resupply')}</summary>
    <p className="bf-hint">{t('resupplyHelp')}</p>
    <form onSubmit={submit}>
      <label>{t('resupplyDepartment')} <select name="department" defaultValue={batch.departments[0]?.department}>
        {batch.departments.map(d => <option key={d.department} value={d.department}>{t(d.department)}</option>)}
      </select></label>
      <label>{t('resupplyReason')} <input name="reason" required maxLength={300} /></label>
      <label>{t('file')} <input type="file" name="file" accept=".csv,.xlsx" required /></label>
      <details className="bf-hint"><summary>{t('sheetLayout')}</summary>
        <input name="sheet" placeholder={t('sheetName')} aria-label={t('sheetName')} />
        <input name="header_row" type="number" min={1} placeholder={t('headerRow')} aria-label={t('headerRow')} />
      </details>
      {error && <p role="alert" className="bf-error">{error}</p>}
      <button className="bf-primary" type="submit" disabled={busy}>{t(busy ? 'busy' : 'resupply')}</button>
    </form>
    {result && <div className="bf-callout" data-tone="ok" role="status">
      <h3>{t('resupplyDone')} · <code className="bf-mono">{result.batch.batch_id}</code></h3>
      <p>{t('resupplyDiff')}：{result.diff.cells_changed} {t('resupplyChangedCells')}
        {result.diff.fields_changed.length ? ` · ${t('resupplyChangedFields')} ${result.diff.fields_changed.join('、')}` : ''}
        {` · ${t('resupplyRows')} ${result.diff.rows_before} → ${result.diff.rows_after}`}</p>
      {Object.keys(result.diff.issues_delta).length > 0 && <p className="bf-hint">{t('resupplyIssues')}：{
        Object.entries(result.diff.issues_delta).map(([kind, delta]) => `${t(`issue_${kind}`)} ${delta > 0 ? '+' : ''}${delta}`).join(' · ')}</p>}
      <p className="bf-hint">{result.next_step}</p>
    </div>}
  </details>
}
type Resupply = { batch: Summary; replaced: string; reason: string; previous_batch: string; next_step: string
  diff: { rows_before: number; rows_after: number; rows_added: number; rows_removed: number
    cells_changed: number; fields_changed: string[]; issues_delta: Record<string, number> } }
