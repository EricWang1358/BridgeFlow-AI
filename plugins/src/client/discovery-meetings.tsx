import { useState, type FormEvent } from 'react'
import { Failure } from './failure.tsx'
import { Sources, type Ref } from './flow-graph.tsx'
import { useUI } from './ui.ts'

type Statement = { text: string; basis: 'reported' | 'assumption'; references: Ref[] }
type Stage = { id: string; title: string; owner_role: string; exit_criteria: string[]; depends_on: string[]; rationale: Statement }
export type Meeting = { id: string; project_id: string; title: string; seq?: number; candidates: { id: string; version: number }[];
  scope: Statement[]; exclusions: string[]; risks: Statement[]; resources: Statement[]; stages: Stage[]; discussion_questions: string[];
  phase: 'preparation' | 'minutes'; participants: string[]; minutes: Statement[]; change_reason: string }
const blank = (): Statement => ({ text: '', basis: 'assumption', references: [] })
const lines = (value: string) => value.split('\n')
export function meetingDraft(project: string, candidate: { id: string; seq: number }): Meeting {
  return { id: '', project_id: project, title: '', candidates: [{ id: candidate.id, version: candidate.seq }], scope: [blank()],
    exclusions: [], risks: [], resources: [], stages: [{ id: '', title: '', owner_role: '', exit_criteria: [''], depends_on: [], rationale: blank() }],
    discussion_questions: [], phase: 'preparation', participants: [], minutes: [], change_reason: '' }
}
function Statements({ title, items, onChange }: { title: string; items: Statement[]; onChange: (items: Statement[]) => void }) {
  const { language } = useUI(), zh = language === 'zh'
  function update(i: number, change: Partial<Statement>) { onChange(items.map((s, n) => n === i ? { ...s, ...change } : s)) }
  return <fieldset aria-label={title}><legend>{title}</legend>{items.map((item, i) => <div key={i}>
    <label>{zh ? '陈述' : 'Statement'} {i + 1}<textarea aria-label={`${zh ? '陈述' : 'Statement'} ${i + 1}`} required maxLength={1200} value={item.text} onChange={e => update(i, { text: e.target.value })} /></label>
    <label>{zh ? '依据类型' : 'Basis'}<select aria-label={zh ? '依据类型' : 'Basis'} value={item.basis} onChange={e => update(i, { basis: e.target.value as Statement['basis'] })}><option value="assumption">{zh ? '假设／建议，待确认' : 'Assumption / proposal, unconfirmed'}</option><option value="reported">{zh ? '有来源的报告陈述' : 'Sourced reported statement'}</option></select></label>
    <Sources value={item.references} onChange={references => update(i, { references })} />
    <button type="button" onClick={() => onChange(items.filter((_, n) => n !== i))}>{zh ? '删除陈述' : 'Remove statement'}</button>
  </div>)}<button type="button" disabled={items.length >= (title === '纪要' || title === 'Minutes' ? 30 : 20)} onClick={() => onChange([...items, blank()])}>{zh ? '添加陈述' : 'Add statement'}</button></fieldset>
}
export function MeetingEditor({ initial }: { initial: Meeting }) {
  const { language } = useUI(), zh = language === 'zh'
  const [draft, setDraft] = useState(initial), [request, setRequest] = useState(''), [error, setError] = useState<unknown>(''), [copied, setCopied] = useState(false)
  function update(change: Partial<Meeting>) { setDraft(value => ({ ...value, ...change })); setRequest(''); setCopied(false); setError('') }
  const cleanLines = (items: string[]) => items.map(s => s.trim()).filter(Boolean)
  function prepare(e: FormEvent) {
    e.preventDefault()
    const statements = [...draft.scope, ...draft.risks, ...draft.resources, ...draft.minutes, ...draft.stages.map(s => s.rationale)]
    if (!draft.scope.length || !draft.stages.length || statements.some(s => !s.text.trim() || s.basis === 'reported' && !s.references.length)) {
      setError(zh ? '请填写范围、阶段和陈述；报告型陈述须添加来源。' : 'Provide scope, stages and statements; reported statements require sources.'); return
    }
    if (draft.phase === 'minutes' && (!cleanLines(draft.participants).length || !draft.minutes.length)) {
      setError(zh ? '会后纪要须填写参会者和纪要。' : 'Minutes require reported participants and notes.'); return
    }
    const { seq: _seq, ...value } = draft
    const meeting = { ...value, expected_seq: initial.seq ?? 0, exclusions: cleanLines(draft.exclusions),
      discussion_questions: cleanLines(draft.discussion_questions), participants: cleanLines(draft.participants),
      stages: draft.stages.map(s => ({ ...s, exit_criteria: cleanLines(s.exit_criteria), depends_on: cleanLines(s.depends_on) })) }
    // The read DTO may contain snapshots/audit projections; never echo those as writes.
    const keys = ['id', 'project_id', 'title', 'candidates', 'scope', 'exclusions', 'risks', 'resources', 'stages', 'discussion_questions', 'phase', 'participants', 'minutes', 'change_reason', 'expected_seq']
    const body = Object.fromEntries(keys.map(k => [k, meeting[k as keyof typeof meeting]]))
    setRequest(`Please call discovery_meeting_save with these exact arguments, and wait for native approval:\n${JSON.stringify({ meeting: body }, (_key, v) => v === null ? undefined : v, 2)}`)
    setError(''); setCopied(false)
  }
  return <section aria-label={zh ? '会议记录编辑' : 'Meeting record editor'}><h3>{zh ? '会议准备与纪要' : 'Meeting preparation and minutes'}</h3>
    <p>{zh ? '估算和建议标为假设。参会姓名是记录信息，不等于投票或立项批准。未批准编辑仅保留在当前页面。' : 'Label estimates and proposals as assumptions. Reported attendance is not a vote or project approval. Unsaved edits live only on this page.'}</p>
    <Failure value={error}/><form onSubmit={prepare} onChange={() => { setRequest(''); setCopied(false) }}>
      <label>{zh ? '会议标识' : 'Meeting ID'}<input required readOnly={!!initial.seq} pattern="[a-zA-Z0-9]([a-zA-Z0-9_]|-){0,79}" value={draft.id} onChange={e => update({ id: e.target.value })} /></label>
      <label>{zh ? '会议标题' : 'Meeting title'}<input required maxLength={200} value={draft.title} onChange={e => update({ title: e.target.value })} /></label>
      <fieldset><legend>{zh ? '候选版本' : 'Candidate versions'}</legend>{draft.candidates.map((c, i) => <div key={i}>
        <label>{zh ? '候选标识' : 'Candidate ID'}<input required pattern="[a-zA-Z0-9]([a-zA-Z0-9_]|-){0,79}" value={c.id} onChange={e => update({ candidates: draft.candidates.map((v, n) => n === i ? { ...v, id: e.target.value } : v) })} /></label>
        <label>{zh ? '候选版本号' : 'Candidate version'}<input required type="number" min="1" step="1" value={c.version} onChange={e => update({ candidates: draft.candidates.map((v, n) => n === i ? { ...v, version: Number(e.target.value) } : v) })} /></label>
        <button type="button" disabled={draft.candidates.length === 1} onClick={() => update({ candidates: draft.candidates.filter((_, n) => n !== i) })}>{zh ? '删除候选' : 'Remove candidate'}</button>
      </div>)}<button type="button" disabled={draft.candidates.length >= 10} onClick={() => update({ candidates: [...draft.candidates, { id: '', version: 1 }] })}>{zh ? '添加候选' : 'Add candidate'}</button></fieldset>
      {(['scope', 'risks', 'resources'] as const).map((key, i) => <Statements key={key} title={(zh ? ['范围', '风险', '资源依赖'] : ['Scope', 'Risks', 'Resources'])[i]!} items={draft[key]} onChange={items => update({ [key]: items })} />)}
      <fieldset aria-label={zh ? '实施阶段' : 'Implementation stages'}><legend>{zh ? '实施阶段' : 'Implementation stages'}</legend>{draft.stages.map((stage, i) => {
        const change = (value: Partial<Stage>) => update({ stages: draft.stages.map((s, n) => n === i ? { ...s, ...value } : s) })
        return <fieldset key={i}><legend>{i + 1}</legend>{(['id', 'title', 'owner_role'] as const).map((key, n) => <label key={key}>{(zh ? ['阶段标识', '阶段标题', '责任角色'] : ['Stage ID', 'Stage title', 'Owner role'])[n]}<input required maxLength={200} value={stage[key]} onChange={e => change({ [key]: e.target.value })} /></label>)}
          <label>{zh ? '退出条件（每行一项）' : 'Exit criteria (one per line)'}<textarea aria-label={zh ? '退出条件（每行一项）' : 'Exit criteria (one per line)'} required value={stage.exit_criteria.join('\n')} onChange={e => change({ exit_criteria: lines(e.target.value) })} /></label>
          <label>{zh ? '前置阶段标识（每行一项）' : 'Prerequisite stage IDs (one per line)'}<textarea aria-label={zh ? '前置阶段标识（每行一项）' : 'Prerequisite stage IDs (one per line)'} value={stage.depends_on.join('\n')} onChange={e => change({ depends_on: lines(e.target.value) })} /></label>
          <label>{zh ? '阶段理由（假设／建议）' : 'Stage rationale (assumption / proposal)'}<textarea aria-label={zh ? '阶段理由（假设／建议）' : 'Stage rationale (assumption / proposal)'} required maxLength={1200} value={stage.rationale.text} onChange={e => change({ rationale: { ...stage.rationale, text: e.target.value } })} /></label>
          <label>{zh ? '阶段理由类型' : 'Stage rationale basis'}<select aria-label={zh ? '阶段理由类型' : 'Stage rationale basis'} value={stage.rationale.basis} onChange={e => change({ rationale: { ...stage.rationale, basis: e.target.value as Statement['basis'] } })}><option value="assumption">{zh ? '假设' : 'Assumption'}</option><option value="reported">{zh ? '报告陈述' : 'Reported'}</option></select></label>
          <Sources value={stage.rationale.references} onChange={references => change({ rationale: { ...stage.rationale, references } })} />
          <button type="button" disabled={draft.stages.length === 1} onClick={() => update({ stages: draft.stages.filter((_, n) => n !== i) })}>{zh ? '删除阶段' : 'Remove stage'}</button>
        </fieldset>
      })}<button type="button" disabled={draft.stages.length >= 10} onClick={() => update({ stages: [...draft.stages, { id: '', title: '', owner_role: '', exit_criteria: [''], depends_on: [], rationale: blank() }] })}>{zh ? '添加阶段' : 'Add stage'}</button></fieldset>
      {(['exclusions', 'discussion_questions', 'participants'] as const).map((key, i) => <label key={key}>{(zh ? ['排除范围（每行一项）', '讨论问题（每行一项）', '参会者记录（每行一人）'] : ['Exclusions (one per line)', 'Discussion questions (one per line)', 'Reported attendees (one per line)'])[i]}<textarea aria-label={(zh ? ['排除范围（每行一项）', '讨论问题（每行一项）', '参会者记录（每行一人）'] : ['Exclusions (one per line)', 'Discussion questions (one per line)', 'Reported attendees (one per line)'])[i]} value={draft[key].join('\n')} onChange={e => update({ [key]: lines(e.target.value) })} /></label>)}
      <label>{zh ? '记录阶段' : 'Record phase'}<select aria-label={zh ? '记录阶段' : 'Record phase'} value={draft.phase} onChange={e => update({ phase: e.target.value as Meeting['phase'], minutes: e.target.value === 'preparation' ? [] : draft.minutes })}><option value="preparation" disabled={initial.phase === 'minutes'}>{zh ? '会前准备' : 'Preparation'}</option><option value="minutes">{zh ? '会后纪要' : 'Minutes'}</option></select></label>
      {draft.phase === 'minutes' && <Statements title={zh ? '纪要' : 'Minutes'} items={draft.minutes} onChange={minutes => update({ minutes })} />}
      <label>{zh ? '本次记录／修订原因' : 'Reason for this record / revision'}<textarea aria-label={zh ? '本次记录／修订原因' : 'Reason for this record / revision'} required maxLength={1200} value={draft.change_reason} onChange={e => update({ change_reason: e.target.value })} /></label>
      <button type="submit">{zh ? '准备会议审批请求' : 'Prepare meeting approval'}</button>
    </form>{request && <><p>{zh ? '尚未保存。粘贴到原生对话并审查批准。' : 'Not saved. Paste into native chat and review approval.'}</p><textarea readOnly rows={10} aria-label={zh ? '会议审批请求' : 'Meeting approval request'} value={request} /><button onClick={() => { void navigator.clipboard.writeText(request).then(() => setCopied(true)).catch(() => setError(zh ? '复制失败，请手动选择。' : 'Copy failed; select manually.')) }}>{zh ? '复制会议请求' : 'Copy meeting request'}</button>{copied && <p role="status">{zh ? '已复制。' : 'Copied.'}</p>}</>}
  </section>
}

