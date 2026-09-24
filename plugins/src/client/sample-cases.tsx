import { useEffect, useRef, useState } from 'react'
import { api, useUI } from './ui.ts'

type Case = { id: string; case_id: string; title: [string, string]; summary: [string, string] }

/** The same case declaration labels both Sources and the Tasks guide. */
export function useDemoCase(caseId: string): Case | null {
  const [sample, setSample] = useState<{ caseId: string; value: Case | null }>({ caseId: '', value: null })
  useEffect(() => {
    setSample({ caseId, value: null })
    if (!caseId) return
    const controller = new AbortController()
    void api<{ cases: Case[] }>('/batches/demo/cases', { signal: controller.signal })
      .then(value => setSample({ caseId, value: value.cases.find(item => item.case_id === caseId) ?? null }))
      .catch(() => { if (!controller.signal.aborted) setSample({ caseId, value: null }) })
    return () => controller.abort()
  }, [caseId])
  return sample.caseId === caseId ? sample.value : null
}

/**
 * The demo cases beyond the guided-tour sample. One batch cannot show every state — a batch
 * that is ready cannot also be held back — so each case is its own notebook. Titles and
 * summaries come from the registry the backend imports from, not from this file.
 */
export function SampleCases({ disabled, open }: { disabled: boolean; open: (id: string, title: string) => void }) {
  const { t, language } = useUI()
  const picker = useRef<HTMLDetailsElement>(null)
  const [cases, setCases] = useState<Case[]>([])
  const [error, setError] = useState(false), [retry, setRetry] = useState(0)
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    const controller = new AbortController()
    setError(false); setLoading(true)
    void api<{ cases: Case[] }>('/batches/demo/cases', { signal: controller.signal })
      .then(value => {
        const choices = value.cases.filter(c => c.id !== 'tour')
        setCases(choices); setLoading(false)
        if (!choices.length) { setError(true); if (picker.current) picker.current.open = true }
      }).catch(() => { if (!controller.signal.aborted) { setError(true); setLoading(false); if (picker.current) picker.current.open = true } })
    return () => controller.abort()
  }, [retry])
  const pick = (pair: [string, string]) => pair[language === 'zh' ? 0 : 1]
  return <details ref={picker} className="bf-sample-cases">
    <summary>{t('sampleCases')}</summary>
    {loading ? <p role="status" className="bf-hint">{t('loading')}</p>
      : error ? <><p role="alert" className="bf-error">{t('sampleCasesUnavailable')}</p>
      <button onClick={() => setRetry(value => value + 1)}>{t('refresh')}</button></>
      : <p className="bf-hint">{t('sampleCasesHelp')}</p>}
    {!loading && !error && <ul>{cases.map(c => <li key={c.id}>
      <button data-case={c.id} disabled={disabled} onClick={() => { if (picker.current) picker.current.open = false; open(c.id, pick(c.title)) }}><strong>{pick(c.title)}</strong><small>{pick(c.summary)}</small></button>
    </li>)}</ul>}
  </details>
}
