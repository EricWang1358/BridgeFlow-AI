import { useEffect, useState } from 'react'
import { tourEvent } from './tour/state.ts'
import { api, cellText, describeError, navigate, useUI } from './ui.ts'
import { GradeMark } from './brief.tsx'
import { Chip } from './workspace.tsx'

/**
 * The 跨部门业务整合总表 for the selected batch, built from the business dictionary (字典 v2).
 * Read-only: each cell shows where it came from on hover; open items are listed with the
 * departments involved. The workbook download keeps the master template's column order.
 */
type Issue = { kind: string; field: string; key: string[]; departments: string[]; message: string }
type Row = { key: string[]; values: Record<string, unknown>; provenance: Record<string, Record<string, unknown>>; complete: boolean }
type Grade = { grade: string | null; chain: string[]; missing: string[] }
type Convention = { id: string; text: string; kind: string; affected_fields: string[]; state: string; version: number; source: string; note: string; requested_value: string; decided_by: string; at: string; declaration_change: string }
type Master = { version: string; columns: string[]; rows: Row[]; issues: Issue[]; assumptions?: Record<string, string>; conventions?: Convention[]; grades?: Record<string, Grade>[]; grade_summary?: Record<string, number> }

function origin(p: Record<string, unknown> | undefined): string {
  if (!p) return ''
  const assumed = (p.assumptions as string[] | undefined)?.length ? `\n${(p.assumptions as string[]).join('\n')}` : ''
  if (p.formula || p.rule) return `= ${String(p.formula ?? p.rule)}（${(p.inputs as string[] | undefined)?.join('、') ?? ''}）${assumed}`
  if (p.conflict) return JSON.stringify(p.conflict)
  const rows = (p.rows as number[] | undefined)?.length ? `rows ${(p.rows as number[]).join(',')} (${String(p.rollup)})` : p.row && `row ${p.row}`
  const verified = p.verified_by_formula === true || p.verified_by_rule === true ? ' ✓' : ''
  return [p.department, p.file, p.sheet, rows, p.column].filter(Boolean).join(' · ') + verified + assumed
}

