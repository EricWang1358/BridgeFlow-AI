import { useEffect, useState, useSyncExternalStore } from 'react'
import type { Context } from '@deepseek-ai/cordis'
import type {} from '@deepseek-ai/dsh-client-ui-sidebar/client'
import type {} from '@deepseek-ai/dsh-client-ui-layout/client'
import type {} from '@deepseek-ai/dsh-client-ui-renderer/client'
import type { ToolCallViewProps } from '@deepseek-ai/dsh-client-ui-tool/client'
import type { ComposerChainProps, InputZone } from '@deepseek-ai/dsh-client-ui-conversation/client'
import { MappingApproval } from './approval.tsx'
import { BusinessReview, type Review } from './review.tsx'
import { configureRuntime, navigate, openSession, reportRouteError, route, useUI } from './ui.ts'
import { DataWorkspace } from './workspace.tsx'
import { QuotationButton } from './quotation.tsx'
import { mountShell } from './shell.tsx'
import { mountState } from './state.tsx'
import { motion } from './motion.ts'
import { style } from './style.ts'

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
    <details><summary>{t('monthlySteps')}</summary><ol>{steps.map(n => <li key={n}><b>{t(`heroStep${n}`)}</b> <span>· {t(`heroStep${n}Hint`)}</span></li>)}</ol></details>
    <div className="bf-actions" style={{ marginBottom: 0 }}>
      <button className="bf-primary" onClick={() => window.dispatchEvent(new Event('bridgeflow:add-sources'))}>{t('heroOpen')}</button><QuotationButton />
    </div>
  </aside>
}

/**
 * An image in the composer meets a text-only model, and the native message points to a
 * model selector this deployment removes on purpose (#99). Another package owns that
 * copy, so we add the way forward beside it instead: tables come in as sources, where
 * every number stays traceable to a cell.
 */
function ImageNotice({ input }: InputZone) {
  const { t } = useUI()
  if (!input.imageIds.length) return null
  return <aside className="bf-callout" data-tone="warn" role="status" aria-label={t('imageNoticeTitle')}>
    <h3>{t('imageNoticeTitle')}</h3><p>{t('imageNotice')}</p>
    <div className="bf-actions" style={{ marginBottom: 0 }}>
      <button className="bf-primary" onClick={() => window.dispatchEvent(new Event('bridgeflow:add-sources'))}>{t('addSources')}</button>
    </div>
  </aside>
}

/** Every approval-gated product tool gets the same decision card: summary, reason, reject first. */
const APPROVAL_CARD_TOOLS = new Set(['confirm_mapping', 'confirm_column_match', 'workflow_record', 'workflow_approve_submit', 'workflow_handoff', 'discovery_propose', 'discovery_register', 'discovery_decision_finalize', 'discovery_decision_propose', 'discovery_decision_resolve', 'discovery_decision_vote', 'discovery_graph_save', 'discovery_score_save', 'discovery_meeting_save', 'quarantine_decide', 'quarantine_apply', 'feishu_import', 'feishu_upload_report'])

