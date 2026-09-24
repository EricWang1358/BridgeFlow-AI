import { useEffect, useState } from 'react'
import { api, describeError, navigate, useUI } from './ui.ts'

/**
 * Declared charts for a batch (E13-UC03).
 *
 * Drawn as inline SVG from the same numbers the table below each chart lists, so the two
 * cannot disagree and a screen reader loses nothing. A gap in a trend stays a gap: the line
 * breaks rather than passing through a month nobody reported. Status never rests on colour
 * alone — a breached point carries a mark and the table says so in words.
 */
type Point = { label: string; value: number | null; batch_id: string; period: string; key: string[]; part: string; breach: boolean; grade: string }
type Chart = { id: string; kind: string; status: string; subject: string; unit: string; points: Point[]
  threshold: number | null; threshold_label: string; reason: string; grade: string }

const WIDTH = 520, HEIGHT = 160, PAD = 28

function format(value: number | null, unit: string) {
  if (value === null) return '—'
  const rounded = Math.abs(value) >= 1000 ? value.toLocaleString(undefined, { maximumFractionDigits: 0 })
    : value.toLocaleString(undefined, { maximumFractionDigits: 2 })
  return unit ? `${rounded}${unit === '%' ? '%' : ` ${unit}`}` : rounded
}

function scale(values: number[]) {
  const low = Math.min(...values, 0), high = Math.max(...values, 0)
  const span = high - low || 1
  return (value: number) => HEIGHT - PAD - ((value - low) / span) * (HEIGHT - PAD * 2)
}

function Trend({ chart, onPoint }: { chart: Chart; onPoint: (p: Point) => void }) {
  const { t } = useUI()
  const measured = chart.points.filter(p => p.value !== null)
  const y = scale([...measured.map(p => p.value as number), ...(chart.threshold === null ? [] : [chart.threshold])])
  const x = (index: number) => PAD + (index * (WIDTH - PAD * 2)) / Math.max(chart.points.length - 1, 1)
  // A gap breaks the line instead of being interpolated: the reader must see the month is missing.
  const segments: string[] = []
  let current: string[] = []
  chart.points.forEach((point, index) => {
    if (point.value === null) { if (current.length > 1) segments.push(current.join(' ')); current = []; return }
    current.push(`${x(index)},${y(point.value)}`)
  })
  if (current.length > 1) segments.push(current.join(' '))
  return <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="bf-chart" role="img"
    aria-label={`${chart.subject} · ${measured.map(p => `${p.period} ${format(p.value, chart.unit)}`).join('; ')}`}>
    {chart.threshold !== null && <>
      <line x1={PAD} x2={WIDTH - PAD} y1={y(chart.threshold)} y2={y(chart.threshold)} className="bf-chart-threshold" />
      <text x={WIDTH - PAD} y={y(chart.threshold) - 4} textAnchor="end" className="bf-chart-label">
        {t('chartThreshold')} {format(chart.threshold, chart.unit)}</text>
    </>}
    {segments.map((points, i) => <polyline key={i} points={points} className="bf-chart-line" />)}
    {chart.points.map((point, index) => point.value === null
      ? <text key={point.label} x={x(index)} y={HEIGHT - PAD / 2} textAnchor="middle" className="bf-chart-label">{point.label} ·{t('chartGap')}</text>
      : <g key={point.label}>
        <circle cx={x(index)} cy={y(point.value)} r={5} className="bf-chart-point" data-breach={point.breach}
          onClick={() => onPoint(point)} role="button" tabIndex={0} aria-label={`${point.period} ${format(point.value, chart.unit)}`}
          onKeyDown={e => { if (e.key === 'Enter') onPoint(point) }} />
        {point.breach && <text x={x(index)} y={y(point.value) - 10} textAnchor="middle" className="bf-chart-label">▲</text>}
        <text x={x(index)} y={HEIGHT - PAD / 2} textAnchor="middle" className="bf-chart-label">{point.label}</text>
      </g>)}
  </svg>
}

function Bars({ chart, onPoint }: { chart: Chart; onPoint: (p: Point) => void }) {
  const values = chart.points.map(p => p.value ?? 0)
  const widest = Math.max(...values.map(Math.abs), 1)
  return <div className="bf-chart-bars" role="img" aria-label={chart.points.map(p => `${p.label} ${format(p.value, chart.unit)}`).join('; ')}>
    {chart.points.map(point => <button key={point.label} className="bf-chart-bar" data-breach={point.breach}
      data-part={point.part} onClick={() => onPoint(point)}>
      <span className="bf-chart-bar-label">{point.breach ? '▲ ' : ''}{point.label}</span>
      <span className="bf-chart-bar-track"><span style={{ width: `${(Math.abs(point.value ?? 0) / widest) * 100}%` }} data-negative={(point.value ?? 0) < 0} /></span>
      <span className="bf-chart-bar-value">{format(point.value, chart.unit)}</span>
    </button>)}
  </div>
}

