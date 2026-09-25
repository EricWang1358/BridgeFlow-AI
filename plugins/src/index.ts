import { discoveryDecisionTools } from './tools/discovery-decision.ts'
import { discoveryMeetingSave } from './tools/discovery-meeting.ts'
import { discoveryScoreSave } from './tools/discovery-score.ts'
import { discoveryGraphSave } from './tools/discovery-graph.ts'
import { discoveryMaterials, discoveryPropose, discoveryRegister } from './tools/discovery.ts'
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
import { feishuImport, feishuUploadReport } from './tools/feishu.ts'
import { integrationSummary } from './tools/integration.ts'
import { checklistTool, inboxTool } from './tools/checklist.ts'
import { conventionDecide, conventionList, conventionPreview } from './tools/conventions.ts'
import { appGuide } from './tools/app-guide.ts'
import { riskDispositionRecord, riskDispositions } from './tools/dispositions.ts'
import { quarantineApply, quarantineDecide, quarantineList } from './tools/quarantine.ts'
import { workflowAcceptScope, workflowApproveSubmit, workflowBoard, workflowCatalogue, workflowDraft, workflowGuidance, workflowHandoff, workflowRecord, workflowScope } from './tools/workflow.ts'
import { listMetrics } from './tools/list-metrics.ts'
import { profileBatch } from './tools/profile-batch.ts'
import { lookupFieldDictionary } from './tools/lookup-field-dictionary.ts'
import { dictionaryDecide, dictionaryDraft, dictionaryDraftView, dictionaryImport, dictionaryProfiles, dictionaryPublish } from './tools/dictionary.ts'
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
  catalogue.register(ctx, appGuide())
  const receipts = new ApprovalReceipts()
  const notes = new ApprovalNotes()
  const details = new PendingDetails()
  const reviews = new ReviewPolicy()
  mountReview(ctx, backend, reviews, catalogue)
  catalogue.register(ctx, batchSummary(backend))
  if (config.allowMappingWrite) {
    catalogue.register(ctx, confirmMapping(backend, receipts))
    catalogue.register(ctx, confirmColumnMatch(backend, receipts))
    catalogue.register(ctx, dictionaryImport(backend, receipts))
    catalogue.register(ctx, dictionaryDraft(backend, receipts))
    catalogue.register(ctx, dictionaryDecide(backend, receipts))
    catalogue.register(ctx, dictionaryPublish(backend, receipts))
    catalogue.register(ctx, quarantineDecide(backend, receipts))
    catalogue.register(ctx, quarantineApply(backend, receipts))
    catalogue.register(ctx, conventionDecide(backend, receipts))
    catalogue.register(ctx, riskDispositionRecord(backend, receipts))
  }
  catalogue.register(ctx, dictionaryProfiles(backend))
  catalogue.register(ctx, dictionaryDraftView(backend))
  catalogue.register(ctx, quarantineList(backend))
  catalogue.register(ctx, conventionList(backend))
  catalogue.register(ctx, conventionPreview(backend))
  catalogue.register(ctx, checklistTool(backend))
  catalogue.register(ctx, inboxTool(backend))
  catalogue.register(ctx, riskDispositions(backend))
  catalogue.register(ctx, integrationSummary(backend))
  catalogue.register(ctx, workflowCatalogue(backend))
  catalogue.register(ctx, workflowDraft(backend))
  catalogue.register(ctx, workflowBoard(backend))
  catalogue.register(ctx, workflowGuidance(backend))
  catalogue.register(ctx, workflowScope(backend))
  catalogue.register(ctx, discoveryMaterials(backend))
  if (config.allowWorkflowWrite) {
    catalogue.register(ctx, discoveryPropose(backend, receipts))
    catalogue.register(ctx, discoveryRegister(backend, receipts))
    catalogue.register(ctx, discoveryGraphSave(backend, receipts))
    catalogue.register(ctx, discoveryScoreSave(backend, receipts))
    catalogue.register(ctx, discoveryMeetingSave(backend, receipts))
    for (const tool of discoveryDecisionTools(backend, receipts)) catalogue.register(ctx, tool)
    catalogue.register(ctx, workflowRecord(backend, receipts))
    catalogue.register(ctx, workflowApproveSubmit(backend, receipts))
    catalogue.register(ctx, workflowHandoff(backend, receipts))
    catalogue.register(ctx, workflowAcceptScope(backend, receipts))
    // Guest mode never talks to Feishu: the tools are not offered at all (docs/22 §9e).
    if (process.env.BRIDGEFLOW_GUEST_MODE !== '1') {
      catalogue.register(ctx, feishuImport(backend, receipts))
      catalogue.register(ctx, feishuUploadReport(backend, receipts))
    }
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
