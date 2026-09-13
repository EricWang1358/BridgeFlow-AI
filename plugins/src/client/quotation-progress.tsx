import { useEffect, useState } from 'react'
import { api, navigate, route, useUI, describeError } from './ui.ts'
import { Chip } from './workspace.tsx'

/** Read the declared contract; an available template is not a completed quote. */
export function QuotationProgress() {
  const {t}=useUI()
  const [catalogue,setCatalogue]=useState<{status:string;contract:{inputs:Record<string,{title:string;owner:string}>}|null}|null>(null)
  const [error,setError]=useState('')
  useEffect(()=>{const abort=new AbortController();void api<NonNullable<typeof catalogue>>('/quotation/contract',{signal:abort.signal}).then(setCatalogue).catch(e=>{if(!abort.signal.aborted)setError(describeError(e, t))});return()=>abort.abort()},[])
  return <section className="bf-quotation-progress" aria-label={t('quotationProgress')}><h3>{t('quotationProgress')}</h3>
    {error ? <p role="alert">{error}</p> : !catalogue ? <p role="status">{t('loading')}</p> : <>
      <Chip status={catalogue.contract?'awaitingSamples':'needs_configuration'}/>
      <p className="bf-hint">{t(catalogue.contract?'quotationStageHelp':'quotationConfigureHelp')}</p>
      {catalogue.contract && <details><summary>{t('awaitingEvidence')}</summary><ul>{Object.entries(catalogue.contract.inputs).map(([key,field])=><li key={key}>{field.title} · {t(field.owner)}</li>)}</ul></details>}
      <button onClick={()=>navigate({...route(),view:'quotation'})}>{t('quotationNext')}</button>
    </>}
  </section>
}
