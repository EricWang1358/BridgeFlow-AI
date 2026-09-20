/**
 * Which person a model-initiated read belongs to (issue #231).
 *
 * The problem this solves: a tool call made by the model has no browser behind it,
 * so it used to reach the backend with the host's own `BRIDGEFLOW_SERVICE_TOKEN` and
 * nothing else. The audit could prove that a read happened; it could not say whose
 * turn caused it. That is fine for one operator and wrong for a shared console.
 *
 * The fix is not for the host to *assert* a name — the host asserting identity is
 * the same trust as before with a label on it. Instead the browser hands over the
 * portal token it already holds, the host has the backend verify it once, and from
 * then on relays that same token on the calls the model triggers. The backend
 * verifies the signature per request exactly as it does for a browser call, so
 * `BRIDGEFLOW_SERVICE_TOKEN` goes back to being a transport credential only.
 *
 * Two deliberate limits:
 *
 * - **Ambiguity is absence.** Bindings are kept per session, but a tool's `exec`
 *   carries no session id (only `callId`, `rootCallId`, `agent`), so a model-initiated
 *   call cannot say which session it belongs to. When exactly one person is currently
 *   bound, that is who the run belongs to. When two are, attaching either one would
 *   attribute A's run to B — a wrong name is worse than no name, so nothing is
 *   attached and the journal records the read as the host's, as before.
 * - **Expiry is real.** Portal tokens live ~15 minutes. An expired binding is dropped
 *   rather than relayed, so a long unattended run degrades to unattributed instead of
 *   presenting a token the backend would reject anyway.
 */

/** One browser's verified claim on one session. */
export type Binding = {
  /** The portal-signed token itself, relayed verbatim; the backend verifies it. */
  readonly token: string
  /** The subject the backend reported when it verified the token (union_id). */
  readonly subject: string
  /** Epoch milliseconds after which this binding is ignored. */
  readonly expiresAt: number
}

/** How long a binding is trusted when the claimer states no lifetime. */
export const DEFAULT_BINDING_MS = 15 * 60 * 1000

export class ActorBindings {
  readonly #bySession = new Map<string, Binding>()

  /** Record a verified claim. A second claim for the same session replaces the first. */
  bind(sessionId: string, binding: Binding): void {
    if (!sessionId || !binding.token || !binding.subject) return
    this.#bySession.set(sessionId, binding)
  }

  /** Forget one session's claim — a sign-out, or a token the backend just refused. */
  release(sessionId: string): void {
    this.#bySession.delete(sessionId)
  }

  /** The claim for one session, or undefined when absent or expired. */
  forSession(sessionId: string, now = Date.now()): Binding | undefined {
    const binding = this.#bySession.get(sessionId)
    if (!binding) return undefined
    if (binding.expiresAt <= now) {
      this.#bySession.delete(sessionId)
      return undefined
    }
    return binding
  }

  /** The subject bound to one session, or '' — for audit fields written host-side. */
  subjectForSession(sessionId: string, now = Date.now()): string {
    return this.forSession(sessionId, now)?.subject ?? ''
  }

  /**
   * The single unambiguous live binding, or undefined.
   *
   * Undefined covers three different situations on purpose — nobody bound, everybody
   * expired, and more than one distinct person bound. All three mean the same thing to
   * a caller: this read cannot be attributed, so do not attribute it.
   */
  unambiguous(now = Date.now()): Binding | undefined {
    const live: Binding[] = []
    for (const [sessionId, binding] of this.#bySession) {
      if (binding.expiresAt <= now) this.#bySession.delete(sessionId)
      else live.push(binding)
    }
    const subjects = new Set(live.map(binding => binding.subject))
    return subjects.size === 1 ? live[0] : undefined
  }

  /** The identity header for a model-initiated call: present only when unambiguous. */
  header(now = Date.now()): Record<string, string> {
    const binding = this.unambiguous(now)
    return binding ? { 'x-bridgeflow-user': binding.token } : {}
  }
}

/**
 * The host is one process serving one shared console, so the bindings are too.
 *
 * A module singleton rather than a parameter because `callBackend` is invoked from
 * every tool body: threading a binding through ~30 call sites would put the burden of
 * remembering it on each of them, and a forgotten argument there fails silently by
 * dropping attribution — exactly the failure this issue exists to remove.
 */
export const actors = new ActorBindings()
