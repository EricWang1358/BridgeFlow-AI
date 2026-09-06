import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react'
import type { Context } from '@deepseek-ai/cordis'
import type { ISessions, SessionEventWindow } from '@deepseek-ai/dsh-api-session-controller/client'
import { api, navigate, route, startReview, useUI, type Summary } from './ui.ts'
import { ImportForm, Chip } from './workspace.tsx'
import { Quotation } from './quotation.tsx'
import { BusinessReview, type Review } from './review.tsx'
import { projectAudit, type AuditEvent } from './audit.ts'
import { QuotationProgress } from './quotation-progress.tsx'
import { useNotebook } from './notebook-session.tsx'
import { PanelResizers, useNativeSidebar } from './shell-layout.tsx'
import { shellStyle } from './shell-style.ts'

type Source = { id: string; filename: string; sheet: string; preview_available: boolean; total?: number; sha256?: string }
type Artifact = { report_id: string; period: string; status: string; created_at: number }
type Preview = { filename: string; sheet: string; sha256: string; columns: string[]; rows: unknown[][]; total: number; offset: number }
const emptyWindow: SessionEventWindow = { entries: [], hasMore: false, revision: 0, change: { kind: 'replace', entries: [] } }
const viewportSubscribe = (fn: () => void) => { window.addEventListener('resize', fn); return () => window.removeEventListener('resize', fn) }
const hashSubscribe = (fn: () => void) => { window.addEventListener('hashchange', fn); return () => window.removeEventListener('hashchange', fn) }

