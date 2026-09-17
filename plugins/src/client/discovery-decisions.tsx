import { useEffect, useState } from 'react'
import { api, describeError, useUI } from './ui.ts'
import { Sources, type Ref } from './flow-graph.tsx'
import type { Meeting } from './discovery-meetings.tsx'

type Condition = { id: string; description: string; confirmer: string }
type Policy = { id: string; version: number; fingerprint: string; declared_by: string; declaration_ref: string;
  proposers: string[]; voters: string[]; approvers: string[]; condition_confirmers: string[]; quorum: number; minimum_yes: number;
  no_votes_block: boolean; abstentions_count_for_quorum: boolean; agent2_owner_role: string; viewer: { subject: string; actions: string[] } }
export type Decision = { id: string; project_id: string; seq: number; proposal_version: number; meeting_id: string; meeting_version: number;
  selected_candidates: string[]; scope: string[]; exclusions: string[]; rationale: string; conditions: Condition[]; policy_fingerprint: string;
  status: string; recorded_status: string; stale_reasons: string[]; pending_conditions: string[];
  votes: Record<string, { actor: string; choice: string; rationale: string }>; resolutions: Record<string, { actor: string; rationale: string; references: Ref[] }>;
  tally: { yes: number; no: number; abstain: number; participation: number; passes: boolean }; finalization: { actor: string; rationale: string; outcome: string; status: string } | null;
  agent2_handoff: { decision_seq: number; owner_role: string; candidates: { id: string; version: number }[]; scope: string[]; exclusions: string[] } | null }
