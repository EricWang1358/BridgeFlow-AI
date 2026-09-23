import { useEffect, useState } from 'react'
import { api, useUI } from './ui.ts'

type Case = { id: string; title: [string, string]; summary: [string, string] }

/**
 * The demo cases beyond the guided-tour sample. One batch cannot show every state — a batch
 * that is ready cannot also be held back — so each case is its own notebook. Titles and
 * summaries come from the registry the backend imports from, not from this file.
 */
export function SampleCases({ disabled, open }: { disabled: boolean; open: (id: string, title: string) => void }) {
  const { t, language } = useUI()
  const [cases, setCases] = useState<Case[]>([])
  useEffect(() => {
    const controller = new AbortController()
    void api<{ cases: Case[] }>('/batches/demo/cases', { signal: controller.signal })
      .then(value => setCases(value.cases.filter(c => c.id !== 'tour'))).catch(() => setCases([]))
    return () => controller.abort()
  }, [])
  if (!cases.length) return null
  const pick = (pair: [string, string]) => pair[language === 'zh' ? 0 : 1]
  return <details className="bf-sample-cases">
    <summary>{t('sampleCases')}</summary>
    <p className="bf-hint">{t('sampleCasesHelp')}</p>
    <ul>{cases.map(c => <li key={c.id}>
      <button data-case={c.id} disabled={disabled} onClick={() => open(c.id, pick(c.title))}><strong>{pick(c.title)}</strong><small>{pick(c.summary)}</small></button>
    </li>)}</ul>
  </details>
}
