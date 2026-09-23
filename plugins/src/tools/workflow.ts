import { withAccess, type ProductTool } from '../tool-catalogue.ts'
import { defineTool } from '@deepseek-ai/dsh-tools'

import { callBackend, type BackendConfig } from '../backend.ts'
import type { ApprovalReceipts } from '../approval/receipts.ts'

/**
 * Tools for helping a person turn what they have into an approved standard record (#144).
 *
 * The captain's job here is a conversation, not a calculation: read which questions a
 * draft still has, ask the person, relay their answers, show them the result and let
 * them approve it. Everything that decides — normalisation, conflicts, required
 * evidence, state, submission, who downstream is told — happens on the host
 * (`backend/src/bridgeflow/workflow/`, `docs/25`).
 *
 * Mutations are approval-gated because they record human decisions:
 *
 * - `workflow_record` relays what the person said. The approval card lists each value,
 *   so the person confirms the model heard them right. The host records the source
 *   as this conversation whatever the model claims.
 * - `workflow_approve_submit` is the reviewer's decision on exact values, bound by
 *   digest; if the values changed since they were shown, it is refused.
 * - `workflow_handoff` records a downstream action against the displayed sequence.
 */

/** Draft as the host shapes it for a model: state, open questions, one record's values. */
export interface WorkflowDraft {
  artifact_id: string
  template: string
  title: string
  department: string
  state: string
  version: number
  seq: number
  digest: string
  values: Record<string, string>
  open_questions: { kind: string; field: string; question: string; why: string; candidates: { value: string; from: string }[] }[]
  notices: string[]
  checks: { title: string; value: string; unit: string; attention: boolean }[]
  /** Present once the target system accepted the record. */
  receipt?: Record<string, string | boolean>
  next_step: string
}

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue }

const draftSchema = {
  type: 'object',
  properties: {
    artifact_id: { type: 'string', required: true },
    template: { type: 'string' }, title: { type: 'string' }, department: { type: 'string' },
    state: { type: 'string', required: true },
    version: { type: 'number' }, seq: { type: 'number', required: true }, digest: { type: 'string', required: true },
    values: { type: 'object', additionalProperties: true },
    open_questions: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          kind: { type: 'string' }, field: { type: 'string' }, question: { type: 'string' }, why: { type: 'string' },
          candidates: {
            type: 'array',
            items: { type: 'object', properties: { value: { type: 'string' }, from: { type: 'string' } }, additionalProperties: false },
          },
        },
        additionalProperties: false,
      },
    },
    notices: { type: 'array', items: { type: 'string' } },
    checks: {
      type: 'array',
      items: {
        type: 'object',
        properties: { title: { type: 'string' }, value: { type: 'string' }, unit: { type: 'string' }, attention: { type: 'boolean' } },
        additionalProperties: false,
      },
    },
    receipt: { type: 'object', additionalProperties: true },
    next_step: { type: 'string' },
  },
  additionalProperties: false,
} as const

/** What rendering reads; structural so it accepts the schema-inferred value. */
interface DraftText {
  artifact_id?: string; seq?: number; digest?: string; values?: Record<string, unknown>
  department?: string; title?: string; version?: number; state?: string; next_step?: string
  open_questions?: { field?: string; kind?: string; question?: string; why?: string }[]
  checks?: { title?: string; value?: string; unit?: string; attention?: boolean }[]
}

/**
 * What the model reads of a draft. The render is all the model sees, so it must carry what
 * the next call needs: `workflow_record` takes the draft's seq, `workflow_approve_submit` its
 * digest and seq. Leaving them out made every submit impossible for a real model — the
 * scripted test model read the raw value and never noticed. The values are one record's
 * fields, as the person gave them, so the person can be shown exactly what they approve.
 */
export function renderDraft(value: DraftText) {
  const questions = value.open_questions ?? []
  const checks = (value.checks ?? []).filter(c => c.attention).map(c => `${c.title} ${c.value}${c.unit}`)
  const values = Object.entries(value.values ?? {}).slice(0, 40).map(([label, v]) => `${label}=${String(v)}`)
  return [{
    type: 'text' as const,
    text:
      `artifact_id=${value.artifact_id ?? ''} seq=${value.seq ?? ''} digest=${value.digest ?? ''}. ` +
      `${value.department ?? ''}「${value.title ?? ''}」v${value.version ?? 1}: ${value.state}. ` +
      (values.length ? `Values: ${values.join('; ')}. ` : '') +
      (questions.length
        ? `Open questions: ${questions.map(q => `${q.field || q.kind} — ${q.question || q.why}`).join('; ')}. `
        : 'No open questions. ') +
      (checks.length ? `Needs attention: ${checks.join('; ')}. ` : '') +
      (value.next_step ?? ''),
  }]
}