export function MetricCharts({ batchId }: { batchId: string }) {
  const { t } = useUI()
  const [charts, setCharts] = useState<{ charts: Chart[]; refusal?: string } | null>(null), [error, setError] = useState('')
  const [tables, setTables] = useState<Record<string, boolean>>({}), [revision, setRevision] = useState(0)
  // Only a sample batch is offered the sample's earlier months; a real batch never is.
  const [sample, setSample] = useState(false)
  const short = !!charts?.charts.some(c => c.status === 'needs_more_periods')
  useEffect(() => {
    if (!short) return
    const controller = new AbortController()
    void api<{ demo_case?: string | null }>(`/batches/${batchId}`, { signal: controller.signal })
      .then(summary => setSample(!!summary.demo_case)).catch(() => setSample(false))
    return () => controller.abort()
  }, [batchId, short])
  useEffect(() => {
    const controller = new AbortController()
    setCharts(null); setError('')
    void api<{ charts: Chart[]; refusal?: string }>(`/conclusions/batches/${batchId}/charts`, { signal: controller.signal })
      .then(setCharts).catch(e => { if (!controller.signal.aborted) setError(describeError(e, t)) })
    return () => controller.abort()
  }, [batchId, revision])
  if (error) return <p role="alert" className="bf-error">{error}</p>
  if (!charts) return <p role="status" className="bf-loading">{t('loading')}</p>
  if (charts.refusal) return <p className="bf-hint">{charts.refusal}</p>
  function open(point: Point) {
    if (point.batch_id) navigate({ batch: point.batch_id, view: 'integration' })
    else navigate({ batch: batchId, view: 'integration' })
  }
  return <section className="bf-charts" aria-label={t('metricCharts')}>
    <h3>{t('metricCharts')}</h3>
    {sample && short && <SampleHistory onLoaded={() => setRevision(n => n + 1)} />}
    {charts.charts.map(chart => <article key={chart.id} className="bf-chart-card">
      <h4>{t(`chart_${chart.id}`) === `chart_${chart.id}` ? chart.subject : t(`chart_${chart.id}`)}
        {chart.unit && <span className="bf-hint"> · {chart.unit}</span>}
        {chart.grade && <span className="bf-grade" data-grade={chart.grade}>{chart.grade}</span>}</h4>
      {chart.status === 'ready'
        ? chart.kind === 'trend' ? <Trend chart={chart} onPoint={open} /> : <Bars chart={chart} onPoint={open} />
        : <p className="bf-hint">{chart.status === 'needs_more_periods' ? t('chartNeedsPeriods') : t('chartUnavailable')}{chart.reason ? ` — ${chart.reason}` : ''}</p>}
      <button onClick={() => setTables(state => ({ ...state, [chart.id]: !state[chart.id] }))}>
        {tables[chart.id] ? t('chartHideTable') : t('chartShowTable')}</button>
      {tables[chart.id] && <table className="bf-chart-table"><thead><tr>
        <th scope="col">{t('chartPoint')}</th><th scope="col">{t('value')}</th><th scope="col">{t('chartState')}</th></tr></thead>
        <tbody>{chart.points.map(point => <tr key={point.label}>
          <td>{point.label}</td><td data-numeric="true">{format(point.value, chart.unit)}</td>
          <td>{point.value === null ? t('chartGapCell') : point.breach ? t('chartBreach') : t('chartWithin')}
            {point.grade && <span className="bf-grade" data-grade={point.grade}>{point.grade}</span>}</td>
        </tr>)}</tbody></table>}
    </article>)}
  </section>
}

/**
 * A sample batch has one month; its supplier's earlier months are one click away, so a
 * trend can be seen without pretending the sample already had history.
 */
export function SampleHistory({ onLoaded }: { onLoaded: () => void }) {
  const { t } = useUI()
  const [busy, setBusy] = useState(false), [error, setError] = useState('')
  return <p className="bf-hint">{t('sampleHistoryHelp')}{' '}
    <button disabled={busy} onClick={() => {
      setBusy(true); setError('')
      void api('/batches/demo/history', { method: 'POST' }).then(onLoaded)
        .catch(e => setError(describeError(e, t))).finally(() => setBusy(false))
    }}>{t(busy ? 'busy' : 'sampleHistory')}</button>
    {error && <span role="alert" className="bf-error"> {error}</span>}</p>
}
