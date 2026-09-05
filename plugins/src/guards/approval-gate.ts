import type { Context } from '@deepseek-ai/cordis'

/**
 * A human decision in front of anything that changes stored state.
 *
 * `sdk-minimal` composes no approval service at all, which is why bash ran
 * unchallenged before the shells were removed: there was no gate, rather than a gate
 * set to allow. `dsh/approval.patch.yml` loads one.
 *
 * Returning `ask` hands the question to that service rather than asking it here,
 * and the seam is fail-closed by construction: `ask` proceeds only on an explicit
 * `allowed-once`, and a missing, throwing or non-conforming answerer resolves to
 * `unavailable`, which denies (`docs/13` §7.3). So with no answerer composed this is
 * a deny-by-default — the right posture for an unattended run. The UI (#30) turns
 * that refusal into an actual decision; it does not create the safety.
 *
 * Read-only tools are deliberately not gated. Asking somebody to approve
 * `list_metrics` teaches them to approve without reading, which is worse than not
 * asking at all.
 */

/** Tools that change stored state, and therefore need a decision behind them. */
export const MUTATING_TOOLS: readonly string[] = ['confirm_mapping']

export const name = 'bridgeflow-approval-gate'
export const inject = ['tools']

export function apply(ctx: Context): void {
  ctx.on('tools/pre-execute', async (exec, next) => {
    if (!MUTATING_TOOLS.includes(exec.name)) return next()

    return {
      kind: 'ask',
      reason:
        `${exec.name} records a decision that will be reused next month and cited ` +
        `in an audit. It changes stored state; nothing is written without approval.`,
    }
  })
}
