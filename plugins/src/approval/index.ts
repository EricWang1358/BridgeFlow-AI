import type { ToolCatalogue } from '../tool-catalogue.ts'
import type { Context } from '@deepseek-ai/cordis'

import { DEFAULT_BACKEND } from '../backend.ts'
import type { AnswererConfig } from './answerer.ts'
import { answerer } from './answerer.ts'
import { PendingDetails } from './detail.ts'
import { gate } from './gate.ts'
import type { ApprovalReceipts } from './receipts.ts'
import type { ApprovalNotes } from './notes.ts'

/**
 * The escalation checkpoint, both halves (#30).
 *
 * The gate decides *that* a question must be asked; the answerer decides *who* is
 * asked. They ship as one plugin because they share the argument summary the operator
 * reads, and because that summary must not outlive them: a stale entry attached to a
 * later call would show a person the wrong thing while they authorise something else.
 */

export const name = 'bridgeflow-approval'
// `approval` is what lets the gate ask through the service and therefore word the
// denial; `tools` is the gate itself.
export const inject = ['tools', 'approval']

export function apply(ctx: Context, config: AnswererConfig & { mode: 'native' | 'console'; receipts: ApprovalReceipts; notes: ApprovalNotes; catalogue: ToolCatalogue; details?: PendingDetails }): void {
  // Web cards and the console answerer share the same pending summaries.
  const details = config.details ?? new PendingDetails()
  gate(ctx, details, config.receipts, config.decisionTimeoutMs, config.notes, config.catalogue)
  if (config.mode === 'console') answerer(ctx, config, details)
}

/** Defaults used when the composing plugin does not override them. */
export const DEFAULT_ANSWERER: AnswererConfig = {
  ...DEFAULT_BACKEND,
  // Long enough that a reviewer can read the evidence and think; short enough that a
  // run left alone fails closed rather than hanging until somebody notices.
  decisionTimeoutMs: 300_000,
}
