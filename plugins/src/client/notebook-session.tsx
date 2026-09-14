import { TourLayer } from './tour/tour.tsx'
import { tourEvent } from './tour/state.ts'
import { defaultNotebookKind } from '../notebook-capabilities.ts'
import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { Context } from '@deepseek-ai/cordis'
import type { ISessions, SessionListState } from '@deepseek-ai/dsh-api-session-controller/client'
import type { SessionId } from '@deepseek-ai/dsh-session'
import type { Notebook } from '../notebooks.ts'
import { api, createNotebookSession, formatDateTime, navigate, route, useUI, type Route, type Summary, describeError } from './ui.ts'

function bookmark(title: string, selected: Route, batch: string, kind: NonNullable<Notebook['kind']>): Notebook {
  return { title, kind, ...(batch ? { batch } : {}), view: selected.view ?? 'state',
    ...(batch && selected.source ? {source:selected.source} : {}),
    ...(batch && selected.report ? {report:selected.report} : {}) }
}

/** DSH owns sessions and its domain store owns bookmarks; drafts remain local until saved. */
export function useNotebook(ctx: Context, selected: Route, batch: string) {
  const { t, language } = useUI(), sessions = ctx.sessions as unknown as ISessions
  const list = useSyncExternalStore<SessionListState>(fn => sessions.list.subscribe(fn), () => sessions.list.getSnapshot())
  const id = list.current
  const [revision,setRevision]=useState(0)
  const [kind, setKind] = useState<NonNullable<Notebook['kind']>>(defaultNotebookKind)
  const [title, setTitle] = useState(''), [saved, setSaved] = useState<Notebook | null>(null)
  const [loadedId,setLoadedId]=useState<SessionId | undefined>(undefined)
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [loaded, setLoaded] = useState(false)
  const confirm = useRef<HTMLDialogElement>(null), history = useRef<HTMLDialogElement>(null)
  const action = useRef<(() => Promise<void>) | null>(null)
  const last = useRef(id), drafts = useRef(new Map<string, Notebook>())
  const current = bookmark(title, selected, batch, kind)
  const ready = loaded && loadedId === id
  const dirty = Boolean(id && ready && (saved
    ? saved.title !== title || saved.batch !== (batch || undefined) || (saved.kind ?? defaultNotebookKind) !== kind
    : Boolean(batch) || title !== t('untitledNotebook') || kind !== defaultNotebookKind))
  useEffect(() => {
    if (ready && route().kind !== kind) navigate({...route(),kind})
  }, [ready, kind, selected.kind])
  useEffect(() => {
    if (id && ready) drafts.current.set(id, current)
  }, [id, ready, title, batch, selected.view, selected.source, selected.report, kind])
  useEffect(() => {
    const changed = last.current !== undefined && last.current !== id
    last.current = id
    setLoaded(false); setSaved(null); setTitle(''); setError('')
    if (!id) { setKind(defaultNotebookKind); setLoadedId(undefined); setLoaded(true); return }
    const controller = new AbortController()
    void api<{notebook: Notebook | null}>(`/notebook?session_id=${encodeURIComponent(id)}`, {signal:controller.signal})
      .then(({notebook}) => {
        if (controller.signal.aborted) return
        const draft = drafts.current.get(id) ?? notebook
        setKind(draft?.kind ?? defaultNotebookKind); setSaved(notebook); setTitle(draft?.title ?? list.byId[id]?.title ?? t('untitledNotebook')); setLoadedId(id); setLoaded(true)
        const target = route().child || route().parent
        if (id !== target && (changed || (!route().batch && (!route().view || route().view === 'state')))) {
          const {title: _title, ...destination} = draft ?? {title:''}
          navigate(Object.keys(destination).length ? destination : {view:'state'})
        }
      }).catch(e => { if (!controller.signal.aborted) setError(describeError(e, t)) })
    return () => controller.abort()
  }, [id, revision])
  useEffect(() => {
    if (!dirty) return
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [dirty])
  async function save() {
    if (!id || !title.trim()) throw new Error(t('notebookTitleRequired'))
    const result = await api<{notebook:Notebook}>(`/notebook?session_id=${encodeURIComponent(id)}`, {
      method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify(current),
    })
    setTitle(result.notebook.title); setSaved(result.notebook); drafts.current.set(id, result.notebook)
    await sessions.refresh()
    tourEvent('saved', batch)
  }
  async function perform(next: () => Promise<void>) {
    setBusy(true); setError('')
    try { await next() } catch (e) { setError(describeError(e, t)) } finally { setBusy(false) }
  }
  function leave(next: () => Promise<void>) {
    if (dirty) { action.current = next; confirm.current?.showModal() }
    else void perform(next)
  }
  async function decide(keep: boolean) {
    setBusy(true); setError('')
    try {
      if (keep) await save()
      else if (id) { drafts.current.delete(id); setSaved(saved); setTitle(saved?.title ?? t('untitledNotebook')) }
      confirm.current?.close()
      const next = action.current; action.current = null
      if (next) await next()
    } catch (e) { setError(describeError(e, t)) } finally { setBusy(false) }
  }
  const create = () => leave(async () => { const fresh = await createNotebookSession(sessions); sessions.open(fresh); navigate({view:'state'}) })
  const exit = () => leave(async () => { sessions.clear(); navigate({view:'state'}); history.current?.showModal(); await sessions.refresh() })
  const openHistory = () => { history.current?.showModal(); void perform(() => sessions.refresh()) }
  const sample = () => leave(async () => {
    const batch = await api<Summary>('/batches/demo',{method:'POST'})
    const fresh = await createNotebookSession(sessions)
    const notebook = {title:t('sampleNotebookTitle'),batch:batch.batch_id,view:'state',kind:'monthly'}
    await api(`/notebook?session_id=${encodeURIComponent(fresh)}`,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(notebook)})
    drafts.current.delete(fresh); sessions.open(fresh); navigate({batch:batch.batch_id,view:'state'}); await sessions.refresh()
    tourEvent('sample', batch.batch_id, fresh)
  })
  const dialogs = <>
    <dialog data-tour-surface="confirm" ref={confirm} className="bf-panel bf-notebook-dialog" aria-label={t('leaveNotebook')} onCancel={() => {action.current=null}}>
      <h2>{t('leaveNotebook')}</h2><p>{t('saveNotebookHelp')}</p>
      <label>{t('notebookName')}<input value={title} maxLength={120} onChange={e=>setTitle(e.target.value)}/></label>
      {error && <p role="alert">{error}</p>}
      <div className="bf-actions"><button disabled={busy || !title.trim()} onClick={()=>void decide(true)}>{t('saveAndContinue')}</button><button disabled={busy} onClick={()=>void decide(false)}>{t('discardAndContinue')}</button><button disabled={busy} onClick={()=>{action.current=null;confirm.current?.close()}}>{t('cancelLeave')}</button></div>
      <TourLayer surface="confirm"/>
    </dialog>
    <dialog data-tour-surface="history" ref={history} className="bf-panel bf-notebook-dialog" aria-label={t('notebooks')}>
      <header><h2>{t('notebooks')}</h2><button onClick={()=>history.current?.close()}>{t('close')}</button></header>
      <p>{t('notebookHistoryHelp')}</p>
      <button disabled={busy} onClick={()=>{history.current?.close();sample()}}>{t('sampleNotebook')}</button>
      {error && <p role="alert">{error}</p>}
      <ul className="bf-notebook-list">{list.ids.map(key=>list.byId[key]).filter(row=>row && !row.parentId && row.origin !== 'subagent' && (row.title || !row.blank)).map(row => row && <li key={row.id}><button aria-current={row.id===id ? 'page' : undefined} onClick={()=>{history.current?.close();if(row.id!==id)leave(async()=>{sessions.open(row.id as SessionId)})}}><strong>{row.title || row.displayTitle}</strong><small>{formatDateTime(row.updatedAt, language)}</small></button></li>)}</ul>
      <TourLayer surface="history"/>
    </dialog>
  </>
  return {title,setTitle,kind,setKind:(value:NonNullable<Notebook['kind']>)=>{setKind(value);navigate({...route(),kind:value})},busy,loaded:ready,dirty,persisted:Boolean(saved),error,retry:()=>setRevision(n=>n+1),dialogs,create,exit,openHistory,sample,save:()=>void perform(save)}
}
