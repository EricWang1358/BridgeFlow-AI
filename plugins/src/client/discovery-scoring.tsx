import { useEffect, useState, type FormEvent } from 'react'
import { api, describeError, useUI, useDataRevision } from './ui.ts'
import { Sources, type Ref } from './flow-graph.tsx'

type Axis = { title: string; unit: string; minimum: string; maximum: string; split: string; split_is_high: boolean; low_meaning: string; high_meaning: string }
type Policy = { id: string; version: number; fingerprint: string; declared_by: string; declaration_ref: string; effort: Axis; value: Axis }
type Rating = { score?: string | null; rationale: string; references: Ref[] }
type Coordinates = { effort: { score: string; normalized: string; side: string }; value: { score: string; normalized: string; side: string } }
export type Score = { id: string; project_id: string; opportunity_id: string; opportunity_title?: string; opportunity_version: number; seq: number; version: number; policy_fingerprint: string; effort: Rating | null; value: Rating | null; actor?: string; coordinates: Coordinates | null; not_plotted_reasons: string[] }
const reasons: Record<string, [string, string]> = {
  candidate_or_evidence_revised: ['候选或依据已修订', 'Candidate or evidence revised'],
  policy_revised: ['量表已改变', 'Policy changed'],
  effort_incomplete: ['投入评分缺少分值、理由或依据', 'Effort rating needs a score, rationale and evidence'],
  value_incomplete: ['价值评分缺少分值、理由或依据', 'Value rating needs a score, rationale and evidence'],
  effort_evidence_revised: ['投入评分依据已修订', 'Effort evidence revised'],
  value_evidence_revised: ['价值评分依据已修订', 'Value evidence revised'],
}
const empty = (): Rating => ({ score: '', rationale: '', references: [] })

function PolicyView({ policy }: { policy: Policy }) {
  const { language } = useUI(), zh = language === 'zh'
  return <section aria-label={zh ? '评分量表' : 'Scoring policy'}><h4>{policy.id} · v{policy.version}</h4><p>{policy.declared_by} · {policy.declaration_ref}</p>{(['effort', 'value'] as const).map(key => { const a = policy[key]; return <p key={key}><strong>{a.title} ({a.unit})</strong>: {a.minimum}–{a.maximum} · {zh ? '分界' : 'Split'} {a.split} ({a.split_is_high ? (zh ? '等于分界算高' : 'Tie is high') : (zh ? '等于分界算低' : 'Tie is low')})<br />{a.low_meaning} / {a.high_meaning}</p> })}</section>
}

