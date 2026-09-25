import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { api, navigate, route, useUI } from '../ui.ts'
import { tours } from './steps.ts'
import { placeCard, type Rect } from './position.ts'
import { closeTourCard, exitTour, moveTour, observeTour, openTourHelp, resetTour, returnTourEntry, retryTourTarget, startTour, tourSnapshot, tourSubscribe } from './state.ts'
import { tourStyle } from './style.ts'
import { Icon } from '../icons.tsx'

const tabbable = 'button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),summary,a[href],[tabindex="0"]'
function visible(el: Element): el is HTMLElement { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden' }
function activeModal() { return Array.from(document.querySelectorAll<HTMLDialogElement>('dialog[open]')).filter(visible).at(-1) }
export function TourDriver({ session, batch, sample, ready, reveal }: { session: string; batch: string; sample: boolean; ready: boolean; reveal: (pane?: 'sources' | 'studio') => void }) {
  const state = useSyncExternalStore(tourSubscribe, tourSnapshot)
  const [authorized, setAuthorized] = useState(false)
  const revealRef = useRef(reveal); revealRef.current = reveal
  useEffect(() => { const c = new AbortController(); void api<{ workspaceId?: string }>('/config', { signal: c.signal }).then(x => setAuthorized(Boolean(x.workspaceId))).catch(() => setAuthorized(false)); return () => c.abort() }, [])
  useEffect(() => { observeTour(session, batch, sample, ready && authorized && !activeModal()); document.body.toggleAttribute('data-tour-ready', ready && authorized); return () => document.body.removeAttribute('data-tour-ready') }, [session, batch, sample, ready, authorized])
  useEffect(() => {
    const tag = document.createElement('style'); tag.textContent = tourStyle; document.head.append(tag)
    return () => tag.remove()
  }, [])
  useEffect(() => {
    if (state.mode !== 'active') return
    const step = tours[state.progress.track][state.progress.index]!
    revealRef.current(step.pane)
    // Reading an already-existing view is safe. Action entry steps never navigate for the user.
    const open = () => {
      if (!step.view || state.progress.batch !== batch || activeModal()) return
      const current = route()
      if (step.view === 'source') {
        if (state.progress.source && (current.view !== 'source' || current.source !== state.progress.source)) navigate({ batch, view: 'source', source: state.progress.source })
      } else if (current.view !== step.view) navigate({ batch, view: step.view })
    }
    open()
    // Restoring a notebook lands on the default view after its metadata loads, which
    // can arrive after this step opened its own view. Reopen it only when the route
    // fell back to that default; a view the person chose is left alone.
    const fellBack = () => { const view = route().view; if (!view || view === 'state') open() }
    window.addEventListener('hashchange', fellBack)
    return () => window.removeEventListener('hashchange', fellBack)
  }, [state.mode, state.progress.track, state.progress.index, state.revision, batch])
  return null
}
export function TourHelpButton() { const { t } = useUI(); return <button data-tour-id="help" onClick={openTourHelp}>{t('tourHelp')}</button> }

/** Each project-owned dialog hosts the same layer inside its own modal focus boundary. */
export function TourLayer({ surface = 'shell' }: { surface?: string }) {
  const { t } = useUI(), state = useSyncExternalStore(tourSubscribe, tourSnapshot), p = state.progress
  const step = tours[p.track][p.index]!
  const card = useRef<HTMLDivElement>(null), savedFocus = useRef<HTMLElement | null>(null), targetRef = useRef<HTMLElement | null>(null)
  const [geo, setGeo] = useState<{ rect: Rect | null; viewport: Rect; surface: string; blocked: boolean; recovering?: boolean; error?: string }>({ rect: null, viewport: { x: 0, y: 0, width: window.innerWidth, height: window.innerHeight }, surface: 'shell', blocked: false })
  const [timedOut, setTimedOut] = useState(false), [height, setHeight] = useState(380)
  const shown = state.mode !== 'hidden' && geo.surface === surface
  useEffect(() => {
    if (state.mode === 'hidden') return
    let frame = 0, scrolled: Element | null = null, stopped = false
    const measure = () => {
      frame = 0
      if (stopped) return
      const modal = activeModal()
      // Never compete with a native modal we do not own or relocate its DOM.
      if (modal && !modal.dataset.tourSurface) { exitTour(); return }
      const owner = modal?.dataset.tourSurface ?? 'shell'
      const candidates = Array.from(document.querySelectorAll<HTMLElement>(`[data-tour-id="${step.target}"]`))
      const normalTarget = state.mode === 'active' ? candidates.find(el => visible(el) && (!modal || modal.contains(el))) ?? null : null
      const recovery = state.mode === 'active' ? Array.from(document.querySelectorAll<HTMLElement>('[data-tour-recovery]')).find(el => visible(el) && (!modal || modal.contains(el))) : null
      const target = recovery ?? normalTarget ?? null
      const error = Array.from(document.querySelectorAll<HTMLElement>('[role=alert]')).find(el => visible(el) && !el.closest('[data-tour-layer]'))?.textContent?.slice(0, 500) ?? ''
      if (targetRef.current !== target) { if (targetRef.current) resize.unobserve(targetRef.current); if (target) resize.observe(target) }
      targetRef.current = target
      const vv = window.visualViewport
      const viewport = { x: vv?.offsetLeft ?? 0, y: vv?.offsetTop ?? 0, width: vv?.width ?? innerWidth, height: vv?.height ?? innerHeight }
      if (target) {
        const r = target.getBoundingClientRect()
        const outside = r.bottom <= viewport.y || r.top >= viewport.y + viewport.height || r.right <= viewport.x || r.left >= viewport.x + viewport.width
        if (target !== scrolled || outside) { scrolled = target; target.scrollIntoView({ block: 'center', inline: 'center', behavior: 'instant' as ScrollBehavior }) }
      }
      let rect: Rect | null = null
      if (target) {
        const r = target.getBoundingClientRect()
        let left = Math.max(viewport.x + 4, r.left - 6), top = Math.max(viewport.y + 4, r.top - 6)
        let right = Math.min(viewport.x + viewport.width - 4, r.right + 6), bottom = Math.min(viewport.y + viewport.height - 4, r.bottom + 6)
        // Clip the spotlight to actual scroll containers, never to invisible offscreen content.
        for (let parent = target.parentElement; parent && parent !== document.body; parent = parent.parentElement) {
          const css = getComputedStyle(parent), b = parent.getBoundingClientRect()
          if (/(auto|scroll|hidden)/.test(css.overflowY)) { top = Math.max(top, b.top); bottom = Math.min(bottom, b.bottom) }
          if (/(auto|scroll|hidden)/.test(css.overflowX)) { left = Math.max(left, b.left); right = Math.min(right, b.right) }
        }
        if (right > left && bottom > top) rect = { x: left, y: top, width: right - left, height: bottom - top }
      }
      const next = { rect, viewport, surface: owner, blocked: Boolean(modal && !target), recovering: Boolean(recovery), error }
      setGeo(old => JSON.stringify(old) === JSON.stringify(next) ? old : next)
    }
    const schedule = () => { if (!frame) frame = requestAnimationFrame(measure) }
    const mutations = new MutationObserver(records => { if (records.some(r => !(r.target as Element).closest?.('[data-tour-layer]'))) schedule() })
    mutations.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['data-tour-id', 'open', 'style', 'class', 'data-mobile-open', 'disabled', 'data-bf-hide-studio', 'data-bf-hide-sources'] })
    const resize = new ResizeObserver(schedule); resize.observe(document.documentElement)
    document.addEventListener('scroll', schedule, true); window.addEventListener('resize', schedule); document.addEventListener('transitionend', schedule, true)
    window.visualViewport?.addEventListener('resize', schedule); window.visualViewport?.addEventListener('scroll', schedule)
    measure()
    return () => { stopped = true; cancelAnimationFrame(frame); mutations.disconnect(); resize.disconnect(); document.removeEventListener('scroll', schedule, true); window.removeEventListener('resize', schedule); document.removeEventListener('transitionend', schedule, true); window.visualViewport?.removeEventListener('resize', schedule); window.visualViewport?.removeEventListener('scroll', schedule) }
  }, [state.mode, step.id, state.revision])
  useEffect(() => {
    setTimedOut(false)
    if (state.mode !== 'active' || geo.rect) return
    const timer = setTimeout(() => setTimedOut(true), 8000)
    return () => clearTimeout(timer)
  }, [state.mode, step.id, Boolean(geo.rect), state.revision])
  useEffect(() => {
    if (!shown || !card.current) return
    const resize = new ResizeObserver(() => { if (card.current) setHeight(Math.min(card.current.scrollHeight + 2, innerHeight * .72)) })
    resize.observe(card.current)
    return () => resize.disconnect()
  }, [shown, state.mode, step.id, timedOut])
  useEffect(() => {
    if (!shown) return
    savedFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
    document.body.setAttribute('data-bf-tour-active', '')
    const focus = requestAnimationFrame(() => card.current?.focus({ preventScroll: true }))
    const keys = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.preventDefault(); e.stopImmediatePropagation(); exitTour(); return }
      if (e.key !== 'Tab') return
      const modal = activeModal()
      const target = targetRef.current
      const roots = [card.current, ...(geo.blocked && modal ? [modal] : target ? [target] : [])].filter(Boolean) as HTMLElement[]
      const nodes = [...new Set(roots.flatMap(root => [root, ...Array.from(root.querySelectorAll<HTMLElement>(tabbable))]).filter(el => el.matches(tabbable) && visible(el)))]
      if (!nodes.length) return
      const i = nodes.indexOf(document.activeElement as HTMLElement)
      e.preventDefault(); nodes[(i + (e.shiftKey ? -1 : 1) + nodes.length) % nodes.length]?.focus()
    }
    document.addEventListener('keydown', keys, true)
    return () => { cancelAnimationFrame(focus); document.removeEventListener('keydown', keys, true); document.body.removeAttribute('data-bf-tour-active'); if (savedFocus.current?.isConnected) savedFocus.current.focus({ preventScroll: true }) }
  }, [shown, step.id, geo.blocked])
  if (!shown) return null
  const active = state.mode === 'active', wait = active && (!geo.rect || geo.recovering), intro = !step.event
  const complete = state.mode === 'complete', help = state.mode === 'help', welcome = state.mode === 'welcome'
  const actual = active ? geo.rect : null, vp = geo.viewport
  const box = placeCard(actual, active ? 350 : 440, height, vp)
  const masks: Rect[] = actual ? [
    { x: vp.x, y: vp.y, width: vp.width, height: actual.y - vp.y },
    { x: vp.x, y: actual.y, width: actual.x - vp.x, height: actual.height },
    { x: actual.x + actual.width, y: actual.y, width: Math.max(0, vp.x + vp.width - actual.x - actual.width), height: actual.height },
    { x: vp.x, y: actual.y + actual.height, width: vp.width, height: Math.max(0, vp.y + vp.height - actual.y - actual.height) },
  ] : geo.blocked ? [] : [vp]
  const css = (r: Rect) => ({ left: r.x, top: r.y, width: r.width, height: r.height })
  return <div data-tour-layer="" data-tour-mode={state.mode} data-tour-step={active ? step.id : ''}>
    {masks.map((m, i) => <div key={i} className="bf-tour-shade" style={css(m)} aria-hidden="true"/>)}
    {actual && <div className="bf-tour-ring" style={css(actual)} aria-hidden="true"/>}
    <div ref={card} data-tour-card="" className="bf-tour-card" role="dialog" aria-label={t(active ? `tour_${step.id}_title` : complete ? 'tourComplete' : 'tourHelp')} aria-describedby={`tour-description-${surface}`} tabIndex={-1} style={geo.blocked ? { position: 'relative', width: 'auto', maxHeight: '32vh', marginTop: 16 } : { ...css(box), height: 'auto', maxHeight: box.height }}>
      <button className="bf-tour-close" aria-label={t('tourExit')} onClick={exitTour}>×</button>
      <span className="bf-tour-eyebrow">{active ? `${t('tourStep')} ${p.index + 1} / ${tours[p.track].length}` : t('tourSafety')}</span>
      {active ? <>
        <div className="bf-tour-progress" aria-hidden="true"><span style={{ width: `${(p.index + 1) / tours[p.track].length * 100}%` }}/></div>
        <h2>{t(`tour_${step.id}_title`)}</h2>
        <p id={`tour-description-${surface}`}>{t(`tour_${step.id}_body`)}</p>
        {wait ? <div className="bf-tour-task" role="status"><b>{t(timedOut ? 'tourMissing' : 'tourWaiting')}</b>{t(timedOut ? 'tourMissingBody' : 'tourWaitingBody')}
          <div className="bf-tour-actions"><button onClick={retryTourTarget}>{t('tourRetry')}</button><button onClick={returnTourEntry}>{t('tourEntry')}</button></div>
        </div> : <>
          <div className="bf-tour-task"><b>{t('tourAction')}</b>{t(`tour_${step.id}_action`)}</div>
          <div className="bf-tour-expected"><b>{t('tourExpected')}</b>{t(`tour_${step.id}_expected`)}</div>
        </>}
        {geo.error && <div className="bf-tour-task" role="alert"><b>{t('tourError')}</b>{geo.error}<p>{t('tourErrorHelp')}</p></div>}
        {['sample', 'result'].includes(step.id) && <details><summary>{t('tourMore')}</summary><p>{t(`tour_${step.id}_more`)}</p></details>}
        {!intro && <p className="bf-tour-wait" role="status">{t(p.done.includes(step.event!) ? 'tourDoneAction' : 'tourWaitingAction')}</p>}
        <div className="bf-tour-actions"><button disabled={p.index === 0} onClick={() => moveTour(-1)}>{t('tourBack')}</button><button onClick={exitTour}>{t('tourExit')}</button><button className="bf-tour-primary" disabled={wait || !intro && !p.done.includes(step.event!)} onClick={() => moveTour(1)}>{t(p.index === tours[p.track].length - 1 ? 'tourFinish' : 'tourNext')}</button></div>
      </> : <>
        <div className="bf-tour-mark" aria-hidden="true"><Icon name={complete ? 'check' : 'sparkle'} size={24} /></div>
        <h2>{t(complete ? p.track === 'core' ? 'tourComplete' : p.track === 'workflow' ? 'tourWorkflowDone' : 'tourSupplementDone' : welcome ? 'tourWelcome' : 'tourHelp')}</h2>
        <p id={`tour-description-${surface}`}>{t(complete ? p.track === 'core' ? 'tourCompleteBody' : p.track === 'workflow' ? 'tourWorkflowDoneBody' : 'tourSupplementBody' : welcome ? 'tourWelcomeBody' : p.status === 'completed' ? 'tourHelpCompleted' : 'tourSkipped')}</p>
        {welcome && <div className="bf-tour-task">{t('tourWelcomeResult')}</div>}
        {help && <div className="bf-tour-list">
          {p.status !== 'notStarted' && p.status !== 'completed' && <button className="bf-tour-primary" onClick={() => startTour(p.track, true)}>{t('tourResume')}</button>}
          {p.track !== 'core' && <button onClick={() => startTour('core', true)}>{t('tourResumeCore')}</button>}<button onClick={() => startTour('core')}>{t('tourCore')}</button><button onClick={() => startTour('review')}>{t('tourReview')}</button><button onClick={() => startTour('quotation')}>{t('tourQuotation')}</button><button onClick={() => startTour('workflow')}>{t('tourWorkflow')}</button>
          <details><summary>{t('tourReset')}</summary><p>{t('tourResetHelp')}</p><button onClick={resetTour}>{t('tourReset')}</button></details>
        </div>}
        {welcome && <button className="bf-tour-secondary" onClick={() => startTour('workflow')}>{t('tourWelcomeWorkflow')}</button>}
        {!help && <div className="bf-tour-actions"><button onClick={complete ? () => startTour(p.track) : exitTour}>{t(complete ? 'tourRestart' : 'tourLater')}</button><button className="bf-tour-primary" onClick={complete ? () => { if (p.track === 'core' && p.batch) navigate({ batch: p.batch, view: 'integration' }); closeTourCard() } : () => startTour('core')}>{t(complete ? 'tourExplore' : 'tourStart')}</button></div>}
        <p className="bf-tour-storage">{t(state.storageOK ? 'tourStorage' : 'tourStorageUnavailable')}</p>
      </>}
    </div>
  </div>
}
