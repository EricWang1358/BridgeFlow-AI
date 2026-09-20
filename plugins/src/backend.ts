/**
 * The one place that knows how to reach Python.
 *
 * Tool declarations live here in TypeScript because that is the only side of the
 * runtime boundary that can declare them: the Python SDK is a JSON-RPC client with
 * no tool surface at all. The bodies stay in Python because that is where pandas is,
 * and where the rules-compute work of issue #13 belongs.
 */

import { actors } from './actor.ts'

/** Where the Python side listens. Configurable because two deployments differ. */
export interface BackendConfig {
  /** Base URL of the BridgeFlow FastAPI service. */
  baseUrl: string
  /** Per-call timeout. A hung backend must not hang the agent turn. */
  timeoutMs: number
}

export const DEFAULT_BACKEND: BackendConfig = {
  baseUrl: 'http://127.0.0.1:8000',
  timeoutMs: 30_000,
}

/** Raised when Python answered, but with a refusal we should show the model. */
export class BackendRefusal extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'BackendRefusal'
  }
}

/**
 * What the host knows about the call being made, for the decision journal.
 *
 * `rootCallId` is the model-requested call that owns the whole execution tree, which is
 * exactly the grouping a person means by "one run": the captain's step and every
 * department subagent's call underneath it carry the same root. Passing `exec` instead of
 * `exec.signal` is what turns the backend's journal from a list of requests into the
 * agent's own trace, and it costs one word at each call site.
 */
export type CallContext = {
  readonly signal: AbortSignal
  readonly callId?: unknown
  readonly rootCallId?: unknown
  readonly name?: string
  readonly agent?: { readonly id?: unknown } | undefined
}

function traceHeaders(from: AbortSignal | CallContext): Record<string, string> {
  if (from instanceof AbortSignal || !('callId' in from || 'agent' in from)) return {}
  const context = from as CallContext
  const header = (value: unknown) => (value === undefined || value === null ? '' : String(value))
  return Object.fromEntries(Object.entries({
    'x-bridgeflow-call': header(context.callId),
    'x-bridgeflow-root': header(context.rootCallId ?? context.callId),
    'x-bridgeflow-agent': header(context.agent?.id),
    'x-bridgeflow-tool': header(context.name),
  }).filter(([, value]) => value !== ''))
}

/**
 * What this call is about, declared by the caller rather than parsed out of its body.
 *
 * A tool's subject lives in its body (`batch_id`, `period`), and the journal's seam
 * deliberately never reads bodies — so the caller states it here. Only these two keys, and
 * only when they are plain strings: nothing else can ride along.
 */
function subjectHeaders(body: unknown): Record<string, string> {
  if (typeof body !== 'object' || body === null) return {}
  const record = body as Record<string, unknown>
  const pick = (key: string) => (typeof record[key] === 'string' && record[key] ? String(record[key]) : '')
  return Object.fromEntries(Object.entries({
    'x-bridgeflow-batch': pick('batch_id'),
    'x-bridgeflow-period': pick('period'),
  }).filter(([, value]) => value !== ''))
}

/**
 * Call one tool endpoint on the Python side.
 *
 * The fourth argument is the tool's `exec` (or just its signal): when the caller cancels,
 * the HTTP request is aborted rather than left running, and the deadline is layered on top
 * so a backend that accepts the connection and then stalls still fails. Handing over the
 * whole `exec` also lets the call be journalled as part of its run.
 */
export async function callBackend<T>(
  config: BackendConfig,
  path: string,
  body: unknown,
  execution: AbortSignal | CallContext,
  approvalReceipt?: string,
): Promise<T> {
  const signal = execution instanceof AbortSignal ? execution : execution.signal
  const deadline = AbortSignal.timeout(config.timeoutMs)
  const combined = AbortSignal.any([signal, deadline])

  let response: Response
  try {
    response = await fetch(`${config.baseUrl}${path}`, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        // Transport credential: it proves the call comes from this host process. It is
        // no longer the identity — that rides in x-bridgeflow-user below and is verified
        // per request by the backend (issue #231, src/actor.ts).
        authorization: `Bearer ${process.env.BRIDGEFLOW_SERVICE_TOKEN ?? ''}`,
        ...(approvalReceipt ? { 'x-bridgeflow-approval': approvalReceipt } : {}),
        ...traceHeaders(execution),
        ...subjectHeaders(body),
        // Whose turn this read belongs to, when that is unambiguous. Absent when
        // nobody is bound, everybody's token expired, or two people are bound at
        // once — a wrong name is worse than no name (src/actor.ts).
        ...actors.header(),
      },
      body: JSON.stringify(body),
      signal: combined,
    })
  } catch (cause) {
    if (signal.aborted) throw cause
    throw new Error(
      `BridgeFlow backend unreachable at ${config.baseUrl}${path}. ` +
        `Start it with: uvicorn bridgeflow.api.main:app`,
      { cause },
    )
  }

  if (response.status === 409) {
    // The backend refused on domain grounds — a missing field dictionary, an
    // unresolved join key. That is an answer, not an infrastructure failure, so it
    // reaches the model as a refusal it can reason about.
    const refusal = (await response.json().catch(() => ({}))) as { detail?: string }
    throw new BackendRefusal(refusal.detail ?? `${path} refused without a reason`)
  }
  if (!response.ok) {
    throw new Error(`BridgeFlow backend ${response.status} on ${path}: ${await response.text()}`)
  }
  return (await response.json()) as T
}
