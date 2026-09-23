import { useEffect, useState, type ReactNode } from 'react'
import { api, describeError, formatNumber, navigate, useUI, type Summary } from './ui.ts'
import { FLOW } from './workflow-flow.tsx'
import { Explain } from './explain.tsx'

/**
 * The month at a glance: one read-only page over what the other pages own.
 *
 * Every number here is read from the endpoint the owning page reads, and every block opens
 * that page — the overview never decides or approves anything, so it cannot disagree with
 * the place where the decision is made. A source that cannot be read says so in its block
 * instead of showing a zero.
 *
 * Colour: one mark colour for magnitude, and the reserved critical colour only for "overdue"
 * or "refused", always with a mark and a word next to it (validated for CVD and contrast in
 * both themes; tokens `--bf-chart-mark` / `--bf-chart-critical`).
 */
type Step = { id: string; state: string; required: boolean }
type Checklist = { steps: Step[]; ready_to_close: boolean; refusal: string }
type Inbox = { total: number; by_department: Record<string, number> }
type Point = { label: string; value: number | null; period: string; breach: boolean }
type Chart = { id: string; kind: string; status: string; subject: string; unit: string; points: Point[]; threshold: number | null }
type BoardRow = { kind: string; state: string; overdue_hours?: number | null }
type Run = { run: string; started_at: string; refused: number; steps: number; tokens?: { total: number } }

/** Read one source; `undefined` while loading, an Error when it could not be read. */
function useSource<T>(path: string | null, deps: unknown[]): T | Error | undefined {
  const { t } = useUI()
  const [value, setValue] = useState<T | Error | undefined>(undefined)
  useEffect(() => {
    if (!path) { setValue(undefined); return }
    const controller = new AbortController()
    setValue(undefined)
    void api<T>(path, { signal: controller.signal }).then(setValue)
      .catch(e => { if (!controller.signal.aborted) setValue(new Error(describeError(e, t))) })
    return () => controller.abort()
  }, [path, ...deps])
  return value
}

function Block({ title, open, onOpen, children, wide = false }: { title: string; open: string; onOpen: () => void; children: ReactNode; wide?: boolean }) {
  return <section className="bf-ov-block" data-wide={wide} aria-label={title}>
    <header><h4>{title}</h4><button onClick={onOpen}>{open} ›</button></header>
    {children}
  </section>
}

function Unread({ value }: { value: unknown }) {
  const { t } = useUI()
  if (value === undefined) return <p className="bf-hint bf-loading">{t('loading')}</p>
  if (value instanceof Error) return <p className="bf-hint" role="alert">{t('ovUnreadable')} {value.message}</p>
  return null
}

/** Horizontal bars: magnitude in one colour, an optional critical share drawn as its own segment. */
function BarList({ rows, unit = '', empty = '' }: { rows: { label: string; value: number; critical?: number; note?: string }[]; unit?: string; empty?: string }) {
  const { t, language } = useUI()
  const [hover, setHover] = useState(-1)
  const widest = Math.max(...rows.map(r => r.value), 1)
  if (!rows.length) return <p className="bf-hint">{empty || t('ovNothing')}</p>
  return <ul className="bf-ov-bars">
    {rows.map((row, i) => {
      const late = Math.min(row.critical ?? 0, row.value)
      return <li key={row.label} onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(-1)} data-hover={hover === i}>
        <span className="bf-ov-bar-label" title={row.label}>{row.label}</span>
        <span className="bf-ov-bar-track" aria-hidden="true">
          {row.value > late && <span className="bf-ov-bar" style={{ width: `${((row.value - late) / widest) * 100}%` }} />}
          {late > 0 && <span className="bf-ov-bar" data-critical="true" style={{ width: `${(late / widest) * 100}%` }} />}
        </span>
        <span className="bf-ov-bar-value">{formatNumber(row.value, language)}{unit}
          {late > 0 && <small className="bf-ov-critical"> ▲ {t('flowOverdue').replaceAll('{n}', String(late))}</small>}</span>
        {hover === i && row.note && <span role="tooltip" className="bf-ov-tip">{row.note}</span>}
      </li>
    })}
  </ul>
}