export function ScoreEditor({ project, opportunity, initial }: { project: string; opportunity: { id: string; seq: number }; initial?: Score | undefined }) {
  const { language, t } = useUI(), zh = language === 'zh'
  const dataRevision = useDataRevision()
  const [policy, setPolicy] = useState<Policy | null>(null), [error, setError] = useState(''), [request, setRequest] = useState('')
  const [ratings, setRatings] = useState({ effort: initial?.effort ?? empty(), value: initial?.value ?? empty() })
  const [revision, setRevision] = useState(0), [copied, setCopied] = useState(false)
  useEffect(() => {
    const abort = new AbortController(); setPolicy(null); setRequest(''); setError('')
    void api<Policy>(`/discovery/${project}/scoring-policy`, { signal: abort.signal }).then(setPolicy).catch(e => { if (!abort.signal.aborted) setError(describeError(e, t)) })
    return () => abort.abort()
  }, [project, revision, dataRevision])
  function update(key: 'effort' | 'value', change: Partial<Rating>) { setRatings(r => ({ ...r, [key]: { ...r[key], ...change } })); setRequest(''); setCopied(false) }
  function prepare(e: FormEvent<HTMLFormElement>) {
    e.preventDefault(); if (!policy) return
    const form = new FormData(e.currentTarget)
    const axes = Object.fromEntries((['effort', 'value'] as const).map(key => { const r = ratings[key]; return [key, { ...(r.score ? { score: r.score } : {}), rationale: r.rationale, references: r.references.map(ref => ({ ...ref, locator: { kind: ref.locator.kind,
      ...(ref.locator.kind !== 'lines' ? { sheet: ref.locator.sheet } : {}), ...(ref.locator.kind !== 'header' ? { start: ref.locator.start, end: ref.locator.end } : {}) } })) }] }))
    const score = { id: initial?.id ?? String(form.get('id')), project_id: project, opportunity_id: opportunity.id,
      opportunity_version: opportunity.seq, expected_seq: initial?.seq ?? 0, policy_fingerprint: policy.fingerprint, ...axes }
    setRequest(`Please call discovery_score_save with these exact arguments, and wait for native approval:\n${JSON.stringify({ score }, null, 2)}`)
    setError(''); setCopied(false)
  }
  return <section aria-label={zh ? '候选评分编辑' : 'Opportunity rating editor'}><h3>{zh ? '候选评分' : 'Rate opportunity'} · {opportunity.id} · v{opportunity.seq}</h3>
    <p>{zh ? '按声明的量表打分，不确定的可以留空。缺分数、理由或依据的那一轴不会画到图上。打分之后，立项仍要另行批准。' : 'Score against the declared scale; leave anything you are unsure of blank. An axis without a score, reason and evidence is not plotted. The project is approved separately.'}</p>
    {error && <p role="alert">{error}</p>}<button onClick={() => setRevision(n => n + 1)}>{zh ? '重新读取量表' : 'Reload policy'}</button>
    {policy && <><PolicyView policy={policy} />{initial && initial.policy_fingerprint !== policy.fingerprint && <p role="alert">{zh ? '量表已变更，请重新核对两轴评分。' : 'The scale has changed; check both scores again.'}</p>}
      <form onSubmit={prepare} onChange={() => { setRequest(''); setCopied(false) }}><label>{zh ? '评分标识' : 'Rating ID'}<input name="id" required readOnly={!!initial} defaultValue={initial?.id ?? ''} pattern="[a-zA-Z0-9]([a-zA-Z0-9_]|-){0,79}" /></label>
        {(['effort', 'value'] as const).map(key => <fieldset key={key} aria-label={zh ? (key === 'effort' ? '投入评分' : '价值评分') : `${key} rating`}><legend>{policy[key].title}</legend>
          <label>{zh ? '分值（可留空）' : 'Score (optional)'}<input inputMode="decimal" pattern="-?[0-9]+(\.[0-9]{1,6})?" maxLength={24} value={ratings[key].score ?? ''} onChange={e => update(key, { score: e.target.value })} /></label>
          <label>{zh ? '评分理由' : 'Rating rationale'}<textarea maxLength={1200} value={ratings[key].rationale} onChange={e => update(key, { rationale: e.target.value })} /></label>
          <Sources value={ratings[key].references} onChange={references => update(key, { references })} />
        </fieldset>)}
        <button type="submit">{zh ? '准备评分审批请求' : 'Prepare rating approval'}</button>
      </form>
    </>}
    {request && <><p>{zh ? '还没保存。把它粘贴到对话里，在那里批准。' : 'Not saved yet. Paste this into the chat and approve it there.'}</p><textarea rows={10} readOnly aria-label={zh ? '评分审批请求' : 'Rating approval request'} value={request} /><button onClick={() => { void navigator.clipboard.writeText(request).then(() => setCopied(true)).catch(() => setError(zh ? '复制失败，请手动选择。' : 'Copy failed; select manually.')) }}>{zh ? '复制评分请求' : 'Copy rating request'}</button>{copied && <p role="status">{zh ? '已复制。' : 'Copied.'}</p>}</>}
  </section>
}

