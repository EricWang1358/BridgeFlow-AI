import { Discovery } from './discovery.tsx'
import { TourDriver, TourHelpButton, TourLayer } from './tour/tour.tsx'
import { tourEvent } from './tour/state.ts'
import { notebookKinds, notebookPurposes, isNotebookKind } from '../notebook-capabilities.ts'
import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react'
import type { Context } from '@deepseek-ai/cordis'
import type { ISessions, SessionEventWindow } from '@deepseek-ai/dsh-api-session-controller/client'
import { api, formatDateTime, navigate, portalLoginUrl, route, startReview, takeRouteError, useUI, type Summary, describeError } from './ui.ts'
import { ImportForm, Chip } from './workspace.tsx'
import { TasksView } from './tasks.tsx'
import { DataView } from './data.tsx'
import { RecordsView } from './records.tsx'
import { FeishuImport, FeishuUpload, WikiFileUpload } from './feishu-picker.tsx'
import { Quotation } from './quotation.tsx'
import { Handoff } from './handoff.tsx'
import { MasterTable } from './master.tsx'
import { MonthlyBrief } from './brief.tsx'
import { BusinessReview, type Review } from './review.tsx'
import { projectAudit, type AuditEvent } from './audit.ts'
import { useNotebook } from './notebook-session.tsx'
import { PanelResizers, useNativeSidebar } from './shell-layout.tsx'
import { shellStyle } from './shell-style.ts'

type Source = { id: string; filename: string; sheet: string; preview_available: boolean; total?: number; sha256?: string }
type Artifact = { report_id: string; period: string; status: string; created_at: number; kind?: string }
type Preview = { filename: string; sheet: string; sha256: string; columns: string[]; rows: unknown[][]; row_numbers?: number[]; total: number; offset: number }
const emptyWindow: SessionEventWindow = { entries: [], hasMore: false, revision: 0, change: { kind: 'replace', entries: [] } }
const viewportSubscribe = (fn: () => void) => { window.addEventListener('resize', fn); return () => window.removeEventListener('resize', fn) }
const hashSubscribe = (fn: () => void) => { window.addEventListener('hashchange', fn); return () => window.removeEventListener('hashchange', fn) }

