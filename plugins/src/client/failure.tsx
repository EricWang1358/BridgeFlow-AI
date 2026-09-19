import type { ReactNode } from 'react'
import { describeFailure, useUI } from './ui.ts'

/**
 * The one way a failure appears in this product (docs/design 12-states E03,
 * 01-portal P10).
 *
 * It replaces fifteen copies of `<p className="bf-error">{error}</p>`, which had two
 * problems beyond looking like a caption. The heading and the service's own words were
 * flattened into one sentence, so a 503 that means "we cannot currently determine your
 * access" read exactly like a stack trace; and each site decided for itself whether
 * there was any way out, so most offered none.
 *
 * `value` is the failure as it was caught — an Error, or somebody's own sentence as a
 * string. Nothing is described at the catch site any more: a caught error is data until
 * it reaches here, which is what lets this decide the wording from what the service
 * actually said (x-bridgeflow-reason) rather than from a string somebody already built.
 *
 * `children` are the actions. There is no built-in retry button: only the call site
 * knows whether retrying is the right offer, and a retry on a fail-closed access check
 * that will keep failing is worse than no button at all.
 */
export function Failure({ value, tone = 'danger', title, children }: {
  value: unknown
  tone?: 'danger' | 'warn'
  /** Only where the site names the state better than the error can — a failed lookup
   *  whose value is prose, not a request failure. Never to restate the error message. */
  title?: string
  children?: ReactNode
}) {
  const { t } = useUI()
  if (!value) return null
  const described = describeFailure(value, t), { body, detail } = described
  const heading = title ?? described.title
  return <div className="bf-callout bf-failure" data-tone={tone} role="alert">
    {heading && <h3>{heading}</h3>}
    {body && <p>{body}</p>}
    {detail && <p className="bf-mono bf-failure-detail">{detail}</p>}
    {children && <div className="bf-actions">{children}</div>}
  </div>
}