export function MeetingView({ meeting }: { meeting: Meeting & { actor?: string; version?: number; status?: string; stale_candidates?: string[]; stale_sources?: string[]; candidate_snapshots?: { id: string; version: number; title: string }[] } }) {
  const { language } = useUI(), zh = language === 'zh'
  const renderStatements = (items: Statement[]) => <ul>{items.map((item, i) => <li key={i}><strong>{item.basis === 'assumption' ? (zh ? '假设／建议' : 'Assumption / proposal') : (zh ? '报告陈述' : 'Reported')}</strong>: {item.text}<ul>{item.references.map((ref, n) => <li key={n}>{ref.material_id} · v{ref.version} · {ref.locator.sheet} · {ref.locator.kind} {ref.locator.start}–{ref.locator.end}</li>)}</ul></li>)}</ul>
  return <section aria-label={zh ? '会议记录详情' : 'Meeting record details'}><h3>{meeting.title} · v{meeting.version}</h3>
    <p>{meeting.phase === 'minutes' ? (zh ? '会后纪要' : 'Minutes') : (zh ? '会前准备' : 'Preparation')} · {zh ? '记录人' : 'Recorder'}: {meeting.actor}</p>
    <p>{zh ? '本记录不代表立项批准；参会姓名为报告信息。' : 'This record does not approve a project; attendee names are reported information.'}</p>
    {meeting.status === 'needs_review' && <p role="alert">{zh ? '输入已变化，需重新审查。候选：' : 'Inputs changed; review required. Candidates: '}{meeting.stale_candidates?.join(', ')} · {zh ? '材料：' : 'Materials: '}{meeting.stale_sources?.join(', ')}</p>}
    <h4>{zh ? '冻结候选版本' : 'Frozen candidate versions'}</h4><ul>{meeting.candidate_snapshots?.map(c => <li key={c.id}>{c.title} · {c.id} · v{c.version}</li>)}</ul>
    {(['scope', 'risks', 'resources'] as const).map((key, i) => <div key={key}><h4>{(zh ? ['范围', '风险', '资源依赖'] : ['Scope', 'Risks', 'Resources'])[i]}</h4>{renderStatements(meeting[key])}</div>)}
    <h4>{zh ? '实施阶段' : 'Implementation stages'}</h4>{meeting.stages.map(s => <article key={s.id}><strong>{s.title} · {s.id}</strong><p>{zh ? '责任角色' : 'Owner role'}: {s.owner_role}</p><p>{zh ? '前置阶段' : 'Prerequisites'}: {s.depends_on.join(', ') || '—'}</p><p>{zh ? '退出条件' : 'Exit criteria'}</p><ul>{s.exit_criteria.map((c, i) => <li key={i}>{c}</li>)}</ul>{renderStatements([s.rationale])}</article>)}
    {(['exclusions', 'discussion_questions', 'participants'] as const).map((key, i) => <div key={key}><h4>{(zh ? ['排除范围', '讨论问题', '报告的参会者'] : ['Exclusions', 'Discussion questions', 'Reported attendees'])[i]}</h4><ul>{meeting[key].map((item, n) => <li key={n}>{item}</li>)}</ul></div>)}
    {meeting.phase === 'minutes' && <><h4>{zh ? '纪要' : 'Minutes'}</h4>{renderStatements(meeting.minutes)}</>}
    <p>{zh ? '记录／修订原因' : 'Record / revision reason'}: {meeting.change_reason}</p>
  </section>
}
