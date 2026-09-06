import type { Context } from '@deepseek-ai/cordis'
// Imported for its module augmentation: this is what declares `ctx.approval` (the
// request API the gate asks through) on the cordis `Context`.
import type {} from '@deepseek-ai/dsh-user-approval'

import type { PendingDetails } from './detail.ts'

/**
 * A human decision in front of anything that changes stored state.
 *
 * `sdk-minimal` composes no approval service at all, which is why bash ran
 * unchallenged before the shells were removed: there was no gate, rather than a gate
 * set to allow. `dsh/approval.patch.yml` loads one.
 *
 * Read-only tools are deliberately not gated. Asking somebody to approve
 * `list_metrics` teaches them to approve without reading, which is worse than not
 * asking at all.
 *
 * ## Why this asks the service rather than returning `ask`
 *
 * Returning `ask` hands the question over and takes back a decision the framework
 * words for us: the model receives exactly
 *
 *     Error: the user rejected tool "confirm_mapping"
 *
 * which is true, minimal, and — measured twice on this project — enough for a model
 * to answer "done" (#86). Nothing in it carries what the operator actually objected
 * to, because that message is a constant: a reason has nowhere to go once the
 * decision is out of our hands.
 *
 * Asking through `ctx.approval.request` keeps everything the `ask` path gave us —
 * the same session policy (`never` still rejects without prompting, so CI is
 * unaffected), the same `approval/asked` + `approval/decided` audit pair, the same
 * fail-closed answerer chain — and additionally lets us write the denial the model
 * reads. That is the difference between a rejection that is merely recorded and one
 * that reaches the narration.
 *
 * The grant is still the only value that permits the call. Every other outcome,
 * including the ones meaning "nobody answered", ends in a deny from here.
 */

/** Tools that change stored state, and therefore need a decision behind them. */
export const MUTATING_TOOLS: readonly string[] = ['confirm_mapping']

/** The only outcome that permits the call (`docs/13` §7.3). */
const GRANT = 'allowed-once'

/** What the operator sees before deciding. Ours, because we know what the tool does. */
function askReason(toolName: string): string {
  return (
    `${toolName} records a decision that will be reused next month and cited in an ` +
    `audit. It changes stored state; nothing is written without approval.`
  )
}

/**
 * The sentence the model reads when a call does not happen.
 *
 * Three jobs, in the order they tend to get forgotten: say nothing was written, say
 * why in the operator's own words if they gave any, and forbid the tidy ending. The
 * framework's constant cannot do this because it has no reason to carry, and a
 * denial an agent reports as success is the worst combination available — the safety
 * worked, and the record lies about it.
 */
function denialReason(toolName: string, outcome: string, note?: string): string {
  // Clauses joined, not concatenated: a sentence assembled from parts cannot come
  // out missing a full stop between "a person refused" and what follows, which is
  // exactly what the first version of this function did.
  const clauses: string[] = [
    outcome === 'unavailable'
      ? `${toolName} did NOT run: nobody was available to decide, so it was refused rather than assumed`
      : outcome === 'cancelled'
        ? `${toolName} did NOT run: the question was withdrawn before anybody answered`
        : `${toolName} did NOT run: a person reviewed it and refused`,
  ]

  // Quoted rather than paraphrased: a model that summarises an objection tends to
  // turn it into whatever it was already about to do.
  if (note) clauses.push(`The reviewer said: "${note}"`)
  clauses.push('Nothing was written, and the decision is not remembered for next month')
  clauses.push('Say plainly that this step did not happen and why')
  clauses.push('Do not describe it as done, and do not re-ask within this turn')

  return `${clauses.join('. ')}.`
}

export function gate(ctx: Context, details: PendingDetails): void {
  ctx.on('tools/pre-execute', async (exec, next) => {
    if (!MUTATING_TOOLS.includes(exec.name)) return next()

    // The approval request carries no arguments, so the summary is stashed here and
    // collected by the answerer. Without it the operator is asked to approve a tool
    // name, which is a signature on a blank page.
    details.record(exec.callId, exec.arguments)

    const agent = exec.agent
    if (!agent) {
      // The audit pair belongs to one agent's session, and answerers route by agent.
      // With neither there is nothing to attribute a decision to, so there is no
      // decision to honour: denying is the fail-closed answer and proceeding would be
      // the anonymous write.
      details.discard(exec.callId)
      return {
        kind: 'deny',
        reason:
          `${exec.name} was refused: the call carries no agent, so its approval could ` +
          'not be attributed or audited. Nothing was written. No retry.',
      }
    }

    let outcome: string
    try {
      outcome = await ctx.approval.request({
        agent,
        toolName: exec.name,
        callId: exec.callId,
        reason: askReason(exec.name),
        signal: exec.signal,
      })
    } catch (error) {
      // The service will not ask without committing the audit pair, so an exception
      // here means no logged decision exists. Deny, and say that rather than
      // implying a person refused when nobody was asked.
      details.discard(exec.callId)
      return {
        kind: 'deny',
        reason:
          `${exec.name} was refused: the approval could not be recorded ` +
          `(${String(error)}). An unlogged decision is not a decision. No retry.`,
      }
    }

    // Read the note *before* discarding: discard clears the note along with the
    // summary, and the note is the one thing this denial has to carry. Measured —
    // the first version discarded first and the reviewer's reason never arrived.
    const note = details.takeNote(exec.callId)
    details.discard(exec.callId)

    if (outcome === GRANT) return { kind: 'allow' }
    return { kind: 'deny', reason: denialReason(exec.name, outcome, note) }
  })
}
