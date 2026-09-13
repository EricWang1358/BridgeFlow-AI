import { ToolCatalogue } from './tool-catalogue.ts'
import type { Context } from '@deepseek-ai/cordis'
import Schema from '@deepseek-ai/schemastery'

import * as approval from './approval/index.ts'
import { DEFAULT_ANSWERER } from './approval/index.ts'
import { DEFAULT_BACKEND, type BackendConfig } from './backend.ts'
import * as untrustedInput from './guards/untrusted-input.ts'
import { aggregateMetric } from './tools/aggregate-metric.ts'
import { confirmMapping } from './tools/confirm-mapping.ts'
import { columnCandidates } from './tools/column-candidates.ts'
import { confirmColumnMatch } from './tools/confirm-column-match.ts'
import { quarantineApply, quarantineDecide, quarantineList } from './tools/quarantine.ts'
import { workflowApproveSubmit, workflowBoard, workflowCatalogue, workflowDraft, workflowRecord } from './tools/workflow.ts'
import { listMetrics } from './tools/list-metrics.ts'
import { profileBatch } from './tools/profile-batch.ts'
import { lookupFieldDictionary } from './tools/lookup-field-dictionary.ts'
import { batchSummary } from './tools/batch-summary.ts'
import { ApprovalReceipts } from './approval/receipts.ts'
import { PendingDetails } from './approval/detail.ts'
import { mountWeb } from './web.ts'
import { ApprovalNotes } from './approval/notes.ts'
import { mountReview, ReviewPolicy } from './tools/review-batch.ts'

export const name = 'bridgeflow'
export const inject = ['tools']

export interface Config {
  /** Base URL of the Python service that executes the tool bodies. */
  backendUrl: string
  /** Per-call timeout in milliseconds. */
  backendTimeoutMs: number
  /** How long a mutating tool may wait on a person before the ask fails closed. */
  decisionTimeoutMs: number
  approvalMode: 'native' | 'console'
  allowMappingWrite: boolean
  /** Recording people's answers and approving drafts (#144). Reads stay available when off. */
  allowWorkflowWrite: boolean
}

export const Config: Schema<Config> = Schema.object({
  backendUrl: Schema.string().default(DEFAULT_BACKEND.baseUrl),
  backendTimeoutMs: Schema.number().default(DEFAULT_BACKEND.timeoutMs),
  decisionTimeoutMs: Schema.number().default(DEFAULT_ANSWERER.decisionTimeoutMs),
  approvalMode: Schema.union(['native', 'console']).default('native'),
  allowMappingWrite: Schema.boolean().default(true),
  allowWorkflowWrite: Schema.boolean().default(true),
})

export function apply(ctx: Context, config: Config): void {
  const backend: BackendConfig = {
    baseUrl: config.backendUrl,
    timeoutMs: config.backendTimeoutMs,
  }

  const catalogue = new ToolCatalogue()

  // Registration is effect-based: disposing this plugin unregisters every tool.
  catalogue.register(ctx, listMetrics(backend))
  catalogue.register(ctx, profileBatch(backend))
  catalogue.register(ctx, columnCandidates(backend))
  catalogue.register(ctx, aggregateMetric(backend))
  catalogue.register(ctx, lookupFieldDictionary(backend))
  const receipts = new ApprovalReceipts()
  const notes = new ApprovalNotes()
  const details = new PendingDetails()
  const reviews = new ReviewPolicy()
  mountReview(ctx, backend, reviews, catalogue)
  catalogue.register(ctx, batchSummary(backend))
  if (config.allowMappingWrite) {
    catalogue.register(ctx, confirmMapping(backend, receipts))
    catalogue.register(ctx, confirmColumnMatch(backend, receipts))
    catalogue.register(ctx, quarantineDecide(backend, receipts))
    catalogue.register(ctx, quarantineApply(backend, receipts))
  }
  catalogue.register(ctx, quarantineList(backend))
  catalogue.register(ctx, workflowCatalogue(backend))
  catalogue.register(ctx, workflowDraft(backend))
  catalogue.register(ctx, workflowBoard(backend))
  if (config.allowWorkflowWrite) {
    catalogue.register(ctx, workflowRecord(backend, receipts))
    catalogue.register(ctx, workflowApproveSubmit(backend, receipts))
  }

  // Final deny applies even when a preset or a later policy exposes another tool.
  const nativeTools = new Set(['subagent', 'ask_user_question'])
  ctx.tools.guard(exec => {
    if (reviews.child(exec.agent)) return reviews.authorized(exec.agent) && exec.name === 'structured_output'
      ? undefined : 'Department reviewers may only submit their structured findings'
    return (catalogue.access(exec.name) || nativeTools.has(exec.name)) ? undefined : `Deployment policy does not authorize ${exec.name}`
  })
  mountWeb(ctx, backend, notes, config.decisionTimeoutMs, details)

  ctx.plugin(untrustedInput)
  ctx.plugin(approval, { ...backend, decisionTimeoutMs: config.decisionTimeoutMs,
    mode: config.approvalMode, receipts, notes, details, catalogue })
}
