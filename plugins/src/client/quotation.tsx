import { tourEvent } from './tour/state.ts'
import { useEffect, useState } from 'react'
import { api, navigate, route, useUI, describeError } from './ui.ts'
import { Notebook } from './notebook.tsx'

type Contract = {
  title: string; description: string; manager_decision: string;
  inputs: Record<string, { title: string; unit: string; owner: string }>;
  roles: Record<string, { responsibility: string; decision_owner: string }>;
  metrics: Record<string, { title: string; unit: string; formula: string }>;
  outputs: string[]; checks: { id: string; title: string; owner: string }[];
}
type Catalogue = { status: string; contract: Contract | null; source?: { filename: string; document_sha256: string; paragraph: string } }
export function Quotation() {
  const { t } = useUI()
  const [catalogue, setCatalogue] = useState<Catalogue | null>(null), [error, setError] = useState(''), [revision, setRevision] = useState(0)
  useEffect(() => {
    const controller = new AbortController(); setCatalogue(null); setError('')
    void api<Catalogue>('/quotation/contract', { signal: controller.signal }).then(value => { setCatalogue(value); tourEvent('quotation', route().batch ?? '') }).catch(e => { if (!controller.signal.aborted) setError(describeError(e, t)) })
    return () => controller.abort()
  }, [revision])
  useEffect(() => {
    const opened = () => { if (catalogue && !error) tourEvent('quotation', route().batch ?? '') }
    window.addEventListener('bridgeflow:quotation-opened', opened)
    return () => window.removeEventListener('bridgeflow:quotation-opened', opened)
  }, [catalogue, error])
  const contract = catalogue?.contract
  return <Notebook title={t('quotation')} description={t('quotationHelp')}
    sources={<>
      <p className="bf-hint">{t('quotationSourceHelp')}</p>
      {contract ? Object.entries(contract.inputs).map(([key, field]) => <article className="bf-source-item" key={key}>
        <strong>{field.title}</strong><span className="bf-hint">{field.unit} · {t(field.owner)}</span><span className="bf-source-pending">{t('awaitingEvidence')}</span>
      </article>) : <p className="bf-empty">{t('quotationUnconfigured')}</p>}
    </>}
    studio={<>
      <div data-tour-id="quotation-scope" className="bf-notebook-note"><strong>{t('quotationStage')}</strong><p>{t('quotationStageHelp')}</p></div>
      {contract && <><h4>{t('decisionOwners')}</h4>{Object.entries(contract.roles).map(([key, role]) => <article className="bf-source-item" key={key}><strong>{role.decision_owner}</strong><p className="bf-hint">{role.responsibility}</p></article>)}
        <h4>{t('quotationChecks')}</h4>{contract.checks.map(check => <p className="bf-hint" key={check.id}>{check.title}</p>)}</>}
      <p className="bf-hint">{t('quotationApprovalHelp')}</p>
    </>}>
    <div className="bf-card-head"><h3>{t('declaredTemplate')}</h3><button data-tour-recovery={error ? '' : undefined} onClick={() => setRevision(n => n + 1)}>{t('refresh')}</button></div>
    {error && <p role="alert" className="bf-error">{error}</p>}
    {!catalogue && !error && <p role="status" className="bf-loading">{t('loading')}</p>}
    {catalogue && !contract && <div className="bf-notebook-empty"><h3>{t('quotationUnconfigured')}</h3><p>{t('quotationConfigureHelp')}</p></div>}
    {contract && <>
      <div className="bf-notebook-note"><span className="bf-chip" data-status="partial">{t('awaitingSamples')}</span><p>{contract.description}</p></div>
      <article className="bf-quotation-paper" aria-label={t('declaredTemplate')}>
        <header><span className="bf-eyebrow">BridgeFlow · {t('quotation')}</span><h3>{contract.title}</h3><p className="bf-hint">{t('quotationNoDraft')}</p></header>
        <dl>{contract.outputs.map(key => <div key={key}><dt>{contract.metrics[key]?.title}</dt><dd>{t('awaitingEvidence')}</dd></div>)}</dl>
        <p className="bf-hint">{contract.manager_decision}</p>
      </article>
      <details className="bf-formulas"><summary>{t('declaredFormulas')}</summary>{contract.outputs.map(key => <article className="bf-source-item" key={key}><strong>{contract.metrics[key]?.title}</strong><code>{contract.metrics[key]?.formula}</code><span className="bf-hint">{contract.metrics[key]?.unit}</span></article>)}</details>
      {catalogue.source && <details className="bf-formulas"><summary>{t('declarationSource')}</summary><p>{catalogue.source.filename} · {catalogue.source.paragraph}</p><code>{catalogue.source.document_sha256}</code></details>}
    </>}
  </Notebook>
}
export function QuotationButton() {
  const { t } = useUI()
  return <button className="bf-open bf-quotation-entry" onClick={() => navigate({ ...route(), view: 'quotation' })}>{t('quotationWorkspace')}</button>
}
