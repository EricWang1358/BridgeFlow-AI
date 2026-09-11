/** Product navigation only. These capabilities never grant tool permissions. */
export type WorkflowId = 'monthly' | 'quotation'

export const notebookPurposes = {
  mixed: { label: 'mixedNotebook', workflows: ['quotation', 'monthly'] },
  monthly: { label: 'monthlyNotebook', workflows: ['monthly'] },
  quotation: { label: 'quotationNotebook', workflows: ['quotation'] },
} as const satisfies Record<string, { label: string; workflows: readonly WorkflowId[] }>

export type NotebookKind = keyof typeof notebookPurposes
export const defaultNotebookKind: NotebookKind = 'mixed'
export const notebookKinds = Object.keys(notebookPurposes) as NotebookKind[]

export function isNotebookKind(value: unknown): value is NotebookKind {
  return typeof value === 'string' && Object.hasOwn(notebookPurposes, value)
}

export function notebookPurpose(kind: unknown) {
  return notebookPurposes[isNotebookKind(kind) ? kind : defaultNotebookKind]
}