/** A small single-series trend with a hover crosshair; a missing month breaks the line. */
function Spark({ chart }: { chart: Chart }) {
  const { language, t } = useUI()
  const [hover, setHover] = useState(-1)
  const W = 220, H = 64, P = 6
  const values = chart.points.map(p => p.value).filter((v): v is number => v !== null)
  const low = Math.min(...values, chart.threshold ?? Infinity), high = Math.max(...values, chart.threshold ?? -Infinity)
  const y = (v: number) => H - P - ((v - low) / (high - low || 1)) * (H - P * 2)
  const x = (i: number) => P + (i * (W - P * 2)) / Math.max(chart.points.length - 1, 1)
  const segments: string[][] = [[]]
  chart.points.forEach((p, i) => { if (p.value === null) segments.push([]); else segments[segments.length - 1]!.push(`${x(i)},${y(p.value)}`) })
  const last = [...chart.points].reverse().find(p => p.value !== null)
  const shown = hover >= 0 ? chart.points[hover] : last
  const show = (p: Point | undefined) => p?.value == null ? '—' : `${formatNumber(p.value, language, { maximumFractionDigits: 2 })}${chart.unit === '%' ? '%' : chart.unit ? ` ${chart.unit}` : ''}`
  return <figure className="bf-ov-spark">
    <figcaption><span>{t(`chart_${chart.id}`) === `chart_${chart.id}` ? chart.subject : t(`chart_${chart.id}`)}</span>
      <b>{show(shown)}{shown?.breach && <small className="bf-ov-critical"> ▲ {t('chartBreach')}</small>}</b>
      <small className="bf-hint">{shown?.period ?? ''}</small></figcaption>
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={chart.points.map(p => `${p.period} ${show(p)}`).join('; ')}
      onMouseMove={e => { const box = e.currentTarget.getBoundingClientRect(); const i = Math.round(((e.clientX - box.left) / box.width * W - P) / ((W - P * 2) / Math.max(chart.points.length - 1, 1))); setHover(Math.max(0, Math.min(chart.points.length - 1, i))) }}
      onMouseLeave={() => setHover(-1)}>
      {chart.threshold !== null && <line className="bf-ov-threshold" x1={P} x2={W - P} y1={y(chart.threshold)} y2={y(chart.threshold)} />}
      {segments.filter(s => s.length > 1).map((s, i) => <polyline key={i} className="bf-ov-line" points={s.join(' ')} />)}
      {hover >= 0 && <line className="bf-ov-cross" x1={x(hover)} x2={x(hover)} y1={0} y2={H} />}
      {chart.points.map((p, i) => p.value !== null && (p.breach || i === hover || p === last) &&
        <circle key={i} cx={x(i)} cy={y(p.value)} r={4} className="bf-ov-dot" data-critical={p.breach} />)}
    </svg>
  </figure>
}

