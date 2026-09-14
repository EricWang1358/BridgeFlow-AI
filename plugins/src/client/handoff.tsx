import { useEffect, useState } from 'react'
import { api, useUI, describeError } from './ui.ts'
import { Notebook } from './notebook.tsx'
import { Chip } from './workspace.tsx'

/**
 * Template filling and handoff, as people see it (#144, #145).
 *
 * Read-only by design: the browser proxy never carries writes (`../web.ts`). Recording
 * answers and approving a draft happen in conversation with the captain, through
 * approval; this page shows where every record and handoff stands, what each draft is
 * still missing, and where the flow is getting stuck. Every label, department and
 * sentence comes from the host's declarations — none is written here.
 */

type Row =
  | { kind: 'artifact'; id: string; title: string; department: string; business_key: string[]; version: number; state: string; summary: string; updated_at: string }
  | { kind: 'handoff'; id: string; title: string; department: string; owner_role: string; business_key: string[]; state: string; stale: boolean; notification: string; summary: string; updated_at: string }
  | { kind: 'partial'; stage: string; title: string; department: string; business_key: string[]; summary: string }
type Draft = {
  id: string; title: string; department: string; state: string; version: number
  values: Record<string, { label: string; value: string; raw: string; evidence: string; note: string; source: { kind: string; ref: string } }>
  issues: { kind: string; label: string; message: string; question: string; blocking: boolean }[]
  checks: { id: string; title: string; value: string; unit: string; attention: boolean }[]
  receipt: Record<string, string | boolean> | null
}
type Catalogue = {
  version: string; status: string; case: string
  templates: Record<string, { title: string; department: string; version: number; status: string; fields: Record<string, { label: string; required: boolean; unit: string }> }>
  stages: Record<string, { title: string; department: string; owner_role: string; inputs: string[] }>
  lineage: { source: string; target: string; transform: string; status: string }[]
  integrations: { sink: string; notifier: string }
}
type Finding = { rule: string; category: string; scope: Record<string, string>; facts: string[]; hypothesis: string; route_to: string; decided_by: string }

