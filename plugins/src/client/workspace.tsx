import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Failure } from './failure.tsx'
import { BusinessReview, type Review } from './review.tsx'
import { api, cellText, columnLabel, formatNumber, navigate, route, reviewRequest, startDiagnosis, startReview, useUI, type Summary } from './ui.ts'
export const departments = ['production', 'procurement', 'finance', 'marketing'] as const
export const sections = ['master', 'corrections', 'mappings', 'columns', 'quarantine', 'review'] as const
export function Chip({ status }: { status: string }) { const { t } = useUI(); return <span className="bf-chip" data-status={status}>{t(status.replaceAll('-', '_'))}</span> }
export type Limits = { maxUploadBytes: number; maxBatchRows: number; maxRequestBytes: number; noteLimit: number; decisionTimeoutMs: number }
type Finding = { check: string; message: string; row: number | null; column: string; count: number }
type CheckReport = { department: string; filename: string; must_fix: Finding[]; review: Finding[]; passed: string[]; accepts: boolean }
export function ImportForm({ onSaved }: { onSaved: (batch: Summary) => void }) {
  const { t, language } = useUI()
  const [limits, setLimits] = useState<Limits | null>(null)
  const [busy, setBusy] = useState(false), [error, setError] = useState<unknown>(''), [reports, setReports] = useState<CheckReport[]>([])
  const [checking, setChecking] = useState('')
  const formRef = useRef<HTMLFormElement>(null)
  useEffect(() => { const controller = new AbortController(); void api<Limits>('/config', { signal: controller.signal }).then(setLimits).catch(e => { if (!controller.signal.aborted) setError(e) }); return () => controller.abort() }, [])
  async function selfCheck() {
    if (!formRef.current) return
    const form = new FormData(formRef.current)
    setError(''); setReports([])
    if (!form.get('period')) { setError(t('selfCheckNeedsPeriod')); return }
    setBusy(true)
    let checked = 0
    try {
      for (const name of departments) {
        const file = form.get(name)
        if (!(file instanceof File) || !file.size) continue
        const body = new FormData()
        body.set('period', String(form.get('period'))); body.set('department', name); body.set('file', file)
        body.set('sheet', String(form.get(`${name}-sheet`) ?? '')); body.set('header_row', String(form.get(`${name}-header`) ?? ''))
        setChecking(name)
        // Each report lands as it arrives. Collecting them and assigning once meant a
        // failure on the third file discarded the first two — four files reading as
        // four failures is exactly what per-department reporting exists to prevent.
        const report = await api<CheckReport>('/batches/self-check', { method: 'POST', body })
        checked++; setReports(previous => [...previous, report])
      }
      if (!checked) setError(t('invalidUpload'))
    } catch (e) { setError(e) } finally { setBusy(false); setChecking('') }
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
    catch (e) { setError(e) } finally { setBusy(false) }
  }
  return <>
    <form ref={formRef} onSubmit={upload} className="bf-steps">
      <div className="bf-step">
        <h3>{t('stepMonth')}</h3>
        <input type="month" name="period" aria-label={t('month')} required />
      </div>
      <div className="bf-step">
        <h3>{t('stepFiles')}</h3>
        <p className="bf-hint">{t('stepFilesHint')} {t('uploadHelp')}</p>
        <div className="bf-files">{departments.map(name => <FileRow key={name} name={name} />)}</div>
      </div>
      {/* I01 step 3: both ways forward on one row, the limits beside the button that
          enforces them, and the self-check's own result directly underneath. The check
          used to sit in step 2, which made "add the files" mean two different jobs. */}
      <div className="bf-step">
        <h3>{t('stepGo')}</h3>
        <p className="bf-hint">{t('stepGoHint')}</p>
        <Failure value={error}/>
        <div className="bf-actions" style={{ marginBottom: 0 }}>
          <button className="bf-primary" disabled={busy || !limits} type="submit">{t(busy ? 'busy' : 'import')}</button>
          <button type="button" disabled={busy} onClick={() => void selfCheck()}>{t('selfCheck')}</button>
          <span className="bf-hint">{limits
            ? `${t('perUpload')} ${limits.maxUploadBytes / 1048576} MiB · ${t('perBatch')} ${formatNumber(limits.maxBatchRows, language)} ${t('rows')}`
            : t('loading')}</span>
        </div>
        <p className="bf-hint" style={{ marginTop: 6 }}>{t('selfCheckHelp')}</p>
      </div>
    </form>
    {/* `checking` is set only by self-check, so a plain import never opens this panel. */}
    <SelfCheckResult reports={reports} checking={checking} />
  </>
}

