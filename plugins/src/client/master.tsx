import { useEffect, useState } from 'react'
import { api, cellText, describeError, useUI } from './ui.ts'
import { Chip } from './workspace.tsx'

/**
 * The 跨部门业务整合总表 for the selected batch, built from the business dictionary (字典 v2).
 * Read-only: each cell shows where it came from on hover; open items are listed with the
 * departments involved. The workbook download keeps the master template's column order.
 */
type Issue = { kind: string; field: string; key: string[]; departments: string[]; message: string }
type Row = { key: string[]; values: Record<string, unknown>; provenance: Record<string, Record<string, unknown>>; complete: boolean }
type Master = { version: string; columns: string[]; rows: Row[]; issues: Issue[] }

function origin(p: Record<string, unknown> | undefined): string {
  if (!p) return ''
  if (p.formula) return `= ${String(p.formula)}（${(p.inputs as string[] | undefined)?.join('、') ?? ''}）`
  if (p.conflict) return JSON.stringify(p.conflict)
  return [p.department, p.file, p.sheet, p.row && `row ${p.row}`, p.column].filter(Boolean).join(' · ') + (p.verified_by_formula === true ? ' ✓' : '')
}

export function MasterTable({ batchId }: { batchId: string }) {
  const { t } = useUI()
  const [master, setMaster] = useState<Master | null>(null), [error, setError] = useState('')
  useEffect(() => {
    const controller = new AbortController()
    setMaster(null); setError('')
    void api<Master>(`/integration/batches/${batchId}`, { signal: controller.signal }).then(setMaster)
      .catch(e => { if (!controller.signal.aborted) setError(describeError(e, t)) })
    return () => controller.abort()
  }, [batchId])
  async function download() {
    try {
      const file = await api<{ filename: string; base64: string }>(`/integration/batches/${batchId}/xlsx`)
      const bytes = Uint8Array.from(atob(file.base64), c => c.charCodeAt(0))
      const link = document.createElement('a')
      link.href = URL.createObjectURL(new Blob([bytes], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }))
      link.download = file.filename
      link.click()
      URL.revokeObjectURL(link.href)
    } catch (e) { setError(describeError(e, t)) }
  }
  if (error) return <p role="alert" className="bf-error">{error}</p>
  if (!master) return <p role="status">{t('loading')}</p>
  return <section aria-label={t('integrationMaster')}>
    <div className="bf-card-head"><h3>{t('integrationMaster')}</h3><button onClick={() => void download()}>{t('downloadMaster')}</button></div>
    <p className="bf-hint">{t('integrationHelp')} · {master.version}</p>
    {master.issues.map((issue, i) => <div className="bf-callout" data-tone={issue.kind === 'undeclared_constant' ? 'info' : 'warn'} key={i}>
      <h3>{t(`issue_${issue.kind}`)}{issue.field ? ` · ${issue.field}` : ''}</h3><p>{issue.message}</p>
    </div>)}
    {!master.rows.length && <div className="bf-empty"><strong>{t('empty')}</strong>{t('integrationNoRows')}</div>}
    {master.rows.length > 0 && <div className="bf-scroll"><table><thead><tr><th>{t('integrationRowState')}</th>{master.columns.map(c => <th scope="col" key={c}>{c}</th>)}</tr></thead>
      <tbody>{master.rows.map((row, i) => <tr key={i}><td><Chip status={row.complete ? 'ready' : 'partial'}/></td>{master.columns.map(c => {
        const { text, numeric, empty } = cellText(row.values[c])
        return <td key={c} data-numeric={numeric} data-empty={empty} title={origin(row.provenance[c])}>{text}</td>
      })}</tr>)}</tbody></table></div>}
  </section>
}
