import { useEffect, useState } from 'react'
import { api, useUI, describeError, useGloss } from './ui.ts'
import { Chip } from './workspace.tsx'

/** Built-in quotation samples: each one's draft, its own contract, and the contract checked against the legal requirements (#302). */
type Citation = { clause: string; excerpt: string }
type Requirement = { requirement_id: string; title: string; basis: string; decided_by: 'rule' | 'model'; status: string; reason_code: string;
  evidence: Citation[]; observed: string | null; unit: string; explanation: string; suggestion: string | null }
type Consistency = { metric: string; title: string; status: string; reason_code: string; quote_value: string | null; quote_unit: string;
  quote_sources: { filename: string; paragraph: string; excerpt: string }[]; contract_value: string | null; evidence: Citation[] }
type Case = {
  quote: { id: string; title: string; customer: string }
  draft: { status: string; fields: { metric: string; title: string; value: string; unit: string }[];
    checks: { id: string; title: string; status: string; decision_owner: string }[]; refusals: { code: string; title: string }[] }
  contract: { file: string; complete: boolean; clauses: { id: string; heading: string; text: string }[] }
  compliance: { legal_version: number; overall: string; requirements: Requirement[]; consistency: Consistency[]; notice: string;
    judgement: { generated_by: string; generated_at: string; stale: boolean; present: boolean } }
}
export type QuoteCases = { status: string; legal: { version: number; title: string; published_by: string; published_at: string } | null;
  quotes: { id: string; title: string; customer: string }[] }

function Cite({ items }: { items: Citation[] }) {
  const { t } = useUI()
  return <>{items.map(c => <q key={c.clause + c.excerpt} className="bf-cite"><b>{t('clauseRef').replace('{id}', c.clause)}</b> {c.excerpt}</q>)}</>
}

export function QuoteCasesPanel({ listing }: { listing: QuoteCases }) {
  const { t, colon, paren } = useUI(), gloss = useGloss()
  const [selected, setSelected] = useState(listing.quotes[0]?.id ?? '')
  const [item, setItem] = useState<Case | null>(null), [error, setError] = useState('')
  useEffect(() => {
    if (!selected) return
    const controller = new AbortController(); setItem(null); setError('')
    void api<Case>(`/quotation/cases/${encodeURIComponent(selected)}`, { signal: controller.signal }).then(setItem)
      .catch(e => { if (!controller.signal.aborted) setError(describeError(e, t)) })
    return () => controller.abort()
  }, [selected])
  const c = item?.compliance
  return <section className="bf-quote-cases" aria-label={t('quoteCases')}>
    <div className="bf-card-head"><h3>{t('quoteCases')}</h3><span className="bf-hint">{t('quoteCasesHelp')}</span></div>
    <nav className="bf-tabs" aria-label={t('quoteCases')}>{listing.quotes.map(q => <button key={q.id} aria-pressed={q.id === selected} onClick={() => setSelected(q.id)}>{q.id} · {gloss.text(q.title)}</button>)}</nav>
    {error && <p role="alert" className="bf-error">{error}</p>}
    {!item && !error && <p role="status" className="bf-loading">{t('loading')}</p>}
    {item && c && <>
      <article className="bf-quotation-paper" aria-label={t('quotation')}>
        <header><span className="bf-eyebrow">BridgeFlow · {t('quotation')} · {item.quote.id}</span><h3>{gloss.text(item.quote.title)}</h3>
          <p className="bf-hint">{item.quote.customer} · <Chip status={item.draft.status} label={t(item.draft.status === 'draft' ? 'quoteDraftReady' : 'quoteDraftRefused')} /></p></header>
        <dl>{item.draft.fields.map(f => <div key={f.metric}><dt>{gloss.text(f.title)}</dt><dd className="bf-quote-value">{f.value} {gloss.text(f.unit)}</dd></div>)}</dl>
        {item.draft.refusals.map(r => <p key={r.code + r.title} className="bf-error">{gloss.text(r.title)}</p>)}
        {item.draft.checks.filter(x => x.status === 'attention').map(x => <p key={x.id} className="bf-hint"><Chip status="attention" /> {gloss.text(x.title)}</p>)}
      </article>

      <div className="bf-card-head"><h3>{t('complianceTitle')}</h3><Chip status={c.overall} /></div>
      <p className="bf-hint">{t('legalVersion').replace('{version}', String(c.legal_version))}{listing.legal ? ` · ${listing.legal.title} · ${listing.legal.published_by} · ${listing.legal.published_at}` : ''}</p>
      {c.judgement.stale && <p role="alert" className="bf-error">{t('judgementStale')}</p>}
      <table className="bf-compliance">
        <thead><tr><th>{t('complianceStatus')}</th><th>{t('complianceRequirement')}</th><th>{t('complianceEvidence')}</th><th>{t('complianceSuggestion')}</th></tr></thead>
        <tbody>{c.requirements.map(r => <tr key={r.requirement_id} data-status={r.status}>
          <td><Chip status={r.status} /><span className="bf-hint">{t(r.decided_by === 'rule' ? 'decidedByRule' : 'decidedByModel')}</span></td>
          <td><strong>{r.title}</strong><span className="bf-hint">{r.basis}</span></td>
          <td>{r.evidence.length ? <Cite items={r.evidence} /> : <span className="bf-hint">{t(`reason_${r.reason_code}`)}</span>}
            {r.explanation && <span className="bf-hint">{t('modelSays')}{colon}{r.explanation}</span>}</td>
          <td>{r.suggestion ?? ''}</td>
        </tr>)}
        {c.consistency.map(x => <tr key={x.metric} data-status={x.status}>
          <td><Chip status={x.status} /><span className="bf-hint">{t('decidedByRule')}</span></td>
          <td><strong>{t('consistencyTitle').replace('{title}', x.title)}</strong></td>
          <td><span>{t('quoteSide')}{colon}{x.quote_value ?? '—'}{x.quote_sources[0] ? paren(`${x.quote_sources[0].filename} · ${x.quote_sources[0].excerpt}`) : ''}</span>
            <span>{t('contractSide')}{colon}{x.contract_value ?? '—'}</span>{x.evidence.length ? <Cite items={x.evidence} /> : <span className="bf-hint">{t(`reason_${x.reason_code}`)}</span>}</td>
          <td>{x.status === 'inconsistent' ? t('consistencySuggestion') : ''}</td>
        </tr>)}</tbody>
      </table>
      <p className="bf-hint">{t('complianceNotice')}</p>
      <p className="bf-hint">{c.judgement.present ? t('judgementFrozen').replace('{by}', c.judgement.generated_by).replace('{at}', c.judgement.generated_at) : t('judgementAbsent')}</p>

      <details className="bf-formulas"><summary>{t('contractClauses')}{colon}{item.contract.file}{item.contract.complete ? ` · ${t('contractComplete')}` : ''}</summary>
        {item.contract.clauses.map(cl => <article className="bf-source-item" key={cl.id}><strong>{t('clauseRef').replace('{id}', cl.id)} · {cl.heading}</strong><p>{cl.text}</p></article>)}
      </details>
    </>}
  </section>
}