export function MasterTable({ batchId }: { batchId: string }) {
  const { t } = useUI()
  const [master, setMaster] = useState<Master | null>(null), [error, setError] = useState(''), [revision, setRevision] = useState(0)
  const [selection, setSelection] = useState<{ row: Row; column: string } | null>(null)
  useEffect(() => {
    const controller = new AbortController()
    setMaster(null); setError(''); setSelection(null)
    void api<Master>(`/integration/batches/${batchId}`, { signal: controller.signal }).then(value => { setMaster(value); if (value.rows.length) tourEvent('master', batchId) })
      .catch(e => { if (!controller.signal.aborted) setError(describeError(e, t)) })
    return () => controller.abort()
  }, [batchId, revision])
  useEffect(() => {
    const opened = () => { if (master?.rows.length) tourEvent('master', batchId) }
    window.addEventListener('bridgeflow:master-opened', opened)
    return () => window.removeEventListener('bridgeflow:master-opened', opened)
  }, [master, batchId])
  async function download() {
    try {
      const file = await api<{ filename: string; base64: string }>(`/integration/batches/${batchId}/xlsx`)
      const bytes = Uint8Array.from(atob(file.base64), c => c.charCodeAt(0))
      const link = document.createElement('a')
      link.href = URL.createObjectURL(new Blob([bytes], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }))
      link.download = file.filename
      link.click()
      tourEvent('download', batchId)
      URL.revokeObjectURL(link.href)
    } catch (e) { setError(describeError(e, t)) }
  }
  if (error) return <div><p role="alert" className="bf-error">{error}</p><button data-tour-recovery="" onClick={() => { setError(''); setRevision(n => n + 1) }}>{t('refresh')}</button></div>
  if (!master) return <p role="status" className="bf-loading">{t('loading')}</p>
  const traceColumn = master.columns.find(c => typeof master.rows[0]?.values[c] === 'number' && master.rows[0]?.provenance[c]?.department)
  const evidence = selection ? selection.row.provenance[selection.column] : null
  const selectedGrade = selection ? master.grades?.[master.rows.indexOf(selection.row)]?.[selection.column] : undefined
  return <section aria-label={t('integrationMaster')}>
    <div className="bf-card-head"><h3>{t('integrationMaster')}</h3><button data-tour-id="master-download" onClick={() => void download()}>{t('downloadMaster')}</button></div>
    <p data-tour-id="master-status" role="status">{master.rows.filter(row => row.complete).length} / {master.rows.length} {t('masterCompleteRows')} · {master.issues.length} {t('masterOpenQuestions')}</p>
    <p className="bf-hint">{t('integrationHelp')} · {master.version}</p>
    {master.grade_summary && <p className="bf-hint">{t('evidenceGrades')}：{['G1', 'G2', 'G3', 'G4'].map(g => `${g} ${master.grade_summary![g] ?? 0}`).join(' · ')}{master.grade_summary.missing ? ` · ${t('gradeMissing')} ${master.grade_summary.missing}` : ''} · {t('gradeLegend')}</p>}
    {Object.keys(master.assumptions ?? {}).length > 0 && <details className="bf-callout" data-tone="info">
      <summary>{t('integrationAssumptions')}（{Object.keys(master.assumptions!).length}）</summary>
      <ul>{Object.entries(master.assumptions!).map(([name, text]) => {
        const decided = master.conventions?.find(c => c.id === name)
        return <li key={name}>
          <strong>{name}</strong> <span className="bf-convention" data-state={decided?.state ?? 'unconfirmed'}>{t(`conventionState_${decided?.state ?? 'unconfirmed'}`)}</span>
          {decided && <span className="bf-hint"> · {t(`conventionKind_${decided.kind}`)}{decided.affected_fields.length ? ` · ${t('conventionAffects')} ${decided.affected_fields.join('、')}` : ''}</span>}
          <div>{text}</div>
          {decided && decided.state !== 'unconfirmed' && <div className="bf-hint">{t('conventionSource')}：{decided.source}（{decided.decided_by} · v{decided.version}）{decided.note ? ` · ${decided.note}` : ''}</div>}
          {decided?.declaration_change && <div className="bf-hint">{t('conventionDeclarationChange')}：<code>{decided.declaration_change}</code></div>}
        </li>
      })}</ul>
      <p className="bf-hint">{t('conventionHelp')}</p>
    </details>}
    <details data-tour-id="master-questions" className="bf-master-questions" onToggle={e => { if (e.currentTarget.open) tourEvent('issues', batchId) }}><summary data-tour-id="master-issues">{t('masterOpenQuestions')} · {master.issues.length}</summary>
    {master.issues.map((issue, i) => <div className="bf-callout" data-tone={issue.kind === 'undeclared_constant' ? 'info' : 'warn'} key={i}>
      <h3>{t(`issue_${issue.kind}`)}{issue.field ? ` · ${issue.field}` : ''}</h3><p>{issue.message}</p>
    </div>)}
    </details>
    {selection && evidence && <aside className="bf-cell-evidence" aria-label={t('masterEvidence')}>
      <h4>{t('masterEvidence')} · {selection.column} {selectedGrade && <GradeMark grade={selectedGrade} />}</h4><p>{cellText(selection.row.values[selection.column]).text}</p><p>{origin(evidence)}</p>
      {typeof evidence.department === 'string' && <button data-tour-id="evidence-source" onClick={() => navigate({ batch: batchId, view: 'source', source: String(evidence.department) })}>{t('masterOpenSource')}</button>}
    </aside>}
    {!master.rows.length && <div className="bf-empty"><strong>{t('empty')}</strong>{t('integrationNoRows')}</div>}
    {master.rows.length > 0 && <div className="bf-scroll"><table><thead><tr><th>{t('integrationRowState')}</th>{master.columns.map(c => <th scope="col" key={c}>{c}</th>)}</tr></thead>
      <tbody>{master.rows.map((row, i) => <tr key={i}><td><Chip status={row.complete ? 'ready' : 'partial'}/></td>{master.columns.map(c => {
        const { text, numeric, empty } = cellText(row.values[c])
        return <td key={c} data-numeric={numeric} data-empty={empty} title={origin(row.provenance[c])}>{row.provenance[c] ? <button className="bf-master-cell" data-tour-id={i === 0 && c === traceColumn ? 'master-evidence-open' : undefined} aria-label={`${t('masterSelectCell')}: ${c} · ${text}`} onClick={() => { setSelection({ row, column: c }); tourEvent('evidence', batchId) }}>{text}</button> : text}</td>
      })}</tr>)}</tbody></table></div>}
  </section>
}