export function Overview({ batchId }: { batchId: string }) {
  const { t, language } = useUI()
  const [tables, setTables] = useState(false)
  const summary = useSource<Summary>(batchId ? `/batches/${batchId}` : null, [])
  const period = summary && !(summary instanceof Error) ? summary.period : ''
  const checklist = useSource<Checklist>(period ? `/monthly/checklist?period=${encodeURIComponent(period)}` : null, [])
  const inbox = useSource<Inbox>(period ? `/monthly/inbox?period=${encodeURIComponent(period)}` : null, [])
  const charts = useSource<{ charts: Chart[]; refusal?: string }>(batchId ? `/conclusions/batches/${batchId}/charts` : null, [])
  const board = useSource<{ rows: BoardRow[] }>('/workflow/board', [])
  const runs = useSource<{ runs: Run[] }>('/journal/runs?limit=12', [])
  const go = (view: string) => navigate({ ...(batchId ? { batch: batchId } : {}), view })
  const ok = <T,>(v: T | Error | undefined): v is T => v !== undefined && !(v instanceof Error)

  const done = ok(checklist) ? checklist.steps.filter(s => s.state === 'done').length : 0
  const total = ok(checklist) ? checklist.steps.length : 0
  const rows = ok(board) ? board.rows.filter(r => r.kind !== 'partial') : []
  const inFlight = rows.filter(r => r.state !== 'completed').length
  const overdue = rows.filter(r => (r.overdue_hours ?? -1) > 0).length
  const stages = FLOW.map(stage => ({
    label: t(`flowStage_${stage.id}`), value: rows.filter(r => (stage.states as readonly string[]).includes(r.state)).length,
    critical: rows.filter(r => (stage.states as readonly string[]).includes(r.state) && (r.overdue_hours ?? -1) > 0).length }))
  const departments = ok(inbox) ? Object.entries(inbox.by_department).sort((a, b) => b[1] - a[1]).map(([label, value]) => ({ label: t(label), value })) : []
  const runList = ok(runs) ? runs.runs.slice().reverse() : []
  const tokens = runList.reduce((n, r) => n + (r.tokens?.total ?? 0), 0), refused = runList.reduce((n, r) => n + r.refused, 0)
  const trends = ok(charts) ? charts.charts.filter(c => c.kind === 'trend' && c.status === 'ready') : []
  const entityBars = ok(charts) ? charts.charts.filter(c => c.kind === 'entity_bars' && c.status === 'ready' && c.points.every(p => (p.value ?? 0) >= 0)).slice(0, 2) : []
  const chartName = (c: Chart) => t(`chart_${c.id}`) === `chart_${c.id}` ? c.subject : t(`chart_${c.id}`)

  const tile = (label: string, value: ReactNode, note: ReactNode, view: string, tone = '') =>
    <button className="bf-ov-tile" data-tone={tone} onClick={() => go(view)}><span>{label}</span><b>{value}</b><small>{note}</small></button>

  return <section className="bf-overview" aria-label={t('overview')}>
    <header className="bf-ov-head"><div><h3>{t('overview')}</h3><p className="bf-hint">{period ? `${period} · ` : ''}{t('overviewIntro')}</p></div>
      <button aria-pressed={tables} onClick={() => setTables(!tables)}>{t(tables ? 'ovHideTables' : 'ovShowTables')}</button></header>
    <Explain text={t('overviewHow')} />
    {!batchId && <p className="bf-callout">{t('ovNoBatch')}</p>}
    <div className="bf-ov-kpis">
      {batchId && tile(t('ovClose'), ok(checklist) ? `${done} / ${total}` : '—',
        ok(checklist) ? <><span className="bf-ov-meter" aria-hidden="true"><span style={{ width: `${total ? (done / total) * 100 : 0}%` }} /></span>{checklist.ready_to_close ? t('ovReady') : t('ovNotReady')}</> : <Unread value={checklist} />, 'tasks')}
      {batchId && tile(t('ovOpenItems'), ok(inbox) ? formatNumber(inbox.total, language) : '—', ok(inbox) ? t('ovOpenItemsNote') : <Unread value={inbox} />, 'tasks')}
      {tile(t('ovWorkflow'), ok(board) ? formatNumber(inFlight, language) : '—',
        ok(board) ? (overdue ? <span className="bf-ov-critical">▲ {t('flowOverdue').replaceAll('{n}', String(overdue))}</span> : t('ovNoneOverdue')) : <Unread value={board} />, 'handoff', overdue ? 'critical' : '')}
      {tile(t('ovRuns'), ok(runs) ? formatNumber(runList.length, language) : '—',
        ok(runs) ? <>{formatNumber(tokens, language)} tokens · {refused ? <span className="bf-ov-critical">✕ {refused} {t('ovRefused')}</span> : t('ovNoRefusals')}</> : <Unread value={runs} />, batchId ? 'records' : 'handoff')}
    </div>
    <div className="bf-ov-grid">
      {batchId && <Block wide title={t('ovTrends')} open={t('monthlyBrief')} onOpen={() => go('brief')}>
        {ok(charts) ? (charts.refusal ? <p className="bf-hint">{charts.refusal}</p> : trends.length || entityBars.length ? <>
          {trends.length > 0 && <div className="bf-ov-sparks">{trends.map(c => <Spark key={c.id} chart={c} />)}</div>}
          {!trends.length && <p className="bf-hint">{t('chartNeedsPeriods')}</p>}
          {entityBars.length > 0 && <div className="bf-ov-sparks" data-bars="true">{entityBars.map(c => <figure key={c.id} className="bf-ov-spark">
            <figcaption><span>{chartName(c)}{c.unit ? ` · ${c.unit}` : ''}</span></figcaption>
            <BarList rows={c.points.map(p => ({ label: p.label, value: p.value ?? 0, note: p.breach ? `▲ ${t('chartBreach')}` : p.period }))} />
          </figure>)}</div>}</>
          : <p className="bf-hint">{t('chartNeedsPeriods')}</p>) : <Unread value={charts} />}
        {tables && trends.length > 0 && <table className="bf-chart-table"><thead><tr><th scope="col">{t('ovMetric')}</th>{trends[0]!.points.map(p => <th key={p.label} scope="col">{p.period}</th>)}</tr></thead>
          <tbody>{trends.map(c => <tr key={c.id}><th scope="row">{c.subject}</th>{c.points.map(p => <td key={p.label} data-numeric="true">{p.value === null ? '—' : formatNumber(p.value, language, { maximumFractionDigits: 2 })}{p.breach ? ' ▲' : ''}</td>)}</tr>)}</tbody></table>}
      </Block>}
      {batchId && <Block title={t('ovByDepartment')} open={t('monthlyTasks')} onOpen={() => go('tasks')}>
        {ok(inbox) ? <BarList rows={departments} /> : <Unread value={inbox} />}
        {tables && ok(inbox) && <DataTable rows={departments.map(d => [d.label, d.value])} head={[t('ovDepartment'), t('ovOpenItems')]} />}
      </Block>}
      <Block title={t('ovStages')} open={t('handoffWorkspace')} onOpen={() => go('handoff')}>
        {ok(board) ? <BarList rows={stages} /> : <Unread value={board} />}
        {tables && ok(board) && <DataTable rows={stages.map(s => [s.label, s.value, s.critical])} head={[t('ovStage'), t('ovRecords'), t('ovOverdue')]} />}
      </Block>
      <Block title={t('ovRunTokens')} open={t('records')} onOpen={() => go(batchId ? 'records' : 'handoff')}>
        {ok(runs) ? <BarList rows={runList.map(r => ({ label: new Date(r.started_at).toLocaleTimeString(language === 'zh' ? 'zh-CN' : 'en-GB', { hour: '2-digit', minute: '2-digit' }),
          value: r.tokens?.total ?? 0, note: `${r.steps} ${t('ovSteps')}${r.refused ? ` · ✕ ${r.refused} ${t('ovRefused')}` : ''}` }))} empty={t('ovNoRuns')} /> : <Unread value={runs} />}
        {tables && ok(runs) && <DataTable rows={runList.map(r => [r.started_at, r.steps, r.tokens?.total ?? 0, r.refused])} head={[t('ovStarted'), t('ovSteps'), 'tokens', t('ovRefused')]} />}
      </Block>
    </div>
  </section>
}

function DataTable({ head, rows }: { head: string[]; rows: (string | number)[][] }) {
  return <table className="bf-chart-table"><thead><tr>{head.map(h => <th key={h} scope="col">{h}</th>)}</tr></thead>
    <tbody>{rows.map((row, i) => <tr key={i}>{row.map((cell, j) => <td key={j} data-numeric={typeof cell === 'number'}>{cell}</td>)}</tr>)}</tbody></table>
}