/**
 * I03: what the same rules say about these files, without creating a batch.
 *
 * Grouped by what the reader has to do about it, not by which file it came from.
 * "Must fix" and "worth checking" are two different jobs for the person holding the
 * sheets; four per-department cards left them to do that sort by eye, with the review
 * items folded behind a `<details>` each.
 */
function SelfCheckResult({ reports, checking }: { reports: CheckReport[]; checking: string }) {
  const { t, language } = useUI()
  const lines = (pick: (r: CheckReport) => Finding[]) => reports.flatMap(r => pick(r).map(f => ({ department: r.department, f })))
  const mustFix = lines(r => r.must_fix), review = lines(r => r.review)
  // Not a partition: a file can carry review items and still be submittable, and saying
  // so is the difference the two buckets exist to draw. `accepts` is the backend's own
  // word for "nothing here blocks the import", which is exactly the question.
  const clean = reports.filter(r => r.accepts)
  // `count` is the finding's own multiplicity: one "three unknown columns" finding is
  // three things to look at, and a heading reading "1" would understate the work.
  const weight = (items: typeof mustFix) => items.reduce((n, l) => n + Math.max(1, l.f.count), 0)
  const line = ({ department, f }: { department: string; f: Finding }) => [
    t(department),
    f.row ? `${t('atRow')} ${f.row}${t('atRowSuffix')}` : '',
    f.column && !f.message.startsWith(f.column) ? f.column : '',
    f.message + (f.count > 1 ? ` ×${f.count}` : ''),
  ].filter(Boolean).join(' · ')
  if (!reports.length && !checking) return null
  // One live region for the whole result, not one per bucket: three of them announce
  // over each other, and the reader needs the three counts together anyway.
  return <section className="bf-selfcheck" aria-label={t('selfCheckResult')} aria-live="polite">
    <div className="bf-card-head">
      <h3>{t('selfCheckResult')}</h3>
      {/* The one thing a person needs to know before reading a word of it. */}
      <span className="bf-chip">{t('noBatchCreated')}</span>
    </div>
    {mustFix.length > 0 && <div className="bf-callout" data-tone="danger">
      <h3>{t('selfCheckMustFix')} · {weight(mustFix)}</h3>
      <ul>{mustFix.map((l, i) => <li key={i}>{line(l)}</li>)}</ul>
    </div>}
    {review.length > 0 && <div className="bf-callout" data-tone="warn">
      <h3>{t('selfCheckReview')} · {weight(review)}</h3>
      <ul>{review.map((l, i) => <li key={i}>{line(l)}</li>)}</ul>
    </div>}
    {/* Counted in files, not findings — which is what the sentence under it says. */}
    {clean.length > 0 && <div className="bf-callout" data-tone="ok">
      <h3>{t('selfCheckAccepted')} · {clean.length}</h3>
      <p>{clean.map(r => t(r.department)).join(language === 'zh' ? '、' : ', ')} {t('selfCheckPassedAll')}</p>
    </div>}
    {checking && <p className="bf-hint">{t('selfCheckRunning')} · {t(checking)}</p>}
    {mustFix.length > 0 && <p className="bf-hint">{t('selfCheckQuarantineHint')}</p>}
  </section>
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
  {/* I02, collapsed by default: most workbooks never need it, and the person whose
      header sits on row 3 is otherwise left editing the file into a shape the system
      likes. Two placeholder-only inputs said neither what they were nor what they did. */}
  {/\.xlsx$/i.test(chosen) && <details className="bf-layout">
    <summary>{t('sheetLayout')}</summary>
    <div className="bf-field-grid">
      <label className="bf-field"><span>{t('sheetName')}</span>
        <input name={`${name}-sheet`} aria-label={`${t(name)} · ${t('sheetName')}`} /></label>
      <label className="bf-field"><span>{t('headerRow')}</span>
        <input name={`${name}-header`} type="number" min={1} aria-label={`${t(name)} · ${t('headerRow')}`} /></label>
    </div>
    <p className="bf-hint">{t('sheetLayoutHint')}</p>
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
  const { t, language } = useUI(), dialog = useRef<HTMLDialogElement>(null)
  const [batch, setBatch] = useState<Summary | null>(null), [batchId, setBatchId] = useState('')
  const [section, setSection] = useState('master'), [offset, setOffset] = useState(0)
  const [view, setView] = useState<View | null>(null), [review, setReview] = useState<Review | null>(null)
  const [reportId, setReportId] = useState(''), [revision, setRevision] = useState(0)
  const [error, setError] = useState<unknown>(''), [busy, setBusy] = useState(false), [notice, setNotice] = useState('')
  // Separate from `notice`, which is a transient confirmation. "No model was called"
  // is a claim about how this batch was produced and belongs on the batch (I04).
  const [justSaved, setJustSaved] = useState(false)
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
      setNotice(''); setJustSaved(false); setBatch(null); setView(null); setReview(null); setBusy(true)
      void api<Summary>(`/batches/${value.batch}`, { signal }).then(result => { if (!signal.aborted) setBatch(result) }).catch(e => { if (!signal.aborted) setError(e) }).finally(() => { if (!signal.aborted) setBusy(false) })
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
        .catch(e => { if (!abort.signal.aborted) setError(String(e).includes('no saved review') ? t('noReport') : e) })
    } else void api<View>(`/batches/${batch.batch_id}/view?section=${section}&offset=${offset}`, { signal: abort.signal }).then(setView).catch(e => { if (!abort.signal.aborted) setError(e) })
    return () => abort.abort()
  }, [batch, section, offset, reportId, revision])
  async function copy(text: string, message: string) { try { await navigator.clipboard.writeText(text); setNotice(message) } catch (e) { setError(e) } }
  const columns = Array.from(new Set(view?.rows.flatMap(row => Object.keys(row)) ?? []))
  const totals = {
    corrections: batch?.departments.reduce((n, d) => n + d.corrections, 0) ?? 0,
    quarantined: batch?.departments.reduce((n, d) => n + d.quarantined, 0) ?? 0,
  }
  const counts: Record<string, number | string> = batch ? { master: batch.master_rows, mappings: batch.unresolved,
    corrections: totals.corrections, columns: batch.column_questions ?? 0, quarantine: totals.quarantined, review: review ? `${review.roles.filter(r => r.status === 'validated').length}/4` : '—' } : {}
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
      <details open={!batch}><summary>{t('newBatch')}</summary><ImportForm onSaved={result => { pendingBatch.current?.abort(); setReportId(''); setView(null); setReview(null); currentBatch.current = result; setBatch(result); setBatchId(result.batch_id); setOffset(0); setSection('master'); setNotice(''); setJustSaved(true); selectBatch(result.batch_id) }} /></details>
      <details><summary>{t('existing')}</summary><label>{t('batchId')} <input value={batchId} onChange={e => setBatchId(e.target.value)} /></label>
        <button disabled={busy || !/^[a-f0-9]{32}$/.test(batchId)} onClick={() => selectBatch(batchId)}>{t('open')}</button></details>
      <p role="status">{notice}</p><Failure value={error}/>
      {batch && <section>
        {/* I04: the first thing said after an import finishes is what the rules did and
            did not do. As a one-line `role=status` it was gone before it was read. */}
        {justSaved && <div className="bf-callout" data-tone="ok">
          <h3>{t('batchSaved')}</h3><p>{t('rulesOnly')}</p>
        </div>}
        <div className="bf-band">
          <span className="bf-period">{batch.period}</span> <Chip status={batch.status} />
        </div>

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
                catch (e) { setError(e) } finally { setBusy(false) }
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

        {batch.derived_from && <p className="bf-hint">{t('derivedFrom')}: <code className="bf-mono">{batch.derived_from}</code></p>}
        {/* I04 per department, "because one failed file should not read as four". The
            batch totals are deliberately not repeated here: the tabs below already carry
            every one of them, next to the rows they count. */}
        <dl className="bf-metrics">{batch.departments.map(d => <div className="bf-metric" key={d.department}>
          <dt>{t(d.department)}</dt>
          <dd><b>{formatNumber(d.rows, language)}</b> <small>{t('rows')}</small>
            <small className="bf-metric-note">{d.corrections} {t('corrections')} · {d.quarantined} {t('quarantine')}</small></dd>
        </div>)}</dl>

        <div className="bf-actions">
          {/* One button, doing the thing. Copy stays as the escape hatch for a
              reviewer who wants to edit the request before sending it. */}
          <button className="bf-primary" disabled={busy} onClick={async () => {
            setError(''); setBusy(true)
            try { await startReview(batch.batch_id, batch.period); close() }
            catch (e) { setError(e) } finally { setBusy(false) }
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