export function ScoreBoard({ project, onEdit }: { project: string; onEdit: (score: Score) => void }) {
  const { language, t } = useUI(), zh = language === 'zh'
  const dataRevision = useDataRevision()
  const [page, setPage] = useState<{ items: Score[]; total: number; has_more: boolean } | null>(null), [policy, setPolicy] = useState<Policy | null>(null)
  const [offset, setOffset] = useState(0), [revision, setRevision] = useState(0), [error, setError] = useState(''), [selected, setSelected] = useState<Score | null>(null)
  const titled = (score: Score) => { const name = score.opportunity_title || score.opportunity_id; return name.length > 18 ? `${name.slice(0, 17)}…` : name }
  useEffect(() => {
    const abort = new AbortController(); setPage(null); setPolicy(null); setSelected(null); setError('')
    void Promise.all([api<Policy>(`/discovery/${project}/scoring-policy`, { signal: abort.signal }), api<{ items: Score[]; total: number; has_more: boolean }>(`/discovery/${project}/score?offset=${offset}&limit=50`, { signal: abort.signal })]).then(([p, list]) => { setPolicy(p); setPage(list) }).catch(e => { if (!abort.signal.aborted) setError(describeError(e, t)) })
    return () => abort.abort()
  }, [project, offset, revision, dataRevision])
  async function select(score: Score) {
    try { setSelected(await api<Score>(`/discovery/${project}/score/${score.id}?version=${score.version}`)) }
    catch (e) { setError(describeError(e, t)) }
  }
  const split = (axis: Axis) => (Number(axis.split) - Number(axis.minimum)) / (Number(axis.maximum) - Number(axis.minimum))
  return <section aria-label={zh ? '评分四象限' : 'Rating quadrants'}><h3>{zh ? '评分四象限' : 'Rating quadrants'}</h3><button onClick={() => setRevision(n => n + 1)}>{t('refresh')}</button>
    <p>{zh ? '只画出当前量表下依据齐全的评分；点的位置只是参考，立项要另行决定。重叠的点可以从列表里分别打开。' : 'Only complete scores under the current scale are plotted. A point\'s position is guidance; the project is decided separately. Open overlapping points from the list.'}</p>
    {error && <p role="alert">{error}</p>}{policy && page && <><PolicyView policy={policy} />
      <div data-tour-id="quadrant-chart"><svg role="img" aria-label={zh ? '投入与价值四象限' : 'Effort and value quadrants'} viewBox="0 0 400 340" className="bf-quadrant">
        <rect x="45" y="25" width="320" height="270" fill="none" stroke="currentColor" />
        <path d={`M ${45 + split(policy.effort) * 320} 25 V 295 M 45 ${295 - split(policy.value) * 270} H 365`} stroke="#94a3b8" strokeDasharray="5 4" />
        <text x="200" y="326" textAnchor="middle" fontSize="12" fill="currentColor">{policy.effort.title} →</text><text x="45" y="16" fontSize="12" fill="currentColor">{policy.value.title} ↑</text>
        {/* Each quadrant named by the declared meanings of its two sides, so the picture reads without the legend. */}
        {([[false, true, 51, 42, 'start'], [true, true, 359, 42, 'end'], [false, false, 51, 287, 'start'], [true, false, 359, 287, 'end']] as const).map(([effortHigh, valueHigh, x, y, anchor]) =>
          <text key={`${effortHigh}${valueHigh}`} x={x} y={y} textAnchor={anchor} fontSize="11" className="bf-quadrant-label">
            {valueHigh ? policy.value.high_meaning : policy.value.low_meaning} · {effortHigh ? policy.effort.high_meaning : policy.effort.low_meaning}</text>)}
        <text x="45" y="310" fontSize="10" className="bf-quadrant-label">{policy.effort.minimum}</text><text x="365" y="310" textAnchor="end" fontSize="10" className="bf-quadrant-label">{policy.effort.maximum}</text>
        <text x="40" y="295" textAnchor="end" fontSize="10" className="bf-quadrant-label">{policy.value.minimum}</text><text x="40" y="30" textAnchor="end" fontSize="10" className="bf-quadrant-label">{policy.value.maximum}</text>
        {page.items.filter(s => s.coordinates && s.policy_fingerprint === policy.fingerprint).map(s => <circle key={s.id} role="button" tabIndex={0} aria-label={`${s.opportunity_id} · ${s.id}`} cx={45 + Number(s.coordinates!.effort.normalized) * 320} cy={295 - Number(s.coordinates!.value.normalized) * 270} r="7" className="bf-quadrant-dot" onClick={() => void select(s)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); void select(s) } }}><title>{s.id}: {s.coordinates!.effort.score}, {s.coordinates!.value.score}</title></circle>)}
        {page.items.filter(s => s.coordinates && s.policy_fingerprint === policy.fingerprint).map(s => {
          const x = 45 + Number(s.coordinates!.effort.normalized) * 320
          const right = Number(s.coordinates!.effort.normalized) > .5
          return <text key={`l${s.id}`} x={x + (right ? -11 : 11)} y={295 - Number(s.coordinates!.value.normalized) * 270 + 4} textAnchor={right ? 'end' : 'start'} fontSize="11" className="bf-quadrant-name">{titled(s)}</text>
        })}
      </svg></div>
      <p>{zh ? '评分总数' : 'Total ratings'}: {page.total} · {zh ? '当前页' : 'Page'} {Math.floor(offset / 50) + 1}</p>
      <ul>{page.items.map(s => <li key={s.id}><button onClick={() => void select(s)}>{s.opportunity_id} · {s.id} · v{s.version}</button>{(!s.coordinates || s.policy_fingerprint !== policy.fingerprint) && <span> {zh ? '未落点：' : 'Not plotted: '}{s.policy_fingerprint !== policy.fingerprint ? (zh ? '量表已改变' : 'Policy changed') : s.not_plotted_reasons.map(reason => reasons[reason]?.[zh ? 0 : 1] ?? reason).join('; ')}</span>}</li>)}</ul>
      <button disabled={!offset} onClick={() => setOffset(n => Math.max(0, n - 50))}>{zh ? '上一页' : 'Previous'}</button><button disabled={!page.has_more} onClick={() => setOffset(n => n + 50)}>{zh ? '下一页' : 'Next'}</button>
    </>}
    {selected && selected.project_id === project && <section aria-label={zh ? '评分依据' : 'Rating evidence'}><h4>{selected.id} · v{selected.version}</h4><p>{zh ? '评分人' : 'Scorer'}: {selected.actor}</p>{(['effort', 'value'] as const).map(key => <div key={key}><strong>{key}: {selected[key]?.score ?? '—'}</strong><p>{selected[key]?.rationale}</p><ul>{selected[key]?.references.map((r, i) => <li key={i}>{r.material_id} · v{r.version} · {r.locator.sheet} · {r.locator.kind} {r.locator.start}–{r.locator.end}</li>)}</ul></div>)}<button onClick={() => onEdit(selected)}>{zh ? '修订此评分' : 'Revise rating'}</button></section>}
  </section>
}
