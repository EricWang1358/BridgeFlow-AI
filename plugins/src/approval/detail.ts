/**
 * What the operator reads before deciding.
 *
 * The approval seam carries a tool name, a call id and a reason — deliberately not
 * the arguments, because `conversation.approval.detail` exists so a UI can pull the
 * already-streamed tool call instead of duplicating it on the wire. We are not the
 * Web Client, so we carry a summary ourselves; the constraints that summary is
 * under are the interesting part:
 *
 * - **Bounded, always.** Values are clipped and the list is truncated. The scenario
 *   is 200,000 rows, and an approval prompt that grows with the data is the same bug
 *   as a tool return value that does (`CLAUDE.md`, seventh hard constraint).
 * - **Labels are argument names, never field names.** They come from the tool's own
 *   declaration in `../tools/`, which is ours; the spreadsheet's schema is still
 *   being negotiated and nothing here may assume it (eighth constraint).
 * - **The console renders this as text.** It is model-authored and rooted in
 *   spreadsheet cells, so it is untrusted twice over.
 */

/** One label/value pair, matching the backend's `ApprovalDetail`. */
export interface ApprovalDetail {
  label: string
  value: string
}

/** Longest value shown, longest label, and how many pairs at most. */
const MAX_VALUE = 120
const MAX_LABEL = 40
const MAX_ITEMS = 12

/** How many calls' summaries are held while their approvals are outstanding. */
const MAX_TRACKED = 64

function clip(text: string, limit: number): string {
  const collapsed = text.replace(/\s+/g, ' ').trim()
  return collapsed.length <= limit ? collapsed : `${collapsed.slice(0, limit - 1)}…`
}

/** Render one argument value compactly, without letting a nested object expand. */
function show(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return clip(value, MAX_VALUE)
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  if (Array.isArray(value)) return clip(`${value.length} item(s)`, MAX_VALUE)
  return clip(JSON.stringify(value) ?? '', MAX_VALUE)
}

/** Summarise a tool call's arguments for a person, within the caps above. */
export function summarise(args: unknown): ApprovalDetail[] {
  if (!args || typeof args !== 'object' || Array.isArray(args)) return []
  return Object.entries(args)
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .slice(0, MAX_ITEMS)
    .map(([label, value]) => ({ label: clip(label, MAX_LABEL), value: show(value) }))
}

/**
 * Summaries waiting to be attached to an approval request, keyed by tool call.
 *
 * The gate sees the arguments; the answerer sees the request. This carries the one
 * to the other. It is owned by the plugin rather than the module, so disposing the
 * plugin drops it — a stale summary attached to a later call would show the operator
 * the wrong thing, which is worse than showing them nothing.
 */
export class PendingDetails {
  readonly #byCallId = new Map<string, ApprovalDetail[]>()

  /** Record one call's summary, evicting the oldest if the map is at its cap. */
  record(callId: string | undefined, args: unknown): void {
    if (!callId) return
    if (this.#byCallId.size >= MAX_TRACKED) {
      const oldest = this.#byCallId.keys().next()
      if (!oldest.done) this.#byCallId.delete(oldest.value)
    }
    this.#byCallId.set(callId, summarise(args))
  }

  /** Take one call's summary. Removing it keeps a rejected call from reappearing. */
  take(callId: string | undefined): ApprovalDetail[] {
    if (!callId) return []
    const detail = this.#byCallId.get(callId) ?? []
    this.#byCallId.delete(callId)
    return detail
  }
}