function Welcome() {
  const { t } = useUI()
  return <div className="bf-welcome"><span aria-hidden="true">✦</span><h2>{t('welcomeTitle')}</h2><p>{t('welcomeHelp')}</p></div>
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
export const inject = ['slots', 'locale', 'sessions', 'uiConversation', 'conversation', 'layout']

/**
 * The settings scope the official locale plugin persists into. Typed locally and
 * minimally: the package owning it is not one of our dependencies, and all we do
 * is what the locale plugin itself does — bind the 'locale' namespace and read it.
 */
interface LocaleSettingsSection { preference?: string }
interface SettingsScopeLike {
  getSnapshot(): { value?: LocaleSettingsSection }
  subscribe(fn: () => void): () => void
}

export function apply(ctx: Context): void {
  configureRuntime(ctx)
  // Default to English for a user with no saved preference (#110). The host
  // otherwise derives the provisional locale from the browser, so a zh-CN browser
  // would open in Chinese. We wait for the settings document to actually load
  // before deciding: writing earlier could clobber a stored preference that has
  // simply not synced yet. The write goes through setLocale — the official,
  // durable entry — so the choice then survives reloads and host restarts like
  // any explicit switch.
  ctx.inject(['locale', 'settingsScope'], ctx => {
    const scope = ((ctx as unknown as { settingsScope: { bind(input: { namespace: string }): SettingsScopeLike } }).settingsScope).bind({ namespace: 'locale' })
    let stop = () => {}
    const check = () => {
      const section = scope.getSnapshot().value
      if (section === undefined) return
      stop()
      if (section.preference === undefined) ctx.locale.setLocale('en')
    }
    stop = scope.subscribe(check)
    check()
    ctx.effect(() => stop, 'bridgeflow: default locale')
  })
  ctx.slots.inject('conversation.composer', () => ctx.slots.register({ name: 'conversation.composer', priority: 0,
    select: ({ pendingInteraction }: ComposerChainProps) => pendingInteraction?.kind === 'approval' && APPROVAL_CARD_TOOLS.has(pendingInteraction.toolName) ? pendingInteraction : null,
  }, MappingApproval))
  ctx.effect(() => { const tag = document.createElement('style'); tag.textContent = style + motion; document.head.append(tag); return () => tag.remove() }, 'bridgeflow: styles')
  ctx.slots.inject('conversation.hero.brand.mark', () => ctx.slots.register({ name: 'conversation.hero.brand.mark', priority: -10 }, Welcome))
  ctx.slots.inject('sidebar.brand.name', () => ctx.slots.register({ name: 'sidebar.brand.name', priority: -10 }, () => <span>BridgeFlow AI</span>))
  // Above the composer card, so the orientation reads before the prompt box rather
  // than competing with it.
  ctx.slots.inject('conversation.input.dock', () => ctx.slots.register({ name: 'conversation.input.dock', id: 'bridgeflow-orientation', order: -10 }, Orientation))
  ctx.slots.inject('conversation.input.dock', () => ctx.slots.register({ name: 'conversation.input.dock', id: 'bridgeflow-image-notice', order: -20 }, ImageNotice))
  ctx.slots.inject('shell.overlay', () => ctx.slots.register({ name: 'shell.overlay', id: 'bridgeflow-data-dialog' }, DataWorkspace))
  mountState(ctx)
  mountShell(ctx)
  ctx.effect(() => {
    const navigateSession = () => { const value = route(); if (value.parent) void openSession(value.parent, value.child).catch(e => { ctx.logger.warn('Session route unavailable: %s', String(e)); reportRouteError(value.child ? 'routeChildUnavailable' : 'routeParentUnavailable') }) }
    navigateSession(); window.addEventListener('hashchange', navigateSession); return () => window.removeEventListener('hashchange', navigateSession)
  }, 'bridgeflow: native session routes')
  for (const key of ['discovery_materials', 'aggregate_metric', 'confirm_mapping', 'column_candidates', 'confirm_column_match', 'workflow_catalogue', 'workflow_draft', 'workflow_guidance', 'workflow_board', 'workflow_record', 'workflow_approve_submit', 'workflow_handoff', 'discovery_propose', 'discovery_register', 'discovery_decision_finalize', 'discovery_decision_propose', 'discovery_decision_resolve', 'discovery_decision_vote', 'discovery_graph_save', 'discovery_score_save', 'discovery_meeting_save', 'quarantine_list', 'quarantine_decide', 'quarantine_apply', 'feishu_import', 'feishu_upload_report', 'integration_summary', 'batch_summary', 'list_metrics', 'lookup_field_dictionary', 'review_context', 'review_finalize']) {
    ctx.slots.inject('tool.call.toolview', () => ctx.slots.register({ name: 'tool.call.toolview', key }, ToolCard))
  }
}