function Shell({ ctx }: { ctx: Context }) {
  const { t } = useUI(), sessions = ctx.sessions as unknown as ISessions
  const session = useSyncExternalStore(fn => sessions.list.subscribe(fn), () => sessions.list.getSnapshot().current)
  const binding = session ? sessions.binding(session) : undefined
  const events = useSyncExternalStore<SessionEventWindow>(fn => binding?.eventSource.subscribe(fn) ?? (() => {}), () => binding?.eventSource.getSnapshot() ?? emptyWindow)
  const audit = useMemo(() => projectAudit(events.entries.filter(e => e.type === 'event').map(e => e.event) as AuditEvent[]), [events])
  const hash = useSyncExternalStore(hashSubscribe, () => location.hash)
  const selected = useMemo(() => route(), [hash])
  const batchId = selected.batch || String(audit.review?.batch_id ?? '')
  const [summary, setSummary] = useState<Summary | null>(null), [sources, setSources] = useState<Source[]>([])
  const [artifacts, setArtifacts] = useState<Artifact[]>([]), [artifactTotal, setArtifactTotal] = useState(0), [artifactOffset, setArtifactOffset] = useState(0)
  const [error, setError] = useState(''), [revision, setRevision] = useState(0), [busy, setBusy] = useState(false)
  const [preview, setPreview] = useState<Preview | null>(null), [report, setReport] = useState<Review | null>(null), [offset, setOffset] = useState(0)
  const [panel, setPanel] = useState(''), [copied, setCopied] = useState(false)
  const navigation = useNativeSidebar(ctx), notebook = useNotebook(ctx, selected, batchId)
  const showState = selected.view === 'state'
  const [expanded, setExpanded] = useState(false)
  const [hiddenSources, setHiddenSources] = useState(false), [hiddenStudio, setHiddenStudio] = useState(false)
  const viewport = useSyncExternalStore(viewportSubscribe, () => window.innerWidth)
  useEffect(() => {
    document.body.toggleAttribute('data-bf-hide-sources', hiddenSources && viewport > 760)
    document.body.toggleAttribute('data-bf-hide-studio', hiddenStudio && viewport > 1100)
    return () => { document.body.removeAttribute('data-bf-hide-sources'); document.body.removeAttribute('data-bf-hide-studio') }
  }, [hiddenSources, hiddenStudio, viewport])
  const importer = useRef<HTMLDialogElement>(null), viewer = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    document.body.toggleAttribute('data-bf-nav', navigation.open)
    const escape = (e: KeyboardEvent) => { if (e.key === 'Escape') { navigation.close(); setPanel('') } }
    window.addEventListener('keydown', escape)
    return () => { document.body.removeAttribute('data-bf-nav'); window.removeEventListener('keydown', escape) }
  }, [navigation.open])
  useEffect(() => {
    const open = () => importer.current?.showModal()
    window.addEventListener('bridgeflow:add-sources', open)
    return () => window.removeEventListener('bridgeflow:add-sources', open)
  }, [])
  useEffect(() => { setOffset(0); setPreview(null); setReport(null); }, [batchId, selected.source, selected.report])
  useEffect(() => { setArtifactOffset(0); setCopied(false) }, [batchId])
  useEffect(() => {
    setSummary(null); setSources([]); setArtifacts([]); setArtifactTotal(0); setError('')
    if (!batchId) return
    const controller = new AbortController(), signal = controller.signal
    void Promise.all([
      api<Summary>(`/batches/${batchId}`, { signal }),
      api<{ sources: Source[] }>(`/batches/${batchId}/sources`, { signal }),
      api<{ artifacts: Artifact[]; total: number }>(`/batches/${batchId}/artifacts?offset=${artifactOffset}`, { signal }),
    ]).then(([batch, files, outputs]) => { setSummary(batch); setSources(files.sources); setArtifacts(outputs.artifacts); setArtifactTotal(outputs.total) })
      .catch(e => { if (!signal.aborted) setError(String(e)) })
    return () => controller.abort()
  }, [batchId, revision, audit.review?.status, audit.review?.report_id, artifactOffset])
  useEffect(() => {
    setPreview(null); setReport(null); setError('')
    if (!batchId) return
    const controller = new AbortController(), signal = controller.signal
    const task = selected.view === 'source' && selected.source
      ? api<Preview>(`/batches/${batchId}/sources/${encodeURIComponent(selected.source)}?offset=${offset}`, { signal }).then(setPreview)
      : selected.view === 'artifact' && selected.report
        ? api<Review>(`/batches/${batchId}/review?report_id=${encodeURIComponent(selected.report)}`, { signal }).then(setReport) : undefined
    void task?.catch(e => { if (!signal.aborted) setError(String(e)) })
    return () => controller.abort()
  }, [batchId, selected.source, selected.report, selected.view, offset, revision])
  const viewing = ['quotation', 'source', 'artifact'].includes(selected.view ?? '')
  useEffect(() => { if (viewing) { setPanel('studio'); setHiddenStudio(false); ctx.layout.closeDetails() } else viewer.current?.close() }, [viewing, selected.source, selected.report, selected.view, ctx])
  const openSource = (source: Source) => { setError(''); navigate({ batch: batchId, view: 'source', source: source.id }) }
  const closePreview = () => { viewer.current?.close(); navigate({ ...(batchId ? { batch: batchId } : {}), kind:notebook.kind, view: 'state' }) }
  const previewContent = selected.view === 'quotation' ? <Quotation /> : preview ? <section aria-label={t('sourcePreview')}>
    <h3>{preview.filename}</h3><p className="bf-hint">{t('parsedOriginal')} {preview.sheet}</p>
    <div className="bf-source-table"><table><thead><tr><th>{t('sourceRow')}</th>{preview.columns.map((c, i) => <th key={i}>{c}</th>)}</tr></thead>
      <tbody>{preview.rows.map((row, i) => <tr key={preview.offset + i}><th>{preview.offset + i + 2}</th>{row.map((cell, j) => <td key={j}>{cell === null ? '—' : String(cell)}</td>)}</tr>)}</tbody></table></div>
    {preview.total > 50 ? <nav className="bf-actions" aria-label={t('sourcePagination')}>
      <button disabled={preview.offset === 0} onClick={() => setOffset(Math.max(0, preview.offset - 50))}>{t('previous')}</button>
      <span role="status">{t('pageLabel')} {Math.floor(preview.offset / 50) + 1} / {Math.ceil(preview.total / 50)} · {preview.offset + 1}–{preview.offset + preview.rows.length} / {preview.total} {t('rows')}</span>
      <button disabled={preview.offset + preview.rows.length >= preview.total} onClick={() => setOffset(preview.offset + 50)}>{t('next')}</button>
    </nav> : <p className="bf-hint" role="status">{t('allRowsShown')} · {preview.total} {t('rows')}</p>}
    <details className="bf-source-provenance"><summary>{t('sourceDetails')}</summary>
      <dl><dt>{t('sourceFilename')}</dt><dd>{preview.filename}</dd><dt>{t('batchId')}</dt><dd><code>{batchId}</code></dd>
        {preview.sheet && <><dt>{t('sourceSheet')}</dt><dd>{preview.sheet}</dd></>}
        <dt>{t('sourceFingerprint')}</dt><dd><code>{preview.sha256}</code></dd></dl>
      <p className="bf-hint">{t('sourceFingerprintHelp')}</p>
    </details>
  </section> : report ? <BusinessReview key={report.report_id} report={report} /> : <p role="status">{t(error || !batchId || selected.view === 'source' && !selected.source || selected.view === 'artifact' && !selected.report ? 'previewUnavailable' : 'loading')}</p>
  return <>
    <header className="bf-shell-top"><div className="bf-shell-brand"><span aria-hidden="true">B</span><strong>BridgeFlow</strong>
      <input className="bf-notebook-title" aria-label={t('notebookName')} value={notebook.title} placeholder={t('untitledNotebook')} maxLength={120} disabled={!session || !notebook.loaded} onChange={e=>notebook.setTitle(e.target.value)}/>
      {session && notebook.loaded && <span className="bf-save-state" role="status" data-dirty={notebook.dirty}>{t(notebook.dirty?'unsavedNotebook':notebook.persisted?'savedNotebook':'draftNotebook')}</span>}
    </div>
      <nav aria-label={t('notebooks')}>
        <button disabled={notebook.busy || !notebook.loaded} onClick={notebook.create}>{t('newNotebook')}</button>
        <button disabled={notebook.busy || !session || !notebook.loaded || !notebook.title.trim()} onClick={notebook.save}>{t('saveNotebook')}</button>
        <button disabled={notebook.busy} onClick={notebook.openHistory}>{t('notebooks')}</button>
        <button disabled={notebook.busy || !session || !notebook.loaded} onClick={notebook.exit}>{t('exitNotebook')}</button>
        <button aria-expanded={viewport > 760 ? !hiddenSources : panel === 'sources'} onClick={() => viewport > 760 ? setHiddenSources(!hiddenSources) : setPanel(panel === 'sources' ? '' : 'sources')}>{t('sources')}</button>
        <button aria-expanded={viewport > 1100 ? !hiddenStudio : panel === 'studio'} onClick={() => viewport > 1100 ? setHiddenStudio(!hiddenStudio) : setPanel(panel === 'studio' ? '' : 'studio')}>{t('studio')}</button>
        <button aria-expanded={navigation.open} onClick={navigation.toggle}>{t('sessionsSettings')}</button>
      </nav>
    </header>
    <PanelResizers hiddenSources={hiddenSources} hiddenStudio={hiddenStudio}/>
    {notebook.dialogs}
    <aside className="bf-shell-pane bf-shell-sources bf-state" data-mobile-open={panel === 'sources'} aria-label={t('sources')}>
      <header><h2>{t('sources')}</h2><button className="bf-mobile-close" onClick={() => setPanel('')}>{t('close')}</button></header>
      <div className="bf-shell-scroll"><label className="bf-notebook-purpose">{t('notebookKind')}<select disabled={notebook.busy || !notebook.loaded} value={notebook.kind} onChange={e=>notebook.setKind(e.target.value as 'monthly'|'quotation'|'mixed')}><option value="mixed">{t('mixedNotebook')}</option><option value="monthly">{t('monthlyNotebook')}</option><option value="quotation">{t('quotationNotebook')}</option></select></label><p className="bf-hint">{t('notebookPurposeHelp')}</p><button className="bf-add-source" onClick={() => importer.current?.showModal()}>＋ {t('addSources')}</button>
        <p className="bf-hint">{t('sourceUploadHelp')}</p>{summary?.demo_case && <p className="bf-sample-notice">{t('sampleNotebookTitle')} · {t('sampleNotebookHelp')}</p>}
        {summary && <div className="bf-source-batch"><span>{summary.period}</span><Chip status={summary.status}/><button title={batchId} onClick={() => void navigator.clipboard.writeText(batchId).then(() => setCopied(true)).catch(e => setError(String(e)))}>{t(copied ? 'copied' : 'copyId')}</button><code>{batchId}</code></div>}
        <ul className="bf-resource-list">{sources.map(source => <li key={source.id}><button aria-pressed={selected.source === source.id && selected.view === 'source'} onClick={() => openSource(source)} disabled={!source.preview_available}>
          <span className="bf-file-icon" aria-hidden="true">▤</span><span><strong>{source.filename}</strong><small>{t(source.id)} · {source.preview_available ? `${source.total} ${t('rows')}` : t('originalUnavailable')}</small></span><span aria-hidden="true">↗</span>
        </button></li>)}</ul>
        {!sources.length && <div className="bf-shell-empty"><span aria-hidden="true">▤</span><strong>{t('emptySources')}</strong><p>{t('emptySourcesHelp')}</p><button disabled={notebook.busy || !notebook.loaded} onClick={notebook.sample}>{t('sampleNotebook')}</button><p>{t('sampleNotebookHelp')}</p></div>}
        <details className="bf-existing"><summary>{t('existing')}</summary><form onSubmit={e => { e.preventDefault(); const form = new FormData(e.currentTarget); navigate({ batch: String(form.get('batch')), view: 'state' }) }}><input name="batch" aria-label={t('batchId')} pattern="[a-f0-9]{32}" required/><button>{t('open')}</button></form></details>
      </div>
    </aside>
    <aside className="bf-shell-pane bf-shell-studio bf-state" data-mobile-open={panel === 'studio'} aria-label={t('studio')}>
      <header><h2>{t('studio')}</h2><button className="bf-mobile-close" onClick={() => setPanel('')}>{t('close')}</button></header>
      <div className="bf-shell-scroll">
        <div className="bf-studio-tools" aria-label={t('tools')}>
          <button data-tone="blue" disabled={!summary || busy} onClick={async () => { if (!summary) return; setBusy(true); setError(''); try { await startReview(batchId, summary.period) } catch (e) { setError(String(e)) } finally { setBusy(false) } }}><span aria-hidden="true">◈</span>{t('startReview')}<span aria-hidden="true">›</span></button>
          <button data-tone="gold" aria-pressed={selected.view === 'quotation'} onClick={() => navigate({ ...(batchId ? { batch: batchId } : {}), view: 'quotation' })}><span aria-hidden="true">▧</span>{t('quotationWorkspace')}<span aria-hidden="true">›</span></button>
          <button data-tone="green" aria-pressed={selected.view === 'master'} disabled={!summary} onClick={() => navigate({ batch: batchId, view: 'master' })}><span aria-hidden="true">▦</span>{t('master')}<span aria-hidden="true">›</span></button>
          <button data-tone="pink" aria-pressed={showState && !viewing} onClick={() => { closePreview(); setHiddenStudio(false); setPanel('studio') }}><span aria-hidden="true">◷</span>{t('state')}<span aria-hidden="true">›</span></button>
        </div>
        {!summary && <p className="bf-hint">{t('studioStartHelp')}</p>}
        {(error || notebook.error) && <p role="alert" className="bf-error">{error || notebook.error}{notebook.error && <button onClick={notebook.retry}>{t('refresh')}</button>}</p>}
        <section className="bf-artifacts" aria-label={t('artifacts')}><header><h3>{t('artifacts')} <span className="bf-badge">{artifactTotal + (summary?.master_rows ? 1 : 0)}</span></h3><button aria-label={t('refreshArtifacts')} onClick={() => setRevision(n => n + 1)}>↻</button></header>
          {!!summary?.master_rows && <button className="bf-artifact" data-kind="master" onClick={() => navigate({ batch: batchId, view: 'master' })}><span aria-hidden="true">▦</span><span><strong>{summary.period} · {t('master')}</strong><small>{summary.master_rows} {t('rows')}</small><Chip status={summary.status}/></span><span aria-hidden="true">↗</span></button>}
          {artifacts.map(item => <button className="bf-artifact" data-kind="review" key={item.report_id} aria-pressed={selected.report === item.report_id} onClick={() => navigate({ batch: batchId, view: 'artifact', report: item.report_id })}><span aria-hidden="true">▤</span><span><strong>{item.period} · {t('review')}</strong><small>{new Date(item.created_at * 1000).toLocaleString()}</small><Chip status={item.status}/></span><span aria-hidden="true">↗</span></button>)}
          {!artifacts.length && !summary?.master_rows && <p className="bf-hint">{t('emptyArtifacts')}</p>}
          {artifactTotal > 50 && <div className="bf-actions"><button disabled={!artifactOffset} onClick={() => setArtifactOffset(Math.max(0, artifactOffset - 50))}>{t('previous')}</button><button disabled={artifactOffset + artifacts.length >= artifactTotal} onClick={() => setArtifactOffset(artifactOffset + 50)}>{t('next')}</button></div>}
        </section>
        {viewing && <section className="bf-inline-preview" aria-label={t('preview')}><header><h3>{t('preview')}</h3><button onClick={() => { setExpanded(true); viewer.current?.showModal() }}>{t('expandPreview')}</button><button onClick={closePreview}>{t('close')}</button></header>{previewContent}</section>}
        {!viewing && showState && <section className="bf-studio-state" aria-label={t('state')}><header><h3>{t('state')}</h3><button onClick={()=>navigate(batchId?{batch:batchId}:{})}>{t('close')}</button></header><p className="bf-hint">{t('studioStateHelp')}</p>{notebook.kind !== 'monthly' && <QuotationProgress/>}{notebook.kind !== 'quotation' && <div className="bf-state-map" aria-label={t('monthlyProgress')}>
          <section><h3>{t('import')}</h3>{summary ? <Chip status={summary.status}/> : <p>{t('emptySourcesHelp')}</p>}</section>
          <section><h3>{t('review')}</h3><Chip status={audit.review?.batch_id === batchId ? String(audit.review.status) : artifacts[0]?.status ?? 'notStarted'}/></section>
          <section><h3>{t('approval')}</h3>{audit.approvals.length ? audit.approvals.map(a => <div key={a.id}><Chip status={a.outcome}/>{a.note && <p>{a.note}</p>}</div>) : <p>{t('noPendingApproval')}</p>}</section>
        </div>}</section>}
      </div>
    </aside>
    <dialog className="bf-panel bf-source-import" aria-label={t('addSources')} ref={importer}><header className="bf-panel-head"><h2>{t('addSources')}</h2><button onClick={() => importer.current?.close()}>{t('close')}</button></header><div className="bf-panel-body"><ImportForm onSaved={batch => { importer.current?.close(); navigate({ batch: batch.batch_id, view: 'state' }); setRevision(n => n + 1) }}/></div></dialog>
    <dialog className="bf-panel bf-expanded-preview" aria-label={t('preview')} ref={viewer} onClose={() => setExpanded(false)}><header className="bf-panel-head"><h2>{t('preview')}</h2><button onClick={() => viewer.current?.close()}>{t('close')}</button></header><div className="bf-panel-body">{viewing && expanded && previewContent}</div></dialog>
  </>
}

export function mountShell(ctx: Context) {
  ctx.effect(() => { const tag = document.createElement('style'); tag.textContent = shellStyle; document.head.append(tag); document.body.setAttribute('data-bf-notebook', ''); return () => { tag.remove(); document.body.removeAttribute('data-bf-notebook') } }, 'bridgeflow: notebook skin')
  ctx.slots.inject('shell.overlay', () => ctx.slots.register({ name: 'shell.overlay', id: 'bridgeflow-notebook' }, () => <Shell ctx={ctx}/>))
}
