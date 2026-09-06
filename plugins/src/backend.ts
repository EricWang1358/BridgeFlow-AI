/**
 * The one place that knows how to reach Python.
 *
 * Tool declarations live here in TypeScript because that is the only side of the
 * runtime boundary that can declare them: the Python SDK is a JSON-RPC client with
 * no tool surface at all. The bodies stay in Python because that is where pandas is,
 * and where the rules-compute work of issue #13 belongs.
 */

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
 * Call one tool endpoint on the Python side.
 *
 * `signal` is the tool's `exec.signal`: when the caller cancels, the HTTP request
 * is aborted rather than left running. The deadline is layered on top so a backend
 * that accepts the connection and then stalls still fails.
 */
export async function callBackend<T>(
  config: BackendConfig,
  path: string,
  body: unknown,
  signal: AbortSignal,
  approvalReceipt?: string,
): Promise<T> {
  const deadline = AbortSignal.timeout(config.timeoutMs)
  const combined = AbortSignal.any([signal, deadline])

  let response: Response
  try {
    response = await fetch(`${config.baseUrl}${path}`, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        authorization: `Bearer ${process.env.BRIDGEFLOW_SERVICE_TOKEN ?? ''}`,
        ...(approvalReceipt ? { 'x-bridgeflow-approval': approvalReceipt } : {}),
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