export function Handoff() {
  const { t } = useUI()
  const [rows, setRows] = useState<Row[] | null>(null), [catalogue, setCatalogue] = useState<Catalogue | null>(null)
  const [findings, setFindings] = useState<Finding[]>([]), [draft, setDraft] = useState<Draft | null>(null)
  const [selected, setSelected] = useState(''), [error, setError] = useState(''), [revision, setRevision] = useState(0)

  useEffect(() => {
    const controller = new AbortController(), signal = controller.signal
    setError('')
    void Promise.all([
      api<{ rows: Row[] }>('/workflow/board', { signal }), api<Catalogue>('/workflow/catalogue', { signal }),
      api<Finding[]>('/workflow/adoption', { signal }),
    ]).then(([board, declared, signals]) => { setRows(board.rows); setCatalogue(declared); setFindings(signals) })
      .catch(e => { if (!signal.aborted) setError(describeError(e, t)) })
    return () => controller.abort()
  }, [revision])

  useEffect(() => {
    if (!selected) { setDraft(null); return }
    const controller = new AbortController()
    void api<Draft>(`/workflow/artifacts/${selected}`, { signal: controller.signal }).then(setDraft)
      .catch(e => { if (!controller.signal.aborted) setError(describeError(e, t)) })
    return () => controller.abort()
  }, [selected, revision])

  return <Notebook title={t('handoffWorkspace')} description={t('handoffHelp')}
    sources={catalogue ? <>
      <p className="bf-hint">{catalogue.case} · {t('catalogueVersion')} {catalogue.version} <Chip status={catalogue.status}/></p>
      {Object.entries(catalogue.templates).map(([key, template]) => <article className="bf-source-item" key={key}>
        <div className="bf-handoff-head"><strong>{template.department}「{template.title}」v{template.version}</strong><Chip status={template.status}/></div>
        <span className="bf-hint">{Object.values(template.fields).map(f => f.label + (f.required ? '' : `（${t('optional')}）`)).join('、')}</span>
      </article>)}
      <h4>{t('fieldLineage')}</h4>
      {catalogue.lineage.map((edge, i) => <p className="bf-hint" key={i}><code>{edge.source}</code> → <code>{edge.target}</code> · {edge.transform} <Chip status={edge.status}/></p>)}
      <p className="bf-hint">{t('integrations')}: {catalogue.integrations.sink} / {catalogue.integrations.notifier}</p>
    </> : <p className="bf-empty">{t('loading')}</p>}
    studio={<>
      <h4>{t('adoptionSignals')}</h4>
      {findings.length ? findings.map((f, i) => <article className="bf-source-item" key={i}>
        <div className="bf-handoff-head"><strong>{Object.values(f.scope).join(' · ')}</strong><Chip status={f.category}/></div>
        <p>{f.facts.join('；')}</p><p className="bf-hint">{f.hypothesis}</p>
        <p className="bf-hint">{t('decidedBy')}: {f.decided_by}</p>
      </article>) : <p className="bf-hint">{t('noAdoptionSignals')}</p>}
      <p className="bf-hint">{t('handoffWriteHelp')}</p>
    </>}>
    <div className="bf-card-head"><h3>{t('handoffBoard')}</h3><button onClick={() => setRevision(n => n + 1)}>{t('refresh')}</button></div>
    {error && <p role="alert" className="bf-error">{error}</p>}
    {!rows && !error && <p role="status" className="bf-loading">{t('loading')}</p>}
    {rows && !rows.length && <div className="bf-notebook-empty"><h3>{t('handoffEmpty')}</h3><p>{t('handoffEmptyHelp')}</p></div>}
    {rows && rows.map((row, i) => <article className="bf-source-item" key={row.kind === 'partial' ? `p${i}` : row.id}>
      <div className="bf-handoff-head"><strong>{row.department} · {row.title}</strong>
        <Chip status={row.kind === 'partial' ? 'partial' : row.state}/>
        {row.kind === 'handoff' && row.notification !== 'none' && <Chip status={`notice_${row.notification}`}/>}
        {row.kind === 'handoff' && row.stale && <Chip status="upstream_revised"/>}</div>
      <p>{row.summary}</p>
      <span className="bf-hint">{row.business_key.join(' · ')}{row.kind === 'handoff' ? ` · ${row.owner_role}` : ''}</span>
      {row.kind === 'artifact' && <button aria-expanded={selected === row.id} onClick={() => setSelected(selected === row.id ? '' : row.id)}>{t(selected === row.id ? 'close' : 'viewDraft')}</button>}
      {row.kind === 'artifact' && selected === row.id && draft?.id === row.id && <DraftDetail draft={draft}/>}
    </article>)}
  </Notebook>
}

function DraftDetail({ draft }: { draft: Draft }) {
  const { t } = useUI()
  return <section className="bf-handoff-draft" aria-label={t('viewDraft')}>
    {draft.issues.filter(i => i.blocking).map((issue, i) => <div className="bf-callout" data-tone="warn" key={i}>
      <h3>{issue.label ? `${issue.label} · ` : ''}{t(issue.kind)}</h3>
      <p>{issue.question || `${t('pleaseProvide')}${issue.label}`}</p>
      {issue.kind !== 'missing' && <p className="bf-hint">{issue.message}</p>}
    </div>)}
    {draft.checks.filter(c => c.attention).map(c => <div className="bf-callout" data-tone="info" key={c.id}><h3>{c.title}</h3><p>{c.value} {c.unit}</p></div>)}
    <div className="bf-scroll"><table><thead><tr><th>{t('field')}</th><th>{t('value')}</th><th>{t('asWritten')}</th><th>{t('provenance')}</th></tr></thead>
      <tbody>{Object.entries(draft.values).map(([key, v]) => <tr key={key}>
        <th>{v.label}</th><td>{v.value}</td><td>{v.raw}{v.note ? ` · ${v.note}` : ''}</td>
        <td>{v.source.kind}: {v.source.ref}{v.evidence ? ` · ${v.evidence}` : ''}</td>
      </tr>)}</tbody></table></div>
    {draft.receipt && <p className="bf-hint">{t('receipt')}: {String(draft.receipt.system)} #{String(draft.receipt.record_id)}</p>}
  </section>
}