function Shell({ ctx }: { ctx: Context }) {
  const { t, language } = useUI(), sessions = ctx.sessions as unknown as ISessions
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
  const [expanded, setExpanded] = useState(false)
  const [hiddenSources, setHiddenSources] = useState(false), [hiddenStudio, setHiddenStudio] = useState(false)
  const viewport = useSyncExternalStore(viewportSubscribe, () => window.innerWidth)
  useEffect(() => {
    document.body.toggleAttribute('data-bf-hide-sources', hiddenSources && viewport > 760)
    document.body.toggleAttribute('data-bf-hide-studio', hiddenStudio && viewport > 1100)
    return () => { document.body.removeAttribute('data-bf-hide-sources'); document.body.removeAttribute('data-bf-hide-studio') }
  }, [hiddenSources, hiddenStudio, viewport])
  const importer = useRef<HTMLDialogElement>(null), viewer = useRef<HTMLDialogElement>(null), feishuUploader = useRef<HTMLDialogElement>(null)
  const [feishuNotice, setFeishuNotice] = useState('')
  // One count for the tasks destination, read from the same projection its page shows.
  const [openItems, setOpenItems] = useState(0)
  useEffect(() => {
    if (!summary?.period) { setOpenItems(0); return }
    const controller = new AbortController()
    void api<{ total: number }>(`/monthly/inbox?period=${encodeURIComponent(summary.period)}`, { signal: controller.signal })
      .then(value => setOpenItems(value.total)).catch(() => setOpenItems(0))
    return () => controller.abort()
  }, [summary?.period, batchId, revision])
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
  useEffect(() => { setArtifactOffset(0); setCopied(false); setFeishuNotice('') }, [batchId])
  useEffect(() => {
    setSummary(null); setSources([]); setArtifacts([]); setArtifactTotal(0); setError('')
    if (!batchId) return
    const controller = new AbortController(), signal = controller.signal
    void Promise.all([
      api<Summary>(`/batches/${batchId}`, { signal }),
      api<{ sources: Source[] }>(`/batches/${batchId}/sources`, { signal }),
      api<{ artifacts: Artifact[]; total: number }>(`/batches/${batchId}/artifacts?offset=${artifactOffset}`, { signal }),
    ]).then(([batch, files, outputs]) => { setSummary(batch); setSources(files.sources); setArtifacts(outputs.artifacts); setArtifactTotal(outputs.total) })
      .catch(e => { if (!signal.aborted) setError(describeError(e, t)) })
    return () => controller.abort()
  }, [batchId, revision, audit.review?.status, audit.review?.report_id, artifactOffset])
  useEffect(() => {
    setPreview(null); setReport(null); setError('')
    if (!batchId) return
    const controller = new AbortController(), signal = controller.signal
    const task = selected.view === 'source' && selected.source
      ? api<Preview>(`/batches/${batchId}/sources/${encodeURIComponent(selected.source)}?offset=${offset}`, { signal }).then(value => { setPreview(value); tourEvent('source', batchId, undefined, selected.source) })
      : selected.view === 'artifact' && selected.report
        ? api<Review>(`/batches/${batchId}/review?report_id=${encodeURIComponent(selected.report)}`, { signal }).then(setReport) : undefined
    void task?.catch(e => { if (!signal.aborted) setError(describeError(e, t)) })
    return () => controller.abort()
  }, [batchId, selected.source, selected.report, selected.view, offset, revision])
  const viewing = ['discovery', 'quotation', 'handoff', 'integration', 'brief', 'source', 'artifact', 'tasks', 'data', 'records'].includes(selected.view ?? '')
  useEffect(() => { if (viewing) { setPanel('studio'); setHiddenStudio(false); ctx.layout.closeDetails() } else viewer.current?.close() }, [viewing, selected.source, selected.report, selected.view, ctx])
  const openSource = (source: Source) => { setError(''); navigate({ batch: batchId, view: 'source', source: source.id }) }
  const closePreview = () => { viewer.current?.close(); navigate({ ...(batchId ? { batch: batchId } : {}), kind:notebook.kind }) }
  const previewContent = selected.view === 'tasks' && batchId
    ? <TasksView batchId={batchId} summary={summary} audit={audit} savedReportStatus={artifacts[0]?.status}
        notebookKind={notebook.kind} onImport={() => importer.current?.showModal()} onRefresh={() => setRevision(n => n + 1)} />
    : selected.view === 'data' && batchId
      ? <DataView batchId={batchId} summary={summary} sources={sources}
          onImport={() => importer.current?.showModal()} onRefresh={() => setRevision(n => n + 1)} />
      : selected.view === 'records' && batchId
        ? <RecordsView batchId={batchId} summary={summary} artifacts={artifacts} language={language} />
        : selected.view === 'discovery' ? <Discovery /> : selected.view === 'quotation' ? <Quotation /> : selected.view === 'handoff' ? <Handoff /> : selected.view === 'integration' && batchId ? <MasterTable batchId={batchId} /> : selected.view === 'brief' && batchId ? <MonthlyBrief batchId={batchId} /> : preview ? <section aria-label={t('sourcePreview')}>
    <h3>{preview.filename}</h3><p className="bf-hint">{t('parsedOriginal')} {preview.sheet}</p>
    <div className="bf-source-table"><table><thead><tr><th>{t('sourceRow')}</th>{preview.columns.map((c, i) => <th key={i}>{c}</th>)}</tr></thead>
      <tbody>{preview.rows.map((row, i) => <tr key={preview.offset + i}><th>{preview.row_numbers?.[i] ?? preview.offset + i + 2}</th>{row.map((cell, j) => <td key={j}>{cell === null ? '—' : String(cell)}</td>)}</tr>)}</tbody></table></div>
    {preview.total > 50 ? <nav className="bf-actions" aria-label={t('sourcePagination')}>
      <button disabled={preview.offset === 0} onClick={() => setOffset(Math.max(0, preview.offset - 50))}>{t('previous')}</button>
      <span role="status">{t('pageLabel')} {Math.floor(preview.offset / 50) + 1} / {Math.ceil(preview.total / 50)} · {preview.offset + 1}–{preview.offset + preview.rows.length} / {preview.total} {t('rows')}</span>
      <button disabled={preview.offset + preview.rows.length >= preview.total} onClick={() => setOffset(preview.offset + 50)}>{t('next')}</button>
    </nav> : <p className="bf-hint" role="status">{t('allRowsShown')} · {preview.total} {t('rows')}</p>}
    <details data-tour-id="source-provenance" className="bf-source-provenance" onToggle={e => { if (e.currentTarget.open) tourEvent('sourceDetails', batchId) }}><summary data-tour-id="source-details">{t('sourceDetails')}</summary>
      <dl><dt>{t('sourceFilename')}</dt><dd>{preview.filename}</dd><dt>{t('batchId')}</dt><dd><code>{batchId}</code></dd>
        {preview.sheet && <><dt>{t('sourceSheet')}</dt><dd>{preview.sheet}</dd></>}
        <dt>{t('sourceFingerprint')}</dt><dd><code>{preview.sha256}</code></dd></dl>
      <p className="bf-hint">{t('sourceFingerprintHelp')}</p>
    </details>
  </section> : report ? <BusinessReview key={report.report_id} report={report} /> : <p role="status">{t(error || !batchId || selected.view === 'source' && !selected.source || selected.view === 'artifact' && !selected.report ? 'previewUnavailable' : 'loading')}</p>
  return <>
    <header className="bf-shell-top"><div className="bf-shell-brand"><span aria-hidden="true">B</span><strong>BridgeFlow</strong>
      <input data-tour-id="notebook-name" onFocus={e => { e.currentTarget.dataset.initialTitle = e.currentTarget.value }} onBlur={e => { if (e.currentTarget.value.trim() && e.currentTarget.value !== e.currentTarget.dataset.initialTitle) tourEvent('named', batchId) }} className="bf-notebook-title" aria-label={t('notebookName')} value={notebook.title} placeholder={t('untitledNotebook')} maxLength={120} disabled={!session || !notebook.loaded} onChange={e=>notebook.setTitle(e.target.value)}/>
      {session && notebook.loaded && <span className="bf-save-state" role="status" data-dirty={notebook.dirty}>{t(notebook.dirty?'unsavedNotebook':notebook.persisted?'savedNotebook':'draftNotebook')}</span>}
    </div>
      <nav aria-label={t('notebooks')}>
        <button disabled={notebook.busy || !notebook.loaded} onClick={notebook.create}>{t('newNotebook')}</button>
        <button data-tour-id="notebook-save" disabled={notebook.busy || !session || !notebook.loaded || !notebook.title.trim()} onClick={notebook.save}>{t('saveNotebook')}</button>
        <button disabled={notebook.busy} onClick={notebook.openHistory}>{t('notebooks')}</button>
        <button disabled={notebook.busy || !session || !notebook.loaded} onClick={notebook.exit}>{t('exitNotebook')}</button>
        <button aria-expanded={viewport > 760 ? !hiddenSources : panel === 'sources'} onClick={() => viewport > 760 ? setHiddenSources(!hiddenSources) : setPanel(panel === 'sources' ? '' : 'sources')}>{t('sources')}</button>
        <button aria-expanded={viewport > 1100 ? !hiddenStudio : panel === 'studio'} onClick={() => viewport > 1100 ? setHiddenStudio(!hiddenStudio) : setPanel(panel === 'studio' ? '' : 'studio')}>{t('studio')}</button>
        <button aria-expanded={navigation.open} onClick={navigation.toggle}>{t('sessionsSettings')}</button>
        <TourHelpButton/>
      </nav>
    </header>
    <TourDriver session={session ?? ''} batch={batchId} sample={summary?.demo_case === 'mock-company-2024-07'} ready={notebook.loaded && !notebook.busy && !notebook.error && !error}
      reveal={pane => { if (pane === 'sources') { setHiddenSources(false); setPanel('sources') } if (pane === 'studio') { setHiddenStudio(false); setPanel('studio') } }}/>
    <TourLayer/>
    <PanelResizers hiddenSources={hiddenSources} hiddenStudio={hiddenStudio}/>
    {notebook.dialogs}
    <aside className="bf-shell-pane bf-shell-sources bf-state" data-mobile-open={panel === 'sources'} aria-label={t('sources')}>
      <header><h2>{t('sources')}</h2><button className="bf-mobile-close" onClick={() => setPanel('')}>{t('close')}</button></header>
      <div className="bf-shell-scroll"><label className="bf-notebook-purpose">{t('notebookKind')}<select disabled={notebook.busy || !notebook.loaded} value={notebook.kind} onChange={e=>{if(isNotebookKind(e.target.value))notebook.setKind(e.target.value)}}>{notebookKinds.map(kind=><option key={kind} value={kind}>{t(notebookPurposes[kind].label)}</option>)}</select></label><p className="bf-hint">{t('notebookPurposeHelp')}</p><button className="bf-add-source" onClick={() => importer.current?.showModal()}>＋ {t('addSources')}</button>
        <p className="bf-hint">{t('sourceUploadHelp')}</p>{summary?.demo_case && <p className="bf-sample-notice">{t('sampleNotebookTitle')} · {t('sampleNotebookHelp')}</p>}
        {summary && <div className="bf-source-batch"><span>{summary.period}</span><Chip status={summary.status}/><button title={batchId} onClick={() => void navigator.clipboard.writeText(batchId).then(() => setCopied(true)).catch(e => setError(describeError(e, t)))}>{t(copied ? 'copied' : 'copyId')}</button><code>{batchId}</code></div>}
        <ul className="bf-resource-list">{sources.map(source => <li key={source.id}><button aria-pressed={selected.source === source.id && selected.view === 'source'} onClick={() => openSource(source)} disabled={!source.preview_available}>
          <span className="bf-file-icon" aria-hidden="true">▤</span><span><strong>{source.filename}</strong><small>{t(source.id)} · {source.preview_available ? `${source.total} ${t('rows')}` : t('originalUnavailable')}</small></span><span aria-hidden="true">↗</span>
        </button></li>)}</ul>
        {!sources.length && <div className="bf-shell-empty"><span aria-hidden="true">▤</span><strong>{t('emptySources')}</strong><p>{t('emptySourcesHelp')}</p><p>{t('sampleNotebookHelp')}</p></div>}
        <button data-tour-id="sample" disabled={notebook.busy || !notebook.loaded} onClick={notebook.sample}>{t('sampleNotebook')}</button>
        <details className="bf-existing"><summary>{t('existing')}</summary><form onSubmit={e => { e.preventDefault(); const form = new FormData(e.currentTarget); navigate({ batch: String(form.get('batch')), view: 'tasks' }) }}><input name="batch" aria-label={t('batchId')} pattern="[a-f0-9]{32}" required/><button>{t('open')}</button></form></details>
      </div>
    </aside>
    <aside className="bf-shell-pane bf-shell-studio bf-state" data-mobile-open={panel === 'studio'} aria-label={t('studio')}>
      <header><h2>{t('studio')}</h2><button className="bf-mobile-close" onClick={() => setPanel('')}>{t('close')}</button></header>
      <div className="bf-shell-scroll">
        <div className="bf-studio-tools" aria-label={t('tools')}>
          {/* Four destinations, named after what a person is doing, not after our modules.
              Everything that used to have two entries now has exactly one, inside one of these. */}
          <button data-tour-id="state-open" data-tone="pink" aria-pressed={selected.view === 'tasks'} disabled={!summary} onClick={() => navigate({ batch: batchId, view: 'tasks' })}><span aria-hidden="true">◷</span>{t('monthlyTasks')}<span className="bf-badge">{openItems}</span><span aria-hidden="true">›</span></button>
          <button data-tone="blue" aria-pressed={selected.view === 'data'} disabled={!summary} onClick={() => navigate({ batch: batchId, view: 'data' })}><span aria-hidden="true">▤</span>{t('dataWorkspace')}<span aria-hidden="true">›</span></button>
          <button data-tone="green" aria-pressed={selected.view === 'brief'} disabled={!summary} onClick={() => navigate({ batch: batchId, view: 'brief' })}><span aria-hidden="true">◎</span>{t('monthlyBrief')}<span aria-hidden="true">›</span></button>
          <button data-tone="teal" aria-pressed={selected.view === 'records'} disabled={!summary} onClick={() => navigate({ batch: batchId, view: 'records' })}><span aria-hidden="true">⇄</span>{t('records')}<span aria-hidden="true">›</span></button>
          <div className="bf-studio-group">{t('otherWorkspaces')}</div>
          <button data-tour-id="quotation-open" data-secondary="true" data-tone="gold" aria-pressed={selected.view === 'quotation'} onClick={() => { navigate({ ...(batchId ? { batch: batchId } : {}), view: 'quotation' }); window.dispatchEvent(new Event('bridgeflow:quotation-opened')) }}><span aria-hidden="true">▧</span>{t('quotationWorkspace')}<span aria-hidden="true">›</span></button>
          <button data-secondary="true" data-tone="teal" aria-pressed={selected.view === 'discovery'} onClick={() => navigate({ view: 'discovery' })}><span aria-hidden="true">▥</span>{t('discoveryWorkspace')}<span aria-hidden="true">›</span></button>
          <button data-secondary="true" data-tone="teal" aria-pressed={selected.view === 'handoff'} onClick={() => navigate({ ...(batchId ? { batch: batchId } : {}), view: 'handoff' })}><span aria-hidden="true">⇄</span>{t('handoffWorkspace')}<span aria-hidden="true">›</span></button>
        </div>
        {!summary && <p className="bf-hint">{t('studioStartHelp')}</p>}
        {(error || notebook.error) && <p role="alert" className="bf-error">{error || notebook.error}{notebook.error && <button onClick={notebook.retry}>{t('refresh')}</button>}</p>}
        {viewing && <section className="bf-inline-preview" aria-label={t('preview')}><header><h3>{t('preview')}</h3><button onClick={() => { setExpanded(true); viewer.current?.showModal() }}>{t('expandPreview')}</button><button onClick={closePreview}>{t('close')}</button></header>{previewContent}</section>}
        <section data-tour-id="artifacts" className="bf-artifacts" aria-label={t('artifacts')}><header><h3>{t('artifacts')} <span className="bf-badge">{artifactTotal + (summary?.master_rows ? 1 : 0)}</span></h3>{artifacts.length > 0 && <button aria-label={t('feishuUpload')} title={t('feishuUpload')} onClick={() => { setFeishuNotice(''); feishuUploader.current?.showModal() }}>⇪</button>}<button aria-label={t('refreshArtifacts')} onClick={() => setRevision(n => n + 1)}>↻</button></header>
          {feishuNotice && <p className="bf-hint" role="status">{feishuNotice}</p>}
          {!!summary?.master_rows && <button className="bf-artifact" data-kind="master" onClick={() => navigate({ batch: batchId, view: 'master' })}><span aria-hidden="true">▦</span><span><strong>{summary.period} · {t('master')}</strong><small>{summary.master_rows} {t('rows')}</small><Chip status={summary.status}/></span><span aria-hidden="true">↗</span></button>}
          {artifacts.map(item => item.kind === 'brief'
            ? <button className="bf-artifact" data-kind="brief" key={`brief-${item.report_id}`} aria-pressed={selected.view === 'brief' && selected.report === item.report_id} onClick={() => navigate({ batch: batchId, view: 'brief', report: item.report_id })}><span aria-hidden="true">◎</span><span><strong>{item.period} · {t('monthlyBrief')}</strong><small>{formatDateTime(item.created_at * 1000, language)}</small><Chip status={item.status}/></span><span aria-hidden="true">↗</span></button>
            : <button className="bf-artifact" data-kind="review" key={item.report_id} aria-pressed={selected.report === item.report_id} onClick={() => navigate({ batch: batchId, view: 'artifact', report: item.report_id })}><span aria-hidden="true">▤</span><span><strong>{item.period} · {t('review')}</strong><small>{formatDateTime(item.created_at * 1000, language)}</small><Chip status={item.status}/></span><span aria-hidden="true">↗</span></button>)}
          {!artifacts.length && !summary?.master_rows && <p className="bf-hint">{t('emptyArtifacts')}</p>}
          {artifactTotal > 50 && <div className="bf-actions"><button disabled={!artifactOffset} onClick={() => setArtifactOffset(Math.max(0, artifactOffset - 50))}>{t('previous')}</button><button disabled={artifactOffset + artifacts.length >= artifactTotal} onClick={() => setArtifactOffset(artifactOffset + 50)}>{t('next')}</button></div>}
        </section>
        {!viewing && summary && <section className="bf-studio-facts" aria-label={t('batchFacts')}>
          <h3>{t('batchFacts')}</h3>
          <p className="bf-hint">{t('batchFactsHint')}</p>
          <dl className="bf-facts">
            <dt>{t('masterCompleteRows')}</dt><dd>{summary.master_rows}</dd>
            <dt>{t('openItems')}</dt><dd>{openItems}</dd>
            <dt>{t('mappings')}</dt><dd>{summary.unresolved}</dd>
            <dt>{t('declarationSource')}</dt><dd><code className="bf-mono">{summary.dictionary}</code></dd>
          </dl>
          {!!summary.superseded_by?.length && <div className="bf-callout" data-tone="warn"><h3>{t('superseded')}</h3><p>{t('supersededHint')}</p>
            <div className="bf-actions" style={{ marginBottom: 0 }}><button onClick={() => navigate({ batch: summary.superseded_by!.at(-1)!, view: 'tasks' })}>{t('openNewest')}</button></div></div>}
        </section>}
      </div>
    </aside>
    <dialog data-tour-surface="import" className="bf-panel bf-source-import" aria-label={t('addSources')} ref={importer}><header className="bf-panel-head"><h2>{t('addSources')}</h2><button onClick={() => importer.current?.close()}>{t('close')}</button></header><div className="bf-panel-body"><ImportForm onSaved={batch => { importer.current?.close(); navigate({ batch: batch.batch_id, view: 'data' }); setRevision(n => n + 1) }}/><details className="bf-feishu"><summary>{t('feishuPick')}</summary><FeishuImport onSaved={batch => { importer.current?.close(); navigate({ batch: batch.batch_id, view: 'data' }); setRevision(n => n + 1) }}/></details><details className="bf-feishu"><summary>{t('feishuUploadFileWiki')}</summary><WikiFileUpload /></details></div><TourLayer surface="import"/></dialog>
    <dialog className="bf-panel bf-feishu-upload-dialog" aria-label={t('feishuUpload')} ref={feishuUploader}><header className="bf-panel-head"><h2>{t('feishuUpload')}</h2><button onClick={() => feishuUploader.current?.close()}>{t('close')}</button></header><div className="bf-panel-body">{batchId && <FeishuUpload batchId={batchId} reportId={selected.report ?? artifacts[0]?.report_id ?? null} onDone={name => { feishuUploader.current?.close(); setFeishuNotice(`${t('feishuUploaded')} · ${name}`) }}/>}</div></dialog>
    <dialog data-tour-surface="viewer" className="bf-panel bf-expanded-preview" aria-label={t('preview')} ref={viewer} onClose={() => setExpanded(false)}><header className="bf-panel-head"><h2>{t('preview')}</h2><button onClick={() => viewer.current?.close()}>{t('close')}</button></header><div className="bf-panel-body">{viewing && expanded && previewContent}</div><TourLayer surface="viewer"/></dialog>
  </>
}

