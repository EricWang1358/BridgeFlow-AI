import { DecisionEditor, DecisionPanel, type Decision } from './discovery-decisions.tsx'
import { MeetingEditor, MeetingView, meetingDraft, type Meeting } from './discovery-meetings.tsx'
import { ScoreBoard, ScoreEditor, type Score } from './discovery-scoring.tsx'
import { FlowDiagram, FlowEditor, type FlowGraph } from './flow-graph.tsx'
import { OpportunityEditor, type Opportunity } from './opportunity-editor.tsx'
import { useEffect, useState, type FormEvent } from 'react'
import { api, describeError, useUI } from './ui.ts'

type Item = { id: string; version: number; filename?: string; title?: string; parser_status?: string; status?: string }
type Page = { items: Item[]; total: number; has_more: boolean }
type Staged = { upload_id: string; digest: string; material: Record<string, unknown>; expires_at: number }

export function Discovery() {
  const { language, t } = useUI()
  const tr = (zh: string, en: string) => language === 'zh' ? zh : en
  const [projectInput, setProjectInput] = useState(''), [project, setProject] = useState('')
  const [kind, setKind] = useState<'material' | 'opportunity' | 'graph' | 'score' | 'meeting' | 'decision'>('material'), [offset, setOffset] = useState(0)
  const [page, setPage] = useState<Page | null>(null), [revision, setRevision] = useState(0)
  const [error, setError] = useState(''), [busy, setBusy] = useState(false)
  const [staged, setStaged] = useState<Staged | null>(null), [copied, setCopied] = useState(false)
  const [scoringTarget, setScoringTarget] = useState<{ candidate: Opportunity; initial?: Score } | null>(null), [scoreKey, setScoreKey] = useState(0)
  const [decisionEdit, setDecisionEdit] = useState<{ meetingId: string; initial?: Decision } | null>(null), [decisionKey, setDecisionKey] = useState(0)
  const [meeting, setMeeting] = useState<Meeting | null>(null), [meetingKey, setMeetingKey] = useState(0)
  const [graphDraft, setGraphDraft] = useState<FlowGraph | null>(null), [graphKey, setGraphKey] = useState(0)
  const [editing, setEditing] = useState<Opportunity | undefined>(), [editorKey, setEditorKey] = useState(0)
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null)
  useEffect(() => {
    setPage(null); setDetail(null); setError('')
    if (!project || kind === 'score') return
    const abort = new AbortController()
    void api<Page>(`/discovery/${project}/${kind}?offset=${offset}&limit=10`, { signal: abort.signal })
      .then(setPage).catch(e => { if (!abort.signal.aborted) setError(describeError(e, t)) })
    return () => abort.abort()
  }, [project, kind, offset, revision])
  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(''); setCopied(false)
    const form = new FormData(event.currentTarget), file = form.get('file')
    if (!(file instanceof File) || !file.size || file.size > 20 * 1024 * 1024) {
      setError(tr('请选择不超过 20 MiB 的非空文件。', 'Choose a nonempty file up to 20 MiB.')); return
    }
    const metadata = Object.fromEntries(['id', 'department', 'period', 'declared_kind', 'source_description'].map(k => [k, form.get(k)]))
    const body = new FormData()
    body.append('metadata', JSON.stringify({ ...metadata, project_id: project, filename: file.name, expected_seq: Number(form.get('expected_seq')) }))
    body.append('file', file)
    setBusy(true)
    try { setStaged(await api<Staged>('/discovery/uploads', { method: 'POST', body })) }
    catch (e) { setError(describeError(e, t)) } finally { setBusy(false) }
  }
  const request = staged ? `Please call discovery_register with these exact arguments, and wait for native approval:\n${JSON.stringify({ upload_id: staged.upload_id, digest: staged.digest, material: staged.material }, null, 2)}` : ''
  async function download(item: Item) {
    try {
      const file = await api<{ filename: string; base64: string }>(`/discovery/${project}/material/${item.id}/original?version=${item.version}`)
      const url = URL.createObjectURL(new Blob([Uint8Array.from(atob(file.base64), c => c.charCodeAt(0))]))
      const link = document.createElement('a'); link.href = url; link.download = file.filename; link.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (e) { setError(describeError(e, t)) }
  }
  return <section className="bf-state bf-discovery" aria-label={tr('立项材料与候选', 'Discovery materials and opportunities')}>
    <h2>{tr('立项材料与候选', 'Discovery materials and opportunities')}</h2>
    <p>{tr('上传的文件先暂存，在对话里批准后才登记。保存提案之后，立项仍要另行批准。', 'Uploads wait until you approve them in the chat. Saving a proposal leaves the project to be approved separately.')}</p>
    <form onSubmit={e => { e.preventDefault(); setPage(null); setDetail(null); setEditing(undefined); setGraphDraft(null); setScoringTarget(null); setMeeting(null); setDecisionEdit(null); setProject(projectInput); setOffset(0); setStaged(null); setRevision(n => n + 1) }}>
      <label>{tr('项目标识', 'Project ID')}<input required pattern="[a-zA-Z0-9]([a-zA-Z0-9_]|-){0,79}" value={projectInput} onChange={e => setProjectInput(e.target.value)} /></label>
      <button type="submit" disabled={busy}>{tr('打开项目', 'Open project')}</button>
      <button type="button" disabled={busy} onClick={() => {
        setBusy(true); setError('')
        void api<{ project_id: string; id: string; seq: number }>('/discovery/sample', { method: 'POST' }).then(decision => {
          setPage(null); setDetail(null); setEditing(undefined); setGraphDraft(null); setScoringTarget(null); setMeeting(null); setDecisionEdit(null)
          setProjectInput(decision.project_id); setProject(decision.project_id); setKind('decision'); setOffset(0); setStaged(null); setRevision(n => n + 1)
        }).catch(e => setError(describeError(e, t))).finally(() => setBusy(false))
      }}>{tr('载入示例项目', 'Load the sample project')}</button>
    </form>
    <p className="bf-hint">{tr('示例项目从一份部门材料走到一条已批准的立项决策；人名和投票都是示例数据。', 'The sample project goes from one department file to an approved MVP decision. Its people and votes are sample data.')}</p>
    {error && <p role="alert">{error}</p>}
    {project && <>
      <h3>{project}</h3>
      <div><button onClick={() => { setKind('material'); setOffset(0) }}>{tr('材料', 'Materials')}</button><button onClick={() => { setKind('opportunity'); setOffset(0) }}>{tr('候选', 'Opportunities')}</button><button onClick={() => { setKind('graph'); setOffset(0) }}>{tr('流程图', 'Flow graphs')}</button><button onClick={() => { setKind('score'); setOffset(0) }}>{tr('评分四象限', 'Rating quadrants')}</button><button onClick={() => { setKind('meeting'); setOffset(0) }}>{tr('会议', 'Meetings')}</button><button onClick={() => { setKind('decision'); setOffset(0) }}>{tr('决策', 'Decisions')}</button>{kind !== 'score' && <button onClick={() => setRevision(n => n + 1)}>{t('refresh')}</button>}</div>
      <form onSubmit={upload} hidden={kind !== 'material'} style={kind !== 'material' ? { display: 'none' } : undefined}>
        {(['id', 'department', 'period', 'source_description'] as const).map((name, index) => <label key={name}>
          {tr(['材料标识', '部门（准确名称）', '期间', '来源说明'][index]!, ['Material ID', 'Department (exact name)', 'Period', 'Provenance'][index]!)}
          <input name={name} required maxLength={name === 'source_description' ? 1200 : 200} {...(name === 'id' ? { pattern: '[a-zA-Z0-9]([a-zA-Z0-9_]|-){0,79}' } : {})} />
        </label>)}
        <label>{tr('当前版本（新材料填 0）', 'Current version (0 for new material)')}<input name="expected_seq" type="number" min="0" step="1" required defaultValue="0" /></label>
        <label>{tr('声明类型', 'Declared type')}<select name="declared_kind">
          {(['template', 'records', 'narrative', 'meeting', 'rule'] as const).map((k, i) => <option key={k} value={k}>{tr(['空模板', '业务数据', '说明', '会议材料', '规则陈述'][i]!, k)}</option>)}
        </select></label>
        <label>{tr('材料文件', 'Material file')}<input name="file" type="file" required /></label>
        <button type="submit" disabled={busy}>{tr(busy ? '上传中…' : '暂存材料', busy ? 'Uploading…' : 'Stage material')}</button>
      </form>
      {staged && <section aria-label={tr('待审批登记', 'Registration awaiting approval')}>
        <p>{tr('还没登记。把下面的请求粘贴到对话里，核对审批卡后再决定。到期：', 'Not registered yet. Paste this request into the chat, check the approval card, then decide. Expires: ')}{new Date(staged.expires_at * 1000).toLocaleString()}</p>
        <textarea readOnly rows={10} value={request} aria-label={tr('登记审批请求', 'Registration approval request')} />
        <button onClick={() => { void navigator.clipboard.writeText(request).then(() => setCopied(true)).catch(() => setError(tr('复制失败，请手动选中上方文字复制。', 'Copy failed; select the text above and copy it yourself.'))) }}>{tr('复制审批请求', 'Copy approval request')}</button>
        {copied && <p role="status">{tr('已复制，请粘贴到原生对话。', 'Copied. Paste into native chat.')}</p>}
      </section>}
      {kind === 'decision' && decisionEdit && <DecisionEditor key={`${project}:${decisionKey}`} project={project} meetingId={decisionEdit.meetingId} initial={decisionEdit.initial} />}
      {kind === 'meeting' && meeting?.project_id === project && <MeetingEditor key={`${project}:${meetingKey}`} initial={meeting} />}
      {kind === 'opportunity' && <><button onClick={() => { setEditing(undefined); setEditorKey(n => n + 1) }}>{tr('开始新候选', 'Start new opportunity')}</button><OpportunityEditor key={`${project}:${editorKey}`} project={project} initial={editing} /></>}
      {kind === 'graph' && graphDraft?.project_id === project && <FlowEditor key={`${project}:${graphKey}`} initial={graphDraft} />}
      {kind === 'score' && <><ScoreBoard key={project} project={project} onEdit={score => { void api<Opportunity>(`/discovery/${project}/opportunity/${score.opportunity_id}`).then(candidate => { setScoringTarget({ candidate, initial: score }); setScoreKey(n => n + 1) }).catch(e => setError(describeError(e, t))) }} />{scoringTarget?.candidate.project_id === project && <ScoreEditor key={`${project}:${scoreKey}`} project={project} opportunity={scoringTarget.candidate} initial={scoringTarget.initial} />}</>}
      {page && <><p>{tr('总数', 'Total')}: {page.total}</p>{page.items.map(item => <article key={item.id}>
        <strong>{item.title ?? item.filename ?? item.id} · {item.id} · v{item.version}</strong><p>{item.parser_status ?? item.status}</p>
        <button onClick={() => { void api<Record<string, unknown>>(`/discovery/${project}/${kind}/${item.id}?version=${item.version}`).then(setDetail).catch(e => setError(describeError(e, t))) }}>{tr('查看详情与依据', 'View details and evidence')}</button>
        {kind === 'opportunity' && <button onClick={() => { void api<Opportunity>(`/discovery/${project}/opportunity/${item.id}`).then(value => { setEditing(value); setEditorKey(n => n + 1) }).catch(e => setError(describeError(e, t))) }}>{tr('修订此候选', 'Revise this opportunity')}</button>}
        {kind === 'opportunity' && <button onClick={() => { void api<Opportunity>(`/discovery/${project}/opportunity/${item.id}`).then(value => { setGraphDraft({ id: '', project_id: project, opportunity_id: value.id, opportunity_version: value.seq, title: '', departments: value.departments, nodes: [], edges: [] }); setGraphKey(n => n + 1); setKind('graph'); setOffset(0) }).catch(e => setError(describeError(e, t))) }}>{tr('设计流程草图', 'Design flow draft')}</button>}
        {kind === 'graph' && <button onClick={() => { void api<FlowGraph>(`/discovery/${project}/graph/${item.id}`).then(value => { setGraphDraft(value); setGraphKey(n => n + 1) }).catch(e => setError(describeError(e, t))) }}>{tr('修订流程图', 'Revise flow graph')}</button>}
        {kind === 'opportunity' && <button onClick={() => { void api<Opportunity>(`/discovery/${project}/opportunity/${item.id}`).then(candidate => { setScoringTarget({ candidate }); setScoreKey(n => n + 1); setKind('score') }).catch(e => setError(describeError(e, t))) }}>{tr('为候选评分', 'Rate opportunity')}</button>}
        {kind === 'opportunity' && <button onClick={() => { void api<Opportunity>(`/discovery/${project}/opportunity/${item.id}`).then(candidate => { setMeeting(meetingDraft(project, candidate)); setMeetingKey(n => n + 1); setKind('meeting'); setOffset(0) }).catch(e => setError(describeError(e, t))) }}>{tr('准备会议', 'Prepare meeting')}</button>}
        {kind === 'meeting' && <button onClick={() => { void api<Meeting>(`/discovery/${project}/meeting/${item.id}`).then(value => { setMeeting(value); setMeetingKey(n => n + 1) }).catch(e => setError(describeError(e, t))) }}>{tr('修订会议记录', 'Revise meeting record')}</button>}
        {kind === 'meeting' && <button onClick={() => { setDecisionEdit({ meetingId: item.id }); setDecisionKey(n => n + 1); setKind('decision'); setOffset(0) }}>{tr('准备 MVP 决策', 'Prepare MVP decision')}</button>}
        {kind === 'material' && <button onClick={() => void download(item)}>{tr('下载此版本原件', 'Download this original version')}</button>}
      </article>)}<button disabled={!offset} onClick={() => setOffset(n => Math.max(0, n - 10))}>{tr('上一页', 'Previous')}</button><button disabled={!page.has_more} onClick={() => setOffset(n => n + 10)}>{tr('下一页', 'Next')}</button></>}
      {detail && detail.project_id === project && kind === 'graph' && 'nodes' in detail && 'edges' in detail && <FlowDiagram graph={detail as unknown as FlowGraph} />}
      {detail && detail.project_id === project && kind === 'meeting' && 'stages' in detail && 'minutes' in detail && <MeetingView meeting={detail as unknown as Meeting} />}
      {detail && detail.project_id === project && kind === 'decision' && 'proposal_version' in detail && <DecisionPanel key={`${project}:${detail.id}:${detail.seq}`} initial={detail as unknown as Decision} onRevise={value => { setDecisionEdit({ meetingId: value.meeting_id, initial: value }); setDecisionKey(n => n + 1) }} />}
      {detail && detail.project_id === project && kind !== 'meeting' && kind !== 'decision' && <section><h3>{tr('版本详情与来源依据', 'Version details and sources')}</h3><pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{JSON.stringify(detail, null, 2)}</pre></section>}
    </>}
  </section>
}