const saidParameter = {
  type: 'array',
  required: true,
  description: 'Exactly what the person said, one field per item. Never a value you inferred or computed.',
  items: {
    type: 'object',
    properties: {
      label: { type: 'string', required: true, description: 'The field label or the wording the person used' },
      value: { type: 'string', required: true, description: 'The value as the person gave it, units included' },
      evidence: { type: 'string', description: 'A reference the person gave for this value, if any' },
    },
    additionalProperties: false,
  },
} as const

type Said = { label: string; value: string; evidence: string }

function said(value: unknown): Said[] {
  return (Array.isArray(value) ? value : []).map((item: Record<string, unknown>) => ({
    label: String(item?.label ?? ''), value: String(item?.value ?? ''), evidence: String(item?.evidence ?? ''),
  }))
}

/** Identical bodies at approval and dispatch; changing one value invalidates the receipt. */
export function recordBody(args: Record<string, unknown>, agentId: string, callId: string | undefined) {
  return args.artifact_id
    ? { artifact_id: args.artifact_id, expected_seq: args.expected_seq, said: said(args.said), confirmed_by: agentId, call_id: callId ?? null }
    : { template: args.template, said: said(args.said), confirmed_by: agentId, call_id: callId ?? null }
}

export function approveBody(args: Record<string, unknown>, agentId: string, callId: string | undefined) {
  return { artifact_id: args.artifact_id, digest: args.digest, expected_seq: args.expected_seq, confirmed_by: agentId, call_id: callId ?? null }
}

export function workflowCatalogue(config: BackendConfig): ProductTool {
  return withAccess(defineTool({
    name: 'workflow_catalogue',
    description:
      'List the approved templates people fill in, their fields (label, required, unit, whether evidence is needed) ' +
      'and the stages that receive them. Use it to know which template applies before recording anything. ' +
      'Only templates with status approved accept data.',
    parameters: {},
    output: {
      schema: { type: 'object', additionalProperties: true },
      render: (_args, value) => [{
        type: 'text',
        text: `Templates: ${((value as { templates?: { template: string; title: string; status: string }[] }).templates ?? [])
          .map(t => `${t.template} (${t.title}, ${t.status})`).join('; ')}`,
      }],
    },
    async execute(_args, exec) {
      return callBackend<Record<string, JsonValue>>(config, '/tools/workflow-catalogue', {}, exec)
    },
  }), { kind: 'read' })
}

export function workflowDraft(config: BackendConfig): ProductTool {
  return withAccess(defineTool({
    name: 'workflow_draft',
    description: 'Read one draft: its state, the questions still open, its values and checks, and the next step.',
    parameters: { artifact_id: { type: 'string', required: true, description: 'Draft id from workflow_record' } },
    output: { schema: draftSchema, render: (_args, value) => renderDraft(value) },
    async execute(args, exec) {
      return callBackend<WorkflowDraft>(config, '/tools/workflow-draft', { artifact_id: args.artifact_id }, exec)
    },
  }), { kind: 'read' })
}

interface BoardText {
  rows?: { kind?: string; id?: string; seq?: number; state?: string; summary: string; stale?: boolean; inputs?: Record<string, number>; awaiting_outputs?: string[] }[]
  truncated?: boolean; total?: number
}
/** One line per row, led by the id and seq that `workflow_draft` / `workflow_handoff` need. */
export function renderBoard(board: BoardText) {
  const rows = (board.rows ?? []).map(r => (r.id ? `[${r.kind} id=${r.id} seq=${r.seq} state=${r.state}${r.stale ? ' stale' : ''}] ` : `[${r.kind}] `)
    + r.summary + (r.inputs ? ` inputs=${JSON.stringify(r.inputs)}` : '') + (r.awaiting_outputs?.length ? ` cannot_complete_until_recorded=${r.awaiting_outputs.join(',')}` : ''))
  const more = board.truncated ? ` (showing the latest ${rows.length} of ${board.total})` : ''
  return [{ type: 'text' as const, text: rows.length ? rows.join(' | ') + more : 'Nothing recorded yet.' }]
}

export function workflowBoard(config: BackendConfig): ProductTool {
  return withAccess(defineTool({
    name: 'workflow_board',
    description:
      'Status summaries: what each department has submitted, what is ready, who it waits on, and whether ' +
      'downstream was notified. Received is not ready, ready is not notified, notified is not done.',
    parameters: {},
    output: {
      schema: { type: 'object', additionalProperties: true },
      render: (_args, value) => renderBoard(value as BoardText),
    },
    async execute(_args, exec) {
      return callBackend<Record<string, JsonValue>>(config, '/tools/workflow-board', {}, exec)
    },
  }), { kind: 'read' })
}

