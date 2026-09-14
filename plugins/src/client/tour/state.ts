import { tours, TOUR_VERSION, required, type Track } from './steps.ts'
export type Progress = { version: number; status: 'notStarted' | 'inProgress' | 'skipped' | 'completed'; track: Track; index: number; done: string[]; batch?: string | undefined; source?: string | undefined }
export const fresh = (): Progress => ({ version: TOUR_VERSION, status: 'notStarted', track: 'core', index: 0, done: [] })
export function parseProgress(raw: string | null): Progress {
  try {
    const p = JSON.parse(raw ?? 'null')
    if (!p || p.version !== TOUR_VERSION || !['notStarted', 'inProgress', 'skipped', 'completed'].includes(p.status)
      || !Object.hasOwn(tours, p.track) || !Number.isInteger(p.index) || p.index < 0 || p.index >= tours[p.track as Track].length
      || !Array.isArray(p.done) || p.done.some((x: unknown) => typeof x !== 'string') || p.batch && !/^[a-f0-9]{32}$/.test(p.batch)) return fresh()
    if (p.source !== undefined && !['production', 'procurement', 'finance', 'marketing'].includes(p.source)) return fresh()
    if (p.status === 'completed' && !canFinish(p)) return fresh()
    return { ...(p.source ? { source: p.source } : {}), version: TOUR_VERSION, status: p.status, track: p.track, index: p.index, done: p.done.filter((x: string) => required.includes(x) || x === 'quotation'), ...(p.batch ? { batch: p.batch } : {}) }
  } catch { return fresh() }
}
export function canFinish(p: Progress) { return p.track !== 'core' || required.every(e => p.done.includes(e)) }
export function acceptEvent(p: Progress, event: string, batch: string): Progress {
  if (p.status !== 'inProgress' || (event !== 'sample' && p.batch !== batch)) return p
  if (!(required.includes(event) || event === 'quotation')) return p
  if (event === 'sample' && p.batch !== batch) return { ...p, batch, source: undefined, done: ['sample'] }
  return { ...p, done: [...new Set([...p.done, event])] }
}
export type TourState = { progress: Progress; mode: 'hidden' | 'welcome' | 'help' | 'active' | 'complete'; scope: string; storageOK: boolean; revision: number }
let value: TourState = { progress: fresh(), mode: 'hidden', scope: '', storageOK: true, revision: 0 }
let initialized = false, observed = { session: '', batch: '', sample: false }, adopted = ''
const listeners = new Set<() => void>()
export const tourSubscribe = (fn: () => void) => { listeners.add(fn); return () => { listeners.delete(fn) } }
export const tourSnapshot = () => value
const key = (scope: string) => `bridgeflow.tour.v${TOUR_VERSION}:${scope || 'landing'}`
function publish(next: TourState, save = true) {
  value = next
  if (save) try { sessionStorage.setItem(key(value.scope), JSON.stringify(value.progress)) } catch { value = { ...value, storageOK: false } }
  for (const fn of listeners) fn()
}
export function observeTour(session: string, batch: string, sample: boolean, ready: boolean) {
  observed = { session, batch, sample }
  if (!ready) return
  if (adopted && adopted !== session) return
  adopted = ''
  if (!initialized || session !== value.scope) {
    if (initialized && !value.scope && session && !value.progress.batch && ['welcome', 'active'].includes(value.mode)) {
      publish({ ...value, scope: session }); return
    }
    initialized = true
    let p = fresh(), ok = true, offered = false
    try { p = parseProgress(sessionStorage.getItem(key(session))); offered = sessionStorage.getItem('bridgeflow.tour.offered') === '1'; sessionStorage.setItem('bridgeflow.tour.offered', '1') } catch { ok = false }
    // Refresh never starts an overlay over an in-progress task without consent.
    publish({ progress: p, mode: p.status === 'notStarted' && !offered ? 'welcome' : 'hidden', scope: session, storageOK: ok, revision: 0 }, false)
  }
}
export function openTourHelp() { publish({ ...value, mode: 'help' }, false) }
export function exitTour() {
  adopted = ''
  publish({ ...value, mode: 'hidden', progress: { ...value.progress, status: value.progress.status === 'completed' ? 'completed' : 'skipped' } })
}
export function startTour(track: Track = 'core', resume = false) {
  try { sessionStorage.setItem(`${key(value.scope)}:track:${value.progress.track}`, JSON.stringify(value.progress)) } catch {}
  let prior = value.progress
  if (resume && prior.track !== track) try { prior = parseProgress(sessionStorage.getItem(`${key(value.scope)}:track:${track}`)) } catch {}
  let p = resume && prior.track === track ? { ...prior, status: 'inProgress' as const } : { ...fresh(), track, status: 'inProgress' as const }
  if (track === 'core' && p.batch && p.batch !== observed.batch) p = { ...fresh(), status: 'inProgress' }
  if (resume && tours[p.track][p.index]!.id === 'source') p.index = tours.core.findIndex(s => s.id === 'evidence')
  if (observed.sample && observed.batch && (track !== 'core' || !p.batch || p.batch === observed.batch)) {
    p = { ...p, batch: observed.batch, done: [...new Set([...p.done, 'sample'])] }
  }
  if (track !== 'core') p.batch = observed.batch
  publish({ ...value, mode: 'active', progress: p, revision: value.revision + 1 })
}
export function resetTour() {
  try { for (const track of Object.keys(tours)) sessionStorage.removeItem(`${key(value.scope)}:track:${track}`) } catch {}
  publish({ ...value, progress: fresh(), mode: 'welcome' }) }
export function moveTour(delta: number) {
  const p = value.progress, steps = tours[p.track], step = steps[p.index]!
  if (delta > 0 && step.event && !p.done.includes(step.event)) return
  if (p.index + delta >= steps.length) {
    if (!canFinish(p)) {
      const index = steps.findIndex(s => s.event && !p.done.includes(s.event))
      publish({ ...value, progress: { ...p, index: Math.max(0, index) } }); return
    }
    publish({ ...value, progress: { ...p, status: 'completed' }, mode: 'complete' }); return
  }
  publish({ ...value, progress: { ...p, index: Math.max(0, p.index + delta) }, revision: value.revision + 1 })
}
export function tourEvent(event: string, batch: string, session?: string, source?: string) {
  if (value.mode !== 'active' || tours[value.progress.track][value.progress.index]!.event !== event) return
  if (event === 'sample' && session) {
    // Only a successful explicit sample action transfers progress to its new native session.
    adopted = observed.session === session ? '' : session
    publish({ ...value, scope: session }, false)
  }
  const previous = value.progress, p = acceptEvent(previous, event, batch)
  if (p === previous) return
  publish({ ...value, progress: source ? { ...p, source } : p })
  if (tours[p.track][p.index]!.event === event) moveTour(1)
}
export function returnTourEntry() {
  const p = value.progress
  // Reopen a read view, or return to the explicit action which creates its target.
  const id = tours[p.track][p.index]!.id
  const index = ['source', 'sourceDetails'].includes(id) ? tours.core.findIndex(s => s.id === 'evidence') : p.index
  publish({ ...value, progress: { ...p, index }, revision: value.revision + 1 })
}
export function retryTourTarget() { publish({ ...value, revision: value.revision + 1 }, false) }
export function closeTourCard() { publish({ ...value, mode: 'hidden' }, false) }
