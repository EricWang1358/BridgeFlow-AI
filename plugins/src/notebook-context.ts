import type { Notebook } from './notebooks.ts'
import { isNotebookKind, type NotebookKind } from './notebook-capabilities.ts'

/**
 * What the captain is told each turn about the notebook it is working in.
 *
 * Asked "isn't this workspace empty?", the captain used to answer from the company-wide
 * handoff board, because nothing told it which notebook it was in. This names the notebook's
 * batch (or that it has none) and which pages are shared by every notebook.
 *
 * Navigation only: it grants nothing. Every tool still checks the batch it is given, the batch
 * id is the only notebook fact passed (never the person's free-text title), and a turn with no
 * known notebook gets no context rather than a guess.
 */
export type Viewing = { batch: string | null; kind?: NotebookKind }

const shared = 'The filling & handoff board and discovery projects are company-wide: every notebook sees the same records, and they are not this notebook\'s contents.'

export function notebookContextText(viewing: Viewing | undefined, saved: Notebook | null): string {
  const batch = viewing ? viewing.batch : saved?.batch ?? null
  const kind = viewing?.kind ?? saved?.kind
  if (!viewing && !saved) return ''
  const purpose = kind ? ` (purpose: ${kind})` : ''
  return batch
    ? `Notebook context (navigation only; grants nothing): this conversation's notebook${purpose} is bound to batch ${batch}. `
      + `When the person says "this batch", "this month" or "this notebook", use that batch; read its period and state with batch_summary. ${shared}`
    : `Notebook context (navigation only; grants nothing): this conversation's notebook${purpose} has no data yet; no batch is bound. `
      + `Its sources, tasks, data, conclusions and artifacts are empty until files are added or a sample is opened. ${shared}`
}

/** A page's report of what it is showing, validated; null when it is not a well-formed report. */
export function parseViewing(value: unknown): Viewing | null {
  if (!value || typeof value !== 'object') return null
  const data = value as Record<string, unknown>
  const batch = data.batch === null || data.batch === undefined || data.batch === '' ? null : data.batch
  if (batch !== null && (typeof batch !== 'string' || !/^[a-f0-9]{32}$/.test(batch))) return null
  if (data.kind !== undefined && !isNotebookKind(data.kind)) return null
  return { batch, ...(data.kind !== undefined ? { kind: data.kind as NotebookKind } : {}) }
}
