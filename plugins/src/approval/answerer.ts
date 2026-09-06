import type { Context } from '@deepseek-ai/cordis'
// Imported for its module augmentation: this is what declares `approval/request`
// on cordis `Events`, and the `approval/asked` + `approval/decided` audit pair.
import type {} from '@deepseek-ai/dsh-user-approval/types'

import type { BackendConfig } from '../backend.ts'
import type { ApprovalDetail, PendingDetails } from './detail.ts'

/**
 * The listener that lets a person say yes.
 *
 * `ctx.approval` is a waterfall: a listener returns an outcome to claim the request,
 * or calls `next()` to delegate. With nothing composed the chain falls through to the
 * fail-closed `'unavailable'`, which denies — that is what #39 shipped and what the
 * live runtime was measured doing:
 *
 *     tool "confirm_mapping" requires approval, but no approval channel is available
 *
 * Correct, and not a human in the loop: nobody could say yes. This listener publishes
 * the question to the operator console (`GET /console`) and waits.
 *
 * **Every failure path delegates rather than decides.** A backend that is down, a
 * queue that is full, a console nobody is watching, an aborted turn — all of them
 * reach `next()`, which lands on `'unavailable'`, which denies. The only value that
 * can produce `'allowed-once'` is one a person clicked. That asymmetry is the whole
 * design: this plugin can turn a refusal into an approval only by way of a human, and
 * can never turn one into an approval by failing.
 */

/** Fields of the backend's `ApprovalQuestion` this side reads. */
interface Question {
  id: string
  state: 'pending' | 'decided' | 'withdrawn'
  outcome: 'allowed-once' | 'rejected' | null
}

export interface AnswererConfig extends BackendConfig {
  /**
   * How long a question may wait on a person before the answerer gives up.
   *
   * Giving up denies. The value is a judgement about the operator, not about safety:
   * too short and a reviewer who looked away loses the decision, too long and a tool
   * call blocks a turn nobody is watching.
   */
  decisionTimeoutMs: number
}

/** One blocking read, bounded so the abort signal and the deadline stay live. */
const POLL_SLICE_MS = 5_000

async function post<T>(config: AnswererConfig, path: string, body: unknown, signal: AbortSignal): Promise<T> {
  const response = await fetch(`${config.baseUrl}${path}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  if (!response.ok) throw new Error(`approval console ${response.status} on ${path}`)
  return (await response.json()) as T
}

export function answerer(ctx: Context, config: AnswererConfig, details: PendingDetails): void {
  ctx.on('approval/request', async (req, next) => {
    // An already-cancelled request has no one waiting; publishing it would put a
    // question on the console that can no longer authorise anything.
    if (req.signal?.aborted) return next()

    const detail: ApprovalDetail[] = details.take(req.callId)

    let question: Question
    try {
      question = await post<Question>(
        config,
        '/approvals/ask',
        { tool_name: req.toolName, call_id: req.callId ?? null, reason: req.reason ?? '', detail },
        AbortSignal.timeout(config.timeoutMs),
      )
    } catch {
      // No console, or a full queue. Delegating denies, which is the honest answer:
      // we could not put this in front of anybody.
      return next()
    }

    try {
      const deadline = Date.now() + config.decisionTimeoutMs
      while (Date.now() < deadline && !req.signal?.aborted) {
        const slice = Math.min(POLL_SLICE_MS, deadline - Date.now())
        const signals = [AbortSignal.timeout(slice + config.timeoutMs)]
        if (req.signal) signals.push(req.signal)

        let state: Question
        try {
          const response = await fetch(
            `${config.baseUrl}/approvals/${question.id}?wait_ms=${slice}`,
            { signal: AbortSignal.any(signals) },
          )
          if (!response.ok) return next()
          state = (await response.json()) as Question
        } catch {
          return next()
        }

        if (state.state === 'decided' && state.outcome) return state.outcome
        if (state.state !== 'pending') return next()
      }
      return next()
    } finally {
      // Withdraw on every exit, decided or not. A question left on the console after
      // its caller stopped waiting invites an operator to authorise a call that has
      // already failed — they would be approving something that is not there.
      await fetch(`${config.baseUrl}/approvals/${question.id}`, {
        method: 'DELETE',
        signal: AbortSignal.timeout(config.timeoutMs),
      }).catch(() => undefined)
    }
  })
}