export function workflowRecord(config: BackendConfig, receipts: ApprovalReceipts): ProductTool {
  return withAccess(defineTool({
    name: 'workflow_record',
    description:
      'Record what the person told you. Without artifact_id it starts a draft for `template`; with artifact_id ' +
      'it answers that draft\'s open questions (pass expected_seq from the draft you read). ' +
      'Relay their words only — never a value you guessed, copied from another field, or calculated. ' +
      'The person confirms each value in the approval. Returns the updated draft and its open questions.',
    parameters: {
      template: { type: 'string', description: 'Template to start a draft for (from workflow_catalogue)' },
      artifact_id: { type: 'string', description: 'Existing draft to answer' },
      expected_seq: { type: 'number', description: 'seq of the draft you last read; required with artifact_id' },
      said: saidParameter,
    },
    output: { schema: draftSchema, render: (_args, value) => renderDraft(value) },
    async execute(args, exec) {
      const path = args.artifact_id ? '/tools/workflow-answer' : '/tools/workflow-receive'
      return callBackend<WorkflowDraft>(
        config, path, recordBody(args, exec.agent?.id ?? 'unknown-agent', exec.callId), exec,
        receipts.take(JSON.stringify([exec.agent?.id, exec.callId])))
    },
  }), {
    kind: 'approval',
    reason: 'Record these values as what the person said. Check each one; nothing is written without approval.',
    denialEffect: 'Nothing was recorded. Ask the person to restate the values; do NOT claim they were saved',
    body: recordBody,
  })
}

export function workflowApproveSubmit(config: BackendConfig, receipts: ApprovalReceipts): ProductTool {
  return withAccess(defineTool({
    name: 'workflow_approve_submit',
    description:
      'The reviewer approves the draft\'s current values (identified by digest) and they are submitted to the ' +
      'target system. Only call after showing the person the values and checks from workflow_draft. ' +
      'If the values changed since, this is refused; read the draft again.',
    parameters: {
      artifact_id: { type: 'string', required: true, description: 'Draft to approve' },
      digest: { type: 'string', required: true, description: 'digest from the draft that was shown' },
      expected_seq: { type: 'number', required: true, description: 'seq from the draft that was shown' },
    },
    output: { schema: draftSchema, render: (_args, value) => renderDraft(value) },
    async execute(args, exec) {
      return callBackend<WorkflowDraft>(
        config, '/tools/workflow-approve-submit', approveBody(args, exec.agent?.id ?? 'unknown-agent', exec.callId),
        exec, receipts.take(JSON.stringify([exec.agent?.id, exec.callId])))
    },
  }), {
    kind: 'approval',
    reason: 'Approve these exact values and submit them to the target system.',
    denialEffect: 'Nothing was approved or submitted; the draft is unchanged. Do NOT tell anyone the data is ready',
    body: approveBody,
  })
}

export function handoffBody(args: Record<string, unknown>, agentId: string, callId: string | undefined) {
  return { handoff_id: args.handoff_id, action: args.action, expected_seq: args.expected_seq,
    reason: args.reason ?? '', confirmed_by: agentId, call_id: callId ?? null }
}

export function workflowHandoff(config: BackendConfig, receipts: ApprovalReceipts): ProductTool {
  return withAccess(defineTool({
    name: 'workflow_handoff',
    description: 'Record an explicitly confirmed downstream action. Read workflow_board first for the handoff id, ' +
      'seq, inputs and stale flag. A return requires a reason. A revised upstream input must be ready and ' +
      'acknowledged before starting or completing. Notification delivery never completes work.',
    parameters: {
      handoff_id: { type: 'string', required: true, description: 'Handoff id from workflow_board' },
      action: { type: 'string', enum: ['start', 'return', 'complete', 'acknowledge'], required: true },
      expected_seq: { type: 'number', required: true, description: 'Sequence from the displayed handoff' },
      reason: { type: 'string', description: 'Actionable explanation; required when returning work' },
    },
    output: {
      schema: { type: 'object', additionalProperties: true },
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value) }],
    },
    async execute(args, exec) {
      return callBackend<Record<string, JsonValue>>(config, '/tools/workflow-handoff',
        handoffBody(args, exec.agent?.id ?? 'unknown-agent', exec.callId), exec,
        receipts.take(JSON.stringify([exec.agent?.id, exec.callId])))
    },
  }), {
    kind: 'approval',
    reason: 'Confirm this downstream action on the displayed handoff version.',
    denialEffect: 'The downstream state did not change. Do NOT claim work started, returned or completed',
    body: handoffBody,
  })
}