const splitLines = (v: string) => v.split('\n').map(s => s.trim()).filter(Boolean)
function usePolicy(project: string, revision = 0) {
  const { t } = useUI()
  const [policy, setPolicy] = useState<Policy | null>(null), [error, setError] = useState('')
  useEffect(() => { const abort = new AbortController(); setPolicy(null); setError('')
    void api<Policy>(`/discovery/${project}/decision-policy`, { signal: abort.signal }).then(setPolicy).catch(e => { if (!abort.signal.aborted) setError(describeError(e, t)) })
    return () => abort.abort()
  }, [project, revision])
  return { policy, error }
}
function PolicyView({ policy }: { policy: Policy }) {
  const { language } = useUI(), zh = language === 'zh'
  return <section aria-label={zh ? '决策规则' : 'Decision rules'}><h4>{policy.id} · v{policy.version}</h4><p>{policy.declared_by} · {policy.declaration_ref}</p>
    <p>{zh ? '当前身份' : 'Current identity'}: {policy.viewer.subject}</p>
    <p>{zh ? '法定人数 / 最低赞成票' : 'Quorum / minimum yes'}: {policy.quorum} / {policy.minimum_yes}</p>
    <p>{policy.no_votes_block ? (zh ? '反对票阻止批准' : 'No votes block approval') : (zh ? '反对票不单独阻止批准' : 'No votes do not independently veto')}; {policy.abstentions_count_for_quorum ? (zh ? '弃权计入法定人数' : 'Abstentions count for quorum') : (zh ? '弃权不计入法定人数' : 'Abstentions do not count for quorum')}</p>
    <p>{zh ? '投票人' : 'Voters'}: {policy.voters.join(', ')}</p><p>{zh ? '决定人' : 'Decision owners'}: {policy.approvers.join(', ')}</p>
    <p>{zh ? 'Agent 2 接收角色' : 'Agent 2 owner role'}: {policy.agent2_owner_role}</p>
  </section>
}
function RequestView({ request }: { request: string }) {
  const { language } = useUI(), zh = language === 'zh'
  const [message, setMessage] = useState('')
  return <section aria-label={zh ? '决策操作请求' : 'Decision action request'}><p>{zh ? '尚未执行。复制到原生对话，核对身份与内容后审批。' : 'Not executed. Copy into native chat, verify identity and content, then review approval.'}</p>
    <textarea readOnly rows={10} aria-label={zh ? '决策审批请求' : 'Decision approval request'} value={request} />
    <button onClick={() => { void navigator.clipboard.writeText(request).then(() => setMessage(zh ? '已复制。' : 'Copied.')).catch(() => setMessage(zh ? '复制失败，请手动选择。' : 'Copy failed; select manually.')) }}>{zh ? '复制决策请求' : 'Copy decision request'}</button>{message && <p role="status">{message}</p>}
  </section>
}
function instruction(tool: string, body: unknown) {
  return `Please call ${tool} with these exact arguments, and wait for native approval:\n${JSON.stringify(body, (_key, value) => value === null ? undefined : value, 2)}`
}
export function DecisionEditor({ project, meetingId, initial }: { project: string; meetingId: string; initial?: Decision | undefined }) {
  const { language, t } = useUI(), zh = language === 'zh'
  const [revision, setRevision] = useState(0), { policy, error: policyError } = usePolicy(project, revision)
  const [meeting, setMeeting] = useState<Meeting | null>(null), [error, setError] = useState(''), [request, setRequest] = useState('')
  const [id, setId] = useState(initial?.id ?? ''), [selected, setSelected] = useState(initial?.selected_candidates ?? [])
  const [scope, setScope] = useState(initial?.scope.join('\n') ?? ''), [exclusions, setExclusions] = useState(initial?.exclusions.join('\n') ?? '')
  const [rationale, setRationale] = useState(''), [conditions, setConditions] = useState<Condition[]>(initial?.conditions ?? [])
  useEffect(() => { const abort = new AbortController(); setMeeting(null); setRequest(''); setError('')
    void api<Meeting>(`/discovery/${project}/meeting/${meetingId}`, { signal: abort.signal }).then(setMeeting).catch(e => { if (!abort.signal.aborted) setError(describeError(e, t)) })
    return () => abort.abort()
  }, [project, meetingId, revision])
  const canPropose = policy?.viewer.actions.includes('discovery_decision_propose')
  return <section aria-label={zh ? '决策提案编辑' : 'Decision proposal editor'}><h3>{zh ? '决策提案' : 'Decision proposal'}</h3>
    <button onClick={() => { setRequest(''); setRevision(n => n + 1) }}>{zh ? '重读纪要与规则' : 'Reload minutes and rules'}</button>
    {(error || policyError) && <p role="alert">{error || policyError}</p>}{policy && <PolicyView policy={policy} />}
    {meeting && policy && <><p>{meeting.title} · v{meeting.seq}</p>{initial && <p role="alert">{zh ? '修订将清空已有选票和条件确认，旧批准不再有效。' : 'Revision clears votes and confirmations and supersedes the old approval.'}</p>}
      {meeting.phase !== 'minutes' ? <p role="alert">{zh ? '请先保存会后纪要，再准备决策。' : 'Save meeting minutes before proposing a decision.'}</p> : <form onChange={() => setRequest('')} onSubmit={e => {
        e.preventDefault()
        if (!selected.length || !splitLines(scope).length || selected.some(c => !meeting.candidates.some(v => v.id === c))) { setError(zh ? '请选择当前纪要中的候选并填写批准范围。' : 'Select candidates from these minutes and specify approved scope.'); return }
        setRequest(instruction('discovery_decision_propose', { proposal: { id, project_id: project, meeting_id: meeting.id, meeting_version: meeting.seq,
          selected_candidates: selected, scope: splitLines(scope), exclusions: splitLines(exclusions), rationale, conditions,
          policy_fingerprint: policy.fingerprint, expected_seq: initial?.seq ?? 0 } })); setError('')
      }}>
        <label>{zh ? '决策标识' : 'Decision ID'}<input required readOnly={!!initial} pattern="[a-zA-Z0-9]([a-zA-Z0-9_]|-){0,79}" value={id} onChange={e => setId(e.target.value)} /></label>
        <fieldset><legend>{zh ? '选中候选' : 'Selected candidates'}</legend>{meeting.candidates.map(c => <label key={c.id}><input type="checkbox" checked={selected.includes(c.id)} onChange={e => setSelected(values => e.target.checked ? [...values, c.id] : values.filter(v => v !== c.id))} />{c.id} · v{c.version}</label>)}</fieldset>
        <label>{zh ? '批准范围（每行一项）' : 'Approval scope (one per line)'}<textarea aria-label={zh ? '批准范围（每行一项）' : 'Approval scope (one per line)'} required value={scope} onChange={e => setScope(e.target.value)} /></label>
        <label>{zh ? '排除范围（每行一项）' : 'Exclusions (one per line)'}<textarea aria-label={zh ? '排除范围（每行一项）' : 'Exclusions (one per line)'} value={exclusions} onChange={e => setExclusions(e.target.value)} /></label>
        <label>{zh ? '提案或修订理由' : 'Proposal or revision rationale'}<textarea aria-label={zh ? '提案或修订理由' : 'Proposal or revision rationale'} required maxLength={1200} value={rationale} onChange={e => setRationale(e.target.value)} /></label>
        <fieldset aria-label={zh ? '批准条件' : 'Approval conditions'}><legend>{zh ? '批准条件' : 'Approval conditions'}</legend>{conditions.map((c, i) => <div key={i}>
          <label>{zh ? '条件标识' : 'Condition ID'}<input required pattern="[a-zA-Z0-9]([a-zA-Z0-9_]|-){0,79}" value={c.id} onChange={e => setConditions(values => values.map((v, n) => n === i ? { ...v, id: e.target.value } : v))} /></label>
          <label>{zh ? '条件说明' : 'Condition description'}<textarea aria-label={zh ? '条件说明' : 'Condition description'} required maxLength={1200} value={c.description} onChange={e => setConditions(values => values.map((v, n) => n === i ? { ...v, description: e.target.value } : v))} /></label>
          <label>{zh ? '指定确认人' : 'Assigned confirmer'}<select aria-label={zh ? '指定确认人' : 'Assigned confirmer'} required value={c.confirmer} onChange={e => setConditions(values => values.map((v, n) => n === i ? { ...v, confirmer: e.target.value } : v))}><option value="">—</option>{policy.condition_confirmers.map(subject => <option key={subject} value={subject}>{subject}</option>)}</select></label>
          <button type="button" onClick={() => { setConditions(values => values.filter((_, n) => n !== i)); setRequest('') }}>{zh ? '删除条件' : 'Remove condition'}</button>
        </div>)}<button type="button" disabled={conditions.length >= 20} onClick={() => { setConditions(values => [...values, { id: '', description: '', confirmer: '' }]); setRequest('') }}>{zh ? '添加条件' : 'Add condition'}</button></fieldset>
        {!canPropose && <p>{zh ? '当前身份没有提案权限。' : 'Current identity cannot propose.'}</p>}<button disabled={!canPropose} type="submit">{zh ? '准备决策提案请求' : 'Prepare decision proposal request'}</button>
      </form>}</>}{request && <RequestView key={request} request={request} />}
  </section>
}
const statusText: Record<string, [string, string]> = { proposed: ['待决定', 'Proposed'], conditional: ['条件式决定，尚未批准交付', 'Conditional; not released'], approved: ['已批准范围', 'Approved scope'], rejected: ['已拒绝', 'Rejected'], needs_review: ['输入已变化，需重审', 'Inputs changed; review required'] }
export function DecisionPanel({ initial, onRevise }: { initial: Decision; onRevise: (decision: Decision) => void }) {
  const { language, t } = useUI(), zh = language === 'zh'
  const [decision, setDecision] = useState(initial), [revision, setRevision] = useState(0)
  const { policy, error: policyError } = usePolicy(initial.project_id, revision)
  const [error, setError] = useState(''), [request, setRequest] = useState(''), [reason, setReason] = useState('')
  const [choice, setChoice] = useState(''), [condition, setCondition] = useState(''), [refs, setRefs] = useState<Ref[]>([])
  useEffect(() => { if (!revision) return; const abort = new AbortController(); setRequest(''); setError('')
    void api<Decision>(`/discovery/${initial.project_id}/decision/${initial.id}`, { signal: abort.signal }).then(setDecision).catch(e => { if (!abort.signal.aborted) setError(describeError(e, t)) })
    return () => abort.abort()
  }, [revision, initial.project_id, initial.id])
  const current = !!policy && decision.policy_fingerprint === policy.fingerprint && decision.status !== 'needs_review'
  const can = (action: string) => current && policy!.viewer.actions.includes(`discovery_decision_${action}`)
  function prepare(action: string, extra: Record<string, unknown>) {
    if (!reason.trim()) { setError(zh ? '请填写本次操作理由。' : 'Provide a rationale for this action.'); return }
    setRequest(instruction(`discovery_decision_${action}`, { project_id: decision.project_id, id: decision.id, expected_seq: decision.seq, proposal_version: decision.proposal_version, rationale: reason, ...extra })); setError('')
  }
  return <section aria-label={zh ? '决策详情与操作' : 'Decision details and actions'}><h3>{decision.id} · v{decision.seq}</h3>
    <button onClick={() => setRevision(n => n + 1)}>{zh ? '刷新决策与身份' : 'Refresh decision and identity'}</button>
    {(error || policyError) && <p role="alert">{error || policyError}</p>}{policy && <PolicyView policy={policy} />}
    <p role="status">{statusText[decision.status]?.[zh ? 0 : 1] ?? decision.status}</p>
    {!!decision.stale_reasons.length && <p role="alert">{zh ? '过期原因' : 'Stale reasons'}: {decision.stale_reasons.join(', ')}</p>}
    <p>{zh ? '提案版本 / 纪要版本' : 'Proposal / minutes version'}: {decision.proposal_version} / {decision.meeting_id} v{decision.meeting_version}</p>
    <p>{zh ? '理由' : 'Rationale'}: {decision.rationale}</p><h4>{zh ? '批准范围' : 'Approval scope'}</h4><ul>{decision.scope.map((s, i) => <li key={i}>{s}</li>)}</ul><h4>{zh ? '排除范围' : 'Exclusions'}</h4><ul>{decision.exclusions.map((s, i) => <li key={i}>{s}</li>)}</ul>
    <p>{zh ? '赞成 / 反对 / 弃权' : 'Yes / no / abstain'}: {decision.tally.yes} / {decision.tally.no} / {decision.tally.abstain}</p>
    <p>{decision.tally.passes ? (zh ? '票数达标，仍须明确决定。' : 'Tally passes; an explicit decision is still required.') : (zh ? '票数尚未满足声明规则。' : 'Tally does not meet declared rules.')}</p>
    <ul>{Object.values(decision.votes).map(v => <li key={v.actor}>{v.actor} · {v.choice} · {v.rationale}</li>)}</ul>
    <h4>{zh ? '条件与确认' : 'Conditions and confirmations'}</h4><ul>{decision.conditions.map(c => <li key={c.id}>{c.id}: {c.description} · {c.confirmer} · {decision.resolutions[c.id] ? (zh ? '已确认' : 'Confirmed') : (zh ? '未确认' : 'Unconfirmed')}{decision.resolutions[c.id] && <><p>{decision.resolutions[c.id]!.rationale}</p><ul>{decision.resolutions[c.id]!.references.map((r, i) => <li key={i}>{r.material_id} · v{r.version} · {r.locator.kind} · {r.locator.sheet} {r.locator.start}–{r.locator.end}</li>)}</ul></>}</li>)}</ul>
    {decision.finalization && <p>{zh ? '决定记录' : 'Recorded decision'}: {decision.finalization.actor} · {decision.finalization.outcome} · {decision.finalization.rationale}</p>}
    {decision.agent2_handoff && current ? <section aria-label={zh ? 'Agent 2 批准范围' : 'Agent 2 approved scope'}><h4>{zh ? '当前有效批准范围' : 'Current approved scope'}</h4><p>{decision.agent2_handoff.owner_role} · {zh ? '决定序号' : 'Decision sequence'} {decision.agent2_handoff.decision_seq}</p><ul>{decision.agent2_handoff.candidates.map(c => <li key={c.id}>{c.id} · v{c.version}</li>)}</ul><p>{zh ? '消费端尚未接入；此处不是执行回执。' : 'Consumer integration is pending; this is not an execution receipt.'}</p></section> : <p>{zh ? '当前没有可交付 Agent 2 的批准范围。' : 'No currently approved scope is available for Agent 2.'}</p>}
    <button disabled={!policy?.viewer.actions.includes('discovery_decision_propose')} onClick={() => onRevise(decision)}>{zh ? '修订决策提案' : 'Revise decision proposal'}</button>
    <div onChange={() => setRequest('')}><label>{zh ? '本次操作理由' : 'Action rationale'}<textarea aria-label={zh ? '本次操作理由' : 'Action rationale'} maxLength={1200} value={reason} onChange={e => setReason(e.target.value)} /></label>
      {decision.status === 'proposed' && can('vote') && <><label>{zh ? '本人投票' : 'Own vote'}<select aria-label={zh ? '本人投票' : 'Own vote'} value={choice} onChange={e => setChoice(e.target.value)}><option value="">—</option><option value="yes">{zh ? '赞成' : 'Yes'}</option><option value="no">{zh ? '反对' : 'No'}</option><option value="abstain">{zh ? '弃权' : 'Abstain'}</option></select></label><button disabled={!choice} onClick={() => prepare('vote', { choice })}>{zh ? '准备本人投票请求' : 'Prepare own vote request'}</button></>}
      {['proposed', 'conditional'].includes(decision.status) && can('resolve') && <fieldset><legend>{zh ? '确认本人负责的条件' : 'Confirm assigned condition'}</legend><select aria-label={zh ? '待确认条件' : 'Condition to confirm'} value={condition} onChange={e => setCondition(e.target.value)}><option value="">—</option>{decision.conditions.filter(c => c.confirmer === policy!.viewer.subject && !decision.resolutions[c.id]).map(c => <option key={c.id} value={c.id}>{c.id}: {c.description}</option>)}</select><Sources value={refs} onChange={value => { setRefs(value); setRequest('') }} /><button disabled={!condition || !refs.length} onClick={() => prepare('resolve', { condition_id: condition, references: refs })}>{zh ? '准备条件确认请求' : 'Prepare condition confirmation'}</button></fieldset>}
      {['proposed', 'conditional'].includes(decision.status) && can('finalize') && <><button disabled={!decision.tally.passes} onClick={() => prepare('finalize', { outcome: 'approve' })}>{zh ? '准备批准决定请求' : 'Prepare approval decision'}</button><button onClick={() => prepare('finalize', { outcome: 'reject' })}>{zh ? '准备拒绝决定请求' : 'Prepare rejection decision'}</button></>}
    </div>{request && <RequestView key={request} request={request} />}
  </section>
}
