import { useEffect, useState, useSyncExternalStore } from 'react'
import type { Context } from '@deepseek-ai/cordis'
import type {} from '@deepseek-ai/dsh-client-ui-sidebar/client'
import type {} from '@deepseek-ai/dsh-client-ui-layout/client'
import type {} from '@deepseek-ai/dsh-client-ui-renderer/client'
import type { ToolCallViewProps } from '@deepseek-ai/dsh-client-ui-tool/client'
import type { ComposerChainProps, InputZone } from '@deepseek-ai/dsh-client-ui-conversation/client'
import { MappingApproval } from './approval.tsx'
import { BusinessReview, type Review } from './review.tsx'
import { configureRuntime, navigate, openSession, route, useUI } from './ui.ts'
import { DataWorkspace, ImportForm } from './workspace.tsx'
import { mountQuotation, QuotationButton } from './quotation.tsx'
import { mountState } from './state.tsx'
import { style } from './style.ts'

let drawer = false
const listeners = new Set<() => void>()
const subscribe = (fn: () => void) => { listeners.add(fn); return () => { listeners.delete(fn) } }
function setDrawer(value: boolean) { drawer = value; for (const fn of listeners) fn() }
function FileButton() { const { t } = useUI(); return <button className="bf-open" onClick={() => setDrawer(!drawer)}>{t('files')}</button> }
function FileDrawer() {
  const { t } = useUI(), open = useSyncExternalStore(subscribe, () => drawer)
  useEffect(() => { if (!open) return; const escape = (e: KeyboardEvent) => { if (e.key === 'Escape') setDrawer(false) }; window.addEventListener('keydown', escape); return () => window.removeEventListener('keydown', escape) }, [open])
  if (!open) return null
  return <aside className="bf-drawer" aria-label={t('files')}><button style={{ float: 'right' }} onClick={() => setDrawer(false)}>{t('close')}</button><h2>{t('files')}</h2><ImportForm onSaved={batch => { setDrawer(false); navigate({ batch: batch.batch_id, view: 'master' }) }} /></aside>
}
/**
 * What this product is, and what to do first.
 *
 * The native shell's blank-session hero says "探索未至之境" and offers a coding
 * prompt placeholder — correct for the harness, wrong for an operator who was asked
 * to reconcile four departments' month-end. Nothing on that screen named the
 * product, the flow, or the one entry point; the entry point itself was the faintest
 * control on the page.
 *
 * This sits above the composer, so it is present exactly where the user's attention
 * already is, and it renders only while the session is blank.
 */
function Orientation({ session, input }: InputZone) {
  const { t } = useUI()
  const steps = [1, 2, 3, 4] as const
  // Orientation is for somebody who has not started. `blank` alone is not that
  // test: a session stays blank until its first durable event, so the card sat
  // there while the user was already typing their request into the box below it.
  // Anything drafted, queued or in flight means they have started.
  const started = !session.blank || input.draft.trim() || input.queue.length || input.phase !== 'plain'
  if (started) return null
  return <aside className="bf-hero" aria-label={t('heroTitle')}>
    <h3>{t('heroTitle')}</h3>
    <p className="bf-lead bf-hint">{t('heroLead')}</p>
    <ol>{steps.map(n => <li key={n}><b>{t(`heroStep${n}`)}</b> <span>· {t(`heroStep${n}Hint`)}</span></li>)}</ol>
    <div className="bf-actions" style={{ marginBottom: 0 }}>
      <button className="bf-primary" onClick={() => setDrawer(true)}>{t('heroOpen')}</button><QuotationButton />
    </div>
  </aside>
}

function ToolCard({ block, toolName, inspect }: ToolCallViewProps) {
  const { t } = useUI(), [expanded, setExpanded] = useState(false)
  const settled = 'kind' in block && block.kind === 'tool-result'
  const text = 'kind' in block ? block.content.filter(c => c.type === 'text').map(c => c.text).join('\n') : block.argsRaw
  if (toolName === 'review_finalize' && settled && !block.isError) {
    try { const report = JSON.parse(text) as Review; if (Array.isArray(report.roles)) return <div className="bf-card"><BusinessReview report={report} />{inspect && <button onClick={inspect}>{t('inspect')}</button>}</div> } catch { /* Bounded fallback below. */ }
  }
  const state = settled ? block.isError ? 'failed' : 'completed' : 'running'
  return <section className="bf-card" aria-label={t(toolName)}>
    <header className="bf-card-head">
      <strong>{t(toolName)}</strong>
      <span role="status" className="bf-chip" data-status={state === 'completed' ? 'ok' : state === 'failed' ? 'rejected' : 'partial'}>{t(state)}</span>
    </header>
    <p>{text.slice(0, 180)}{text.length > 180 ? '…' : ''}</p>
    <div className="bf-actions" style={{ margin: '10px 0 0' }}>
      {text.length > 180 && <button className="bf-quiet" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>{t('details')}</button>}
      {inspect && <button className="bf-quiet" onClick={inspect}>{t('inspect')}</button>}
    </div>
    {expanded && text.length > 180 && <pre>{text.slice(0, 2400)}{text.length > 2400 ? '\n…' : ''}</pre>}
  </section>
}
export const inject = ['slots', 'locale', 'sessions', 'uiConversation', 'conversation']
export function apply(ctx: Context): void {
  configureRuntime(ctx)
  ctx.slots.inject('conversation.composer', () => ctx.slots.register({ name: 'conversation.composer', priority: 0,
    select: ({ pendingInteraction }: ComposerChainProps) => pendingInteraction?.kind === 'approval' && pendingInteraction.toolName === 'confirm_mapping' ? pendingInteraction : null,
  }, MappingApproval))
  ctx.effect(() => { const tag = document.createElement('style'); tag.textContent = style; document.head.append(tag); return () => tag.remove() }, 'bridgeflow: styles')
  ctx.slots.inject('sidebar.brand.name', () => ctx.slots.register({ name: 'sidebar.brand.name', priority: -10 }, () => <span>BridgeFlow AI</span>))
  ctx.slots.inject('sidebar.footer.action', () => ctx.slots.register({ name: 'sidebar.footer.action', id: 'bridgeflow-data' }, DataWorkspace))
  ctx.slots.inject('conversation.session.header.utilities', () => ctx.slots.register({ name: 'conversation.session.header.utilities', id: 'bridgeflow-files', order: 20 }, FileButton))
  ctx.slots.inject('shell.overlay', () => ctx.slots.register({ name: 'shell.overlay', id: 'bridgeflow-files' }, FileDrawer))
  // Above the composer card, so the orientation reads before the prompt box rather
  // than competing with it.
  ctx.slots.inject('conversation.input.dock', () => ctx.slots.register({ name: 'conversation.input.dock', id: 'bridgeflow-orientation', order: -10 }, Orientation))
  mountState(ctx)
  mountQuotation(ctx)
  ctx.effect(() => {
    const navigateSession = () => { const value = route(); if (value.parent) void openSession(value.parent, value.child).catch(e => ctx.logger.warn('Session route unavailable: %s', String(e))) }
    navigateSession(); window.addEventListener('hashchange', navigateSession); return () => window.removeEventListener('hashchange', navigateSession)
  }, 'bridgeflow: native session routes')
  for (const key of ['aggregate_metric', 'confirm_mapping', 'batch_summary', 'list_metrics', 'lookup_field_dictionary', 'review_context', 'review_finalize']) {
    ctx.slots.inject('tool.call.toolview', () => ctx.slots.register({ name: 'tool.call.toolview', key }, ToolCard))
  }
}