export function workflowGuidance(config: BackendConfig): ProductTool {
  return withAccess(defineTool({
    name: 'workflow_guidance',
    description: 'Read role guidance for one declared stage: entry, templates, destination, receipt, status and ' +
      'support role. Missing contacts remain unconfigured. This does not grant permissions or assign people.',
    parameters: { stage: { type: 'string', required: true, description: 'Stage id from workflow_catalogue' } },
    output: {
      schema: { type: 'object', additionalProperties: true },
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value) }],
    },
    async execute(args, exec) {
      return callBackend<Record<string, JsonValue>>(config, '/tools/workflow-guidance', { stage: args.stage }, exec)
    },
  }), { kind: 'read' })
}

type ScopeText = { accepted: { project_id: string; decision_id: string; decision_seq: number; scope: string[]; exclusions: string[]; by?: string; accepted_at?: string } | null
  current: boolean; stale_reasons: string[]; runnable_candidates: string[]
  pending?: { project_id: string; decision_id: string; decision_seq: number; scope: string[]; candidates: string[] }[]; next_step?: string }
/** The accepted scope and any approved decision waiting, led by the ids and seq acceptance takes. */
export function renderScope(value: ScopeText) {
  const lines = [value.accepted
    ? `Accepted: ${value.accepted.project_id}/${value.accepted.decision_id} v${value.accepted.decision_seq} by ${value.accepted.by || '—'}; `
      + `${value.current ? 'current' : `STALE (${value.stale_reasons.join(', ')})`}. Scope: ${value.accepted.scope.join('; ')}. `
      + `Exclusions: ${value.accepted.exclusions.join('; ') || 'none'}.`
    : `No MVP decision accepted yet; this catalogue can run: ${value.runnable_candidates.join(', ') || 'nothing'}.`]
  for (const p of value.pending ?? []) lines.push(`Waiting: project_id=${p.project_id} decision_id=${p.decision_id} decision_seq=${p.decision_seq} `
    + `candidates=${p.candidates.join(',')} scope: ${p.scope.join('; ')}`)
  if (value.next_step) lines.push(value.next_step)
  return [{ type: 'text' as const, text: lines.join('\n') }]
}

export function workflowScope(config: BackendConfig): ProductTool {
  return withAccess(defineTool({
    name: 'workflow_scope',
    description: 'Which approved MVP decision from discovery the workflow runs under, whether it is still current, and ' +
      'approved decisions waiting to be accepted (with the decision_seq acceptance needs). Read this before workflow_accept_scope.',
    parameters: {},
    output: { schema: { type: 'object', additionalProperties: true }, render: (_args, value) => renderScope(value as ScopeText) },
    async execute(_args, exec) {
      return callBackend<Record<string, JsonValue>>(config, '/tools/workflow-scope', {}, exec)
    },
  }), { kind: 'read' })
}

export function scopeBody(args: Record<string, unknown>, agentId: string, callId: string | undefined) {
  return { project_id: args.project_id, decision_id: args.decision_id, decision_seq: args.decision_seq,
    confirmed_by: agentId, call_id: callId ?? null }
}

export function workflowAcceptScope(config: BackendConfig, receipts: ApprovalReceipts): ProductTool {
  return withAccess(defineTool({
    name: 'workflow_accept_scope',
    description: 'A person accepts an approved MVP decision (from workflow_scope) as the scope the workflow runs under. ' +
      'The host re-reads the decision: it must still be approved at decision_seq, and its candidates must be scenarios ' +
      'the catalogue can run. Show the scope and exclusions first; the approval card is the person\'s decision.',
    parameters: {
      project_id: { type: 'string', required: true, description: 'project_id from workflow_scope' },
      decision_id: { type: 'string', required: true, description: 'decision_id from workflow_scope' },
      decision_seq: { type: 'number', required: true, description: 'decision_seq from workflow_scope' },
    },
    output: { schema: { type: 'object', additionalProperties: true }, render: (_args, value) => renderScope(value as ScopeText) },
    async execute(args, exec) {
      return callBackend<Record<string, JsonValue>>(config, '/tools/workflow-accept-scope',
        scopeBody(args, exec.agent?.id ?? 'unknown-agent', exec.callId), exec,
        receipts.take(JSON.stringify([exec.agent?.id, exec.callId])))
    },
  }), {
    kind: 'approval',
    reason: 'Accept this approved MVP decision as the scope the filling-and-handoff workflow runs under.',
    denialEffect: 'Nothing was accepted; the workflow scope is unchanged. Do NOT describe the decision as accepted',
    body: scopeBody,
  })
}