/**
 * A session link that cannot be opened fails visibly (#40), wherever the page is. It is
 * its own overlay so no pane, tab or dialog state can hide or clear it.
 */
function RouteNotice() {
  const { t } = useUI()
  const [key, setKey] = useState('')
  useEffect(() => {
    const show = () => { const next = takeRouteError(); if (next) setKey(next) }
    window.addEventListener('bridgeflow:route-error', show)
    show()
    return () => window.removeEventListener('bridgeflow:route-error', show)
  }, [])
  if (!key) return null
  return <div className="bf-state bf-route-notice bf-callout" data-tone="danger" role="alert">
    <p>{t(key)}{key === 'loginRequired' && portalLoginUrl() && <> <a className="bf-login-link" href={portalLoginUrl()}>{t('loginWithFeishu')}</a></>}</p><button onClick={() => setKey('')}>{t('close')}</button>
  </div>
}

export function mountShell(ctx: Context) {
  ctx.slots.inject('shell.overlay', () => ctx.slots.register({ name: 'shell.overlay', id: 'bridgeflow-route-notice' }, RouteNotice))
  ctx.effect(() => { const tag = document.createElement('style'); tag.textContent = shellStyle; document.head.append(tag); document.body.setAttribute('data-bf-notebook', ''); return () => { tag.remove(); document.body.removeAttribute('data-bf-notebook') } }, 'bridgeflow: notebook skin')
  ctx.slots.inject('shell.overlay', () => ctx.slots.register({ name: 'shell.overlay', id: 'bridgeflow-notebook' }, () => <Shell ctx={ctx}/>))
}
