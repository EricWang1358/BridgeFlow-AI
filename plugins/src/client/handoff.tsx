import { useEffect, useState } from 'react'
import { api, askCaptain, useUI, describeError, useGloss, useDataRevision } from './ui.ts'
import { Notebook } from './notebook.tsx'
import { Chip } from './workspace.tsx'
import { tourEvent } from './tour/state.ts'
import { WorkflowFlow } from './workflow-flow.tsx'
import { WorkflowScopeCard, WorkflowTimeline } from './workflow-scope.tsx'
import { useGuestMode } from './guest.tsx'
import { translateBoard } from './zh-messages.ts'

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
  | { kind: 'handoff'; id: string; stage: string; title: string; department: string; owner_role: string; business_key: string[]; state: string; stale: boolean; notification: string; summary: string; updated_at: string; due_at?: string; overdue_hours?: number | null; awaiting_outputs?: string[] }
  | { kind: 'partial'; stage: string; title: string; department: string; business_key: string[]; summary: string }
export type Draft = {
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
  const { t, paren, language } = useUI(), gloss = useGloss()
  const dataRevision = useDataRevision()
  const guest = useGuestMode()
  const modelOff = guest.guest && !guest.llm
  const [rows, setRows] = useState<Row[] | null>(null), [catalogue, setCatalogue] = useState<Catalogue | null>(null)
  const [findings, setFindings] = useState<Finding[]>([]), [draft, setDraft] = useState<Draft | null>(null)
  const [selected, setSelected] = useState(''), [error, setError] = useState(''), [revision, setRevision] = useState(0)
  const [busy, setBusy] = useState(false), [timeline, setTimeline] = useState('')

  useEffect(() => {
    const controller = new AbortController(), signal = controller.signal
    setError('')
    void Promise.all([
      api<{ rows: Row[] }>('/workflow/board', { signal }), api<Catalogue>('/workflow/catalogue', { signal }),
      api<Finding[]>('/workflow/adoption', { signal }),
    ]).then(([board, declared, signals]) => {
      setRows(board.rows); setCatalogue(declared); setFindings(signals)
      if (board.rows.length) tourEvent('workflowSample', '')  // records already exist: the tour's load step is done
    })
      .catch(e => { if (!signal.aborted) setError(describeError(e, t)) })
    return () => controller.abort()
  }, [revision, dataRevision])

  useEffect(() => {
    if (!selected) { setDraft(null); return }
    const controller = new AbortController()
    void api<Draft>(`/workflow/artifacts/${selected}`, { signal: controller.signal }).then(setDraft)
      .catch(e => { if (!controller.signal.aborted) setError(describeError(e, t)) })
    return () => controller.abort()
  }, [selected, revision, dataRevision])

  const counts: Record<string, number> = {}, overdue: Record<string, number> = {}
  for (const row of rows ?? []) if (row.kind !== 'partial') {
    counts[row.state] = (counts[row.state] ?? 0) + 1
    if (row.kind === 'handoff' && (row.overdue_hours ?? -1) > 0) overdue[row.state] = (overdue[row.state] ?? 0) + 1
  }
  const fill = (key: string, id: string) => t(key).replaceAll('{id}', id)
  // The next step of a record is a request to the captain, never a write from this page:
  // every write still goes through the captain's tool and a person's approval.
  const next = (row: Row): [string, string] | null =>
    row.kind === 'artifact' && row.state === 'needs_input' ? ['askNeedsInput', fill('requestNeedsInput', row.id)]
      : row.kind === 'artifact' && row.state === 'ready_for_review' ? ['askReview', fill('requestReview', row.id)]
        : row.kind === 'handoff' && row.state === 'waiting' ? ['askStart', fill('requestStart', row.id)]
          : row.kind === 'handoff' && row.state === 'in_progress' && !row.awaiting_outputs?.length ? ['askComplete', fill('requestComplete', row.id)] : null
  async function run(action: () => Promise<unknown>) {
    setBusy(true); setError('')
    try { await action(); setRevision(n => n + 1) } catch (e) { setError(describeError(e, t)) } finally { setBusy(false) }
  }
  // Technical ids read as words when there is a label for them, and as themselves otherwise.
  const label = (key: string, raw: string) => t(key) === key ? raw : t(key)
  return <Notebook title={t('handoffWorkspace')} description={t('handoffHelp')}
    sources={catalogue ? <>
      <p className="bf-hint">{catalogue.case} · {t('catalogueVersion')} {catalogue.version} <Chip status={catalogue.status}/></p>
      {Object.entries(catalogue.templates).map(([key, template]) => <article className="bf-source-item" key={key}>
        <div className="bf-handoff-head"><strong>{gloss.text(template.department)}「{gloss.label(template.title)}」v{template.version}</strong><Chip status={template.status}/></div>
        <span className="bf-hint">{Object.values(template.fields).map(f => gloss.text(f.label) + (f.required ? '' : paren(t('optional')))).join(', ')}</span>
      </article>)}
      <h4>{t('fieldLineage')}</h4>
      {catalogue.lineage.map((edge, i) => <p className="bf-hint" key={i}><code>{edge.source}</code> → <code>{edge.target}</code> · {label(`transform_${edge.transform}`, edge.transform)} <Chip status={edge.status}/></p>)}
      <p className="bf-hint">{t('integrations')}: {label(`integration_${catalogue.integrations.sink}`, catalogue.integrations.sink)} / {label(`integration_${catalogue.integrations.notifier}`, catalogue.integrations.notifier)}</p>
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
    <p className="bf-chip bf-shared" data-status="info">{t('sharedAcrossNotebooks')}</p>
    <div className="bf-card-head"><h3>{t('handoffBoard')}</h3><button onClick={() => setRevision(n => n + 1)}>{t('refresh')}</button></div>
    {error && <p role="alert" className="bf-error">{error}</p>}
    {!rows && !error && <p role="status" className="bf-loading">{t('loading')}</p>}
    <WorkflowScopeCard revision={revision} onChanged={() => setRevision(n => n + 1)} />
    {modelOff && rows?.some(row => next(row)) && <p className="bf-hint" role="status">{t('guestModelActionUnavailable')}</p>}
    {rows && !rows.length && <p className="bf-hint">{t('handoffEmpty')}</p>}
    <WorkflowFlow counts={counts} overdue={overdue} />
    {rows && !rows.length && <div className="bf-notebook-empty"><p>{t('handoffEmptyHelp')}</p>
      <p className="bf-hint">{t('workflowSampleHelp')}</p>
      <button data-tour-id="workflow-sample" className="bf-primary" disabled={busy} onClick={() => void run(async () => { await api('/workflow/sample', { method: 'POST' }); tourEvent('workflowSample', '') })}>{t(busy ? 'busy' : 'workflowSample')}</button></div>}
    {rows && rows.map((row, i) => <article data-tour-id={i === 0 ? 'workflow-sample' : undefined} className="bf-source-item" key={row.kind === 'partial' ? `p${i}` : row.id}>
      <div className="bf-handoff-head"><strong>{gloss.text(row.department)} · {gloss.label(row.title)}</strong>
        <Chip status={row.kind === 'partial' ? 'partial' : row.state}/>
        {row.kind === 'handoff' && row.notification !== 'none' && <Chip status={`notice_${row.notification}`}/>}
        {row.kind === 'handoff' && row.stale && <Chip status="upstream_revised"/>}
        {row.kind === 'handoff' && row.overdue_hours != null && <span className="bf-due" data-overdue={row.overdue_hours > 0}>
          {t(row.overdue_hours > 0 ? 'overdueBy' : 'dueIn').replaceAll('{h}', String(Math.abs(Math.round(row.overdue_hours))))}</span>}</div>
      <p>{language === 'zh' ? translateBoard(row.summary) : gloss.message(row.summary)}</p>
      <span className="bf-hint">{row.business_key.join(' · ')}{row.kind === 'handoff' ? ` · ${row.owner_role}` : ''}</span>
      {(() => { const step = next(row); return step && <button className="bf-primary" disabled={busy || modelOff}
        onClick={() => void run(() => askCaptain(step[1]))}>{t(step[0])}</button> })()}
      {row.kind !== 'partial' && <div className="bf-row-actions">
        <button data-tour-id={i === 0 ? 'workflow-timeline' : undefined} aria-expanded={timeline === row.id} onClick={() => { setTimeline(timeline === row.id ? '' : row.id); tourEvent('workflowTimeline', '') }}>{t('timeline')}</button>
        {row.kind === 'artifact' && <button aria-expanded={selected === row.id} onClick={() => setSelected(selected === row.id ? '' : row.id)}>{t(selected === row.id ? 'close' : 'viewDraft')}</button>}
      </div>}
      {row.kind !== 'partial' && timeline === row.id && <WorkflowTimeline kind={row.kind} id={row.id} />}
      {row.kind === 'artifact' && selected === row.id && draft?.id === row.id && <DraftDetail draft={draft}/>}
    </article>)}
  </Notebook>
}

/** The draft behind an approval card: the values a person is asked to approve (#253 follow-up). */
export function DraftForApproval({ artifactId }: { artifactId: string }) {
  const { t } = useUI()
  const [draft, setDraft] = useState<Draft | null>(null), [failed, setFailed] = useState(false)
  useEffect(() => {
    const controller = new AbortController()
    void api<Draft>(`/workflow/artifacts/${artifactId}`, { signal: controller.signal }).then(setDraft)
      .catch(() => { if (!controller.signal.aborted) setFailed(true) })
    return () => controller.abort()
  }, [artifactId])
  if (failed) return <p className="bf-hint">{t('draftUnavailable')}</p>
  return draft ? <DraftDetail draft={draft} /> : <p className="bf-hint bf-loading">{t('loading')}</p>
}

export function DraftDetail({ draft }: { draft: Draft }) {
  const { t } = useUI(), gloss = useGloss()
  return <section className="bf-handoff-draft" aria-label={t('viewDraft')}>
    {draft.issues.filter(i => i.blocking).map((issue, i) => <div className="bf-callout" data-tone="warn" key={i}>
      <h3>{issue.label ? `${gloss.label(issue.label)} · ` : ''}{t(issue.kind)}</h3>
      <p>{issue.question || `${t('pleaseProvide')}${gloss.label(issue.label)}`}</p>
      {issue.kind !== 'missing' && <p className="bf-hint">{gloss.message(issue.message)}</p>}
    </div>)}
    {draft.checks.filter(c => c.attention).map(c => <div className="bf-callout" data-tone="info" key={c.id}><h3>{gloss.message(c.title)}</h3><p>{c.value} {c.unit}</p></div>)}
    <div className="bf-scroll"><table><thead><tr><th>{t('field')}</th><th>{t('value')}</th><th>{t('asWritten')}</th><th>{t('provenance')}</th></tr></thead>
      <tbody>{Object.entries(draft.values).map(([key, v]) => <tr key={key}>
        <th>{gloss.label(v.label)}</th><td>{v.value}</td><td>{v.raw}{v.note ? ` · ${v.note}` : ''}</td>
        <td>{v.source.kind}: {v.source.ref}{v.evidence ? ` · ${v.evidence}` : ''}</td>
      </tr>)}</tbody></table></div>
    {draft.receipt && <p className="bf-hint">{t('receipt')}: {String(draft.receipt.system)} #{String(draft.receipt.record_id)}</p>}
  </section>
}
