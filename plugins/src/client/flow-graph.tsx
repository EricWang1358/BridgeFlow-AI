import { useEffect, useId, useState, type FormEvent } from 'react'
import { useUI } from './ui.ts'

export type Ref = { material_id: string; version: number; locator: { kind: 'header' | 'rows' | 'lines'; sheet?: string | null; start?: number | null; end?: number | null } }
type Node = { id: string; title: string; department: string; role: string; trigger: string; inputs: string[]; outputs: string[]; references: Ref[] }
type Edge = { id: string; source: string; target: string; kind: 'information' | 'document'; status: 'confirmed' | 'inferred' | 'missing' | 'conflict'; rationale: string; condition?: string | null; rework: boolean; references: Ref[]; confirmation?: string | null }
export type FlowGraph = { id: string; project_id: string; opportunity_id: string; opportunity_version: number; title: string; departments: string[]; nodes: Node[]; edges: Edge[]; seq?: number; stale_sources?: string[]; opportunity_stale?: boolean }
const ref = (): Ref => ({ material_id: '', version: 1, locator: { kind: 'header', sheet: '' } })
const lines = (text: string) => text.split('\n').map(v => v.trim()).filter(Boolean)
const colors = { confirmed: '#167447', inferred: '#335fba', missing: '#6b7280', conflict: '#bd3333' }

export function Sources({ value, onChange }: { value: Ref[]; onChange: (value: Ref[]) => void }) {
  const { language } = useUI(), zh = language === 'zh'
  function change(index: number, patch: Partial<Ref>) { onChange(value.map((v, i) => i === index ? { ...v, ...patch } : v)) }
  return <fieldset><legend>{zh ? '来源依据' : 'Source evidence'}</legend>{value.map((r, index) => <fieldset key={index}><legend>{index + 1}</legend>
    <label>{zh ? '材料标识' : 'Material ID'}<input required pattern="[a-zA-Z0-9]([a-zA-Z0-9_]|-){0,79}" value={r.material_id} onChange={e => change(index, { material_id: e.target.value })} /></label>
    <label>{zh ? '材料版本' : 'Material version'}<input required type="number" min={1} step={1} value={r.version} onChange={e => change(index, { version: Number(e.target.value) })} /></label>
    <label>{zh ? '位置类型' : 'Location type'}<select value={r.locator.kind} onChange={e => change(index, { locator: { kind: e.target.value as Ref['locator']['kind'], sheet: '', start: 1, end: 1 } })}><option value="header">{zh ? '表头' : 'Header'}</option><option value="rows">{zh ? '表格行' : 'Sheet rows'}</option><option value="lines">{zh ? '文本行' : 'Text lines'}</option></select></label>
    {r.locator.kind !== 'lines' && <label>{zh ? '工作表' : 'Sheet'}<input required maxLength={200} value={r.locator.sheet ?? ''} onChange={e => change(index, { locator: { ...r.locator, sheet: e.target.value } })} /></label>}
    {r.locator.kind !== 'header' && (['start', 'end'] as const).map(key => <label key={key}>{key}<input required type="number" min={1} step={1} value={r.locator[key] ?? 1} onChange={e => change(index, { locator: { ...r.locator, [key]: Number(e.target.value) } })} /></label>)}
    <button type="button" onClick={() => onChange(value.filter((_, i) => i !== index))}>{zh ? '移除此依据' : 'Remove reference'}</button>
  </fieldset>)}<button type="button" disabled={value.length >= 10} onClick={() => onChange([...value, ref()])}>{zh ? '添加依据' : 'Add evidence'}</button></fieldset>
}

export function FlowDiagram({ graph }: { graph: FlowGraph }) {
  const marker = useId().replace(/:/g, ''), { language } = useUI(), zh = language === 'zh'
  const [selected, setSelected] = useState<Node | Edge | null>(null)
  useEffect(() => setSelected(null), [graph])
  const positions = new Map(graph.nodes.map((node, i) => [node.id, { x: 130 + i % 3 * 270, y: 70 + Math.floor(i / 3) * 180 }]))
  return <section aria-label={zh ? '流程草图' : 'Flow diagram'}>
    <p>{zh ? '布局不表示先后顺序；以箭头和条件为准。点击节点或关系查看依据。' : 'Layout does not imply sequence; use arrows and conditions. Select nodes or edges for evidence.'}</p>
    {(graph.opportunity_stale || graph.stale_sources?.length) ? <p role="alert">{zh ? '候选或来源已修订，须重新核对。' : 'Candidate or sources changed; review again.'} {graph.stale_sources?.join(', ')}</p> : null}
    <div style={{ overflow: 'auto' }}><svg role="img" aria-label={zh ? '信息流与文件流' : 'Information and document flow'} viewBox={`0 0 830 ${Math.max(200, Math.ceil(graph.nodes.length / 3) * 180)}`} style={{ minWidth: 650, width: '100%' }}>
      <defs><marker id={marker} markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="currentColor" /></marker></defs>
      {graph.edges.map((edge, i) => {
        const a = positions.get(edge.source), b = positions.get(edge.target); if (!a || !b) return null
        const lift = edge.rework ? -65 : 65 + i % 3 * 12
        return <g key={edge.id} style={{ color: colors[edge.status] }}><path d={`M ${a.x} ${a.y + 28} C ${a.x + 80} ${a.y + lift}, ${b.x - 80} ${b.y + lift}, ${b.x} ${b.y + 28}`} stroke={colors[edge.status]} fill="none" strokeWidth={2} strokeDasharray={edge.status === 'confirmed' ? undefined : '6 4'} markerEnd={`url(#${marker})`} /><title>{edge.id}: {edge.source} → {edge.target} · {edge.status}</title></g>
      })}
      {graph.nodes.map(node => { const p = positions.get(node.id)!; return <g key={node.id} role="button" tabIndex={0} aria-label={node.title || node.id} onClick={() => setSelected(node)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSelected(node) } }}>
        <rect x={p.x - 110} y={p.y - 28} width={220} height={56} rx={8} fill="var(--bf-bg, white)" stroke="#64748b" />
        <text x={p.x} y={p.y - 4} textAnchor="middle" fill="currentColor" fontSize={13}>{(node.title || node.id).slice(0, 24)}</text><text x={p.x} y={p.y + 16} textAnchor="middle" fill="currentColor" fontSize={11}>{node.department.slice(0, 22)}</text><title>{node.title} · {node.role}</title>
      </g> })}
    </svg></div>
    <ul>{graph.edges.map(edge => <li key={edge.id}><button style={{ borderLeft: `5px solid ${colors[edge.status]}` }} onClick={() => setSelected(edge)}>{edge.source} → {edge.target} · {edge.kind === 'document' ? (zh ? '文件流' : 'Document') : (zh ? '信息流' : 'Information')} · {({ confirmed: zh ? '已确认' : 'Confirmed', inferred: zh ? '推断' : 'Inferred', missing: zh ? '缺失' : 'Missing', conflict: zh ? '冲突' : 'Conflict' })[edge.status]}{edge.rework ? (zh ? ' · 返工' : ' · Rework') : ''}</button></li>)}</ul>
    {selected && <div aria-label={zh ? '图元素详情' : 'Graph element details'}><h4>{'title' in selected ? selected.title : `${selected.source} → ${selected.target}`}</h4><p>{'trigger' in selected ? `${selected.role} · ${selected.trigger}` : selected.rationale}</p>{'condition' in selected && <p>{selected.condition}</p>}{'confirmation' in selected && <p>{selected.confirmation}</p>}{'inputs' in selected && <p>{zh ? '输入 / 输出' : 'Inputs / outputs'}: {selected.inputs.join(', ')} / {selected.outputs.join(', ')}</p>}<ul>{selected.references.map((r, i) => <li key={i}>{r.material_id} · v{r.version} · {r.locator.sheet} · {r.locator.kind} {r.locator.start}–{r.locator.end}</li>)}</ul></div>}
  </section>
}

export function FlowEditor({ initial }: { initial: FlowGraph }) {
  const { language } = useUI(), zh = language === 'zh'
  const [graph, setGraph] = useState(initial), [request, setRequest] = useState(''), [error, setError] = useState('')
  const change = (patch: Partial<FlowGraph>) => { setGraph(g => ({ ...g, ...patch })); setRequest(''); setError('') }
  const node = (index: number, patch: Partial<Node>) => change({ nodes: graph.nodes.map((n, i) => i === index ? { ...n, ...patch } : n) })
  const edge = (index: number, patch: Partial<Edge>) => change({ edges: graph.edges.map((n, i) => i === index ? { ...n, ...patch } : n) })
  const cleanRefs = (refs: Ref[]) => refs.map(r => ({ ...r, locator: { kind: r.locator.kind, ...(r.locator.kind !== 'lines' ? { sheet: r.locator.sheet } : {}), ...(r.locator.kind !== 'header' ? { start: r.locator.start, end: r.locator.end } : {}) } }))
  function prepare(e: FormEvent) {
    e.preventDefault(); setError('')
    if (!graph.nodes.length || graph.nodes.some(n => !n.references.length) || graph.edges.some(e => !graph.nodes.some(n => n.id === e.source) || !graph.nodes.some(n => n.id === e.target)) || new Set(graph.nodes.map(n => n.id)).size !== graph.nodes.length || new Set(graph.edges.map(n => n.id)).size !== graph.edges.length) { setError(zh ? '节点必须有依据，节点/关系标识不能重复。' : 'Nodes need evidence and node/edge identifiers must be unique.'); return }
    const refs = [...graph.nodes, ...graph.edges].flatMap(item => item.references)
    if (refs.some(r => r.locator.kind !== 'header' && Number(r.locator.end) < Number(r.locator.start)) || graph.edges.some(e => e.status !== 'missing' && !e.references.length || e.status === 'conflict' && new Set(e.references.map(r => JSON.stringify(r))).size < 2)) { setError(zh ? '检查来源区间和关系依据；冲突需两个不同来源。' : 'Check source ranges and edge evidence; conflicts need two distinct sources.'); return }
    const value = { id: graph.id, project_id: graph.project_id, title: graph.title, departments: graph.departments, opportunity_id: graph.opportunity_id, opportunity_version: graph.opportunity_version, expected_seq: graph.seq ?? 0,
      nodes: graph.nodes.map(n => ({ ...n, references: cleanRefs(n.references) })), edges: graph.edges.map(e => ({ id: e.id, source: e.source, target: e.target, kind: e.kind, status: e.status, rationale: e.rationale, rework: e.rework, references: cleanRefs(e.references), ...(e.condition ? { condition: e.condition } : {}), ...(e.status === 'confirmed' ? { confirmation: e.confirmation } : {}) })) }
    const body = JSON.stringify({ graph: value }, null, 2)
    if (body.length > 60000) { setError(zh ? '图过大，请拆分后审批。' : 'Graph is too large; split it for approval.'); return }
    setRequest(`Please call discovery_graph_save with these exact arguments, and wait for native approval:\n${body}`)
  }
  return <section aria-label={zh ? '流程图编辑' : 'Flow editor'}><h3>{zh ? '流程草图编辑' : 'Edit flow draft'}</h3><p>{graph.opportunity_id} · v{graph.opportunity_version} · {zh ? '图版本' : 'Graph version'} {graph.seq ?? 0}</p><FlowDiagram graph={graph} />
    <form onSubmit={prepare}>
      <label>{zh ? '图标识' : 'Graph ID'}<input required pattern="[a-zA-Z0-9]([a-zA-Z0-9_]|-){0,79}" readOnly={!!graph.seq} value={graph.id} onChange={e => change({ id: e.target.value })} /></label>
      <label>{zh ? '图标题' : 'Graph title'}<input required maxLength={200} value={graph.title} onChange={e => change({ title: e.target.value })} /></label>
      {graph.nodes.map((n, i) => <fieldset key={i}><legend>{zh ? '节点' : 'Node'} {i + 1}</legend>
        {(['id', 'title', 'role', 'trigger'] as const).map((key, j) => <label key={key}>{zh ? ['节点标识', '节点标题', '负责角色', '触发条件'][j] : key}<input required maxLength={key === 'trigger' ? 1200 : 200} {...(key === 'id' ? { pattern: '[a-zA-Z0-9]([a-zA-Z0-9_]|-){0,79}' } : {})} value={n[key]} onChange={e => node(i, { [key]: e.target.value })} /></label>)}
        <label>{zh ? '节点部门' : 'Node department'}<select required value={n.department} onChange={e => node(i, { department: e.target.value })}>{graph.departments.map(d => <option key={d}>{d}</option>)}</select></label>
        {(['inputs', 'outputs'] as const).map(key => <label key={key}>{key}<textarea value={n[key].join('\n')} onChange={e => node(i, { [key]: e.target.value.split('\n') })} onBlur={e => node(i, { [key]: lines(e.target.value) })} /></label>)}
        <Sources value={n.references} onChange={references => node(i, { references })} />
        <button type="button" disabled={graph.edges.some(e => e.source === n.id || e.target === n.id)} onClick={() => change({ nodes: graph.nodes.filter((_, j) => i !== j) })}>{zh ? '删除无关联节点' : 'Remove unlinked node'}</button>
      </fieldset>)}
      <button type="button" disabled={graph.nodes.length >= 50} onClick={() => change({ nodes: [...graph.nodes, { id: '', title: '', department: graph.departments[0]!, role: '', trigger: '', inputs: [], outputs: [], references: [ref()] }] })}>{zh ? '添加节点' : 'Add node'}</button>
      {graph.edges.map((v, i) => <fieldset key={i}><legend>{zh ? '关系' : 'Edge'} {i + 1}</legend>
        <label>{zh ? '关系标识' : 'Edge ID'}<input required pattern="[a-zA-Z0-9]([a-zA-Z0-9_]|-){0,79}" value={v.id} onChange={e => edge(i, { id: e.target.value })} /></label>
        {(['source', 'target'] as const).map((key, j) => <label key={key}>{zh ? ['起点', '终点'][j] : key}<select aria-label={zh ? ['起点', '终点'][j] : key} required value={v[key]} onChange={e => edge(i, { [key]: e.target.value })}><option value="">—</option>{graph.nodes.filter(n => n.id).map(n => <option key={n.id} value={n.id}>{n.title || n.id}</option>)}</select></label>)}
        <label>{zh ? '流类型' : 'Flow type'}<select value={v.kind} onChange={e => edge(i, { kind: e.target.value as Edge['kind'] })}><option value="information">{zh ? '信息流' : 'Information'}</option><option value="document">{zh ? '文件流' : 'Document'}</option></select></label>
        <label>{zh ? '依据状态' : 'Evidence status'}<select value={v.status} onChange={e => edge(i, { status: e.target.value as Edge['status'] })}>{Object.keys(colors).map((s, j) => <option key={s} value={s}>{zh ? ['已确认', '推断', '缺失', '冲突'][j] : s}</option>)}</select></label>
        <label>{zh ? '关系说明' : 'Rationale'}<textarea required maxLength={1200} value={v.rationale} onChange={e => edge(i, { rationale: e.target.value })} /></label>
        <label>{zh ? '分支条件（可选）' : 'Branch condition (optional)'}<input maxLength={1200} value={v.condition ?? ''} onChange={e => edge(i, { condition: e.target.value })} /></label>
        <label><input type="checkbox" checked={v.rework} onChange={e => edge(i, { rework: e.target.checked })} />{zh ? '返工关系' : 'Rework edge'}</label>
        {v.status === 'confirmed' && <label>{zh ? '人工确认说明' : 'Human confirmation'}<textarea required maxLength={1200} value={v.confirmation ?? ''} onChange={e => edge(i, { confirmation: e.target.value })} /></label>}
        <Sources value={v.references} onChange={references => edge(i, { references })} /><button type="button" onClick={() => change({ edges: graph.edges.filter((_, j) => i !== j) })}>{zh ? '删除关系' : 'Remove edge'}</button>
      </fieldset>)}
      <button type="button" disabled={!graph.nodes.length || graph.edges.length >= 100} onClick={() => change({ edges: [...graph.edges, { id: '', source: '', target: '', kind: 'information', status: 'missing', rationale: '', rework: false, references: [] }] })}>{zh ? '添加关系' : 'Add edge'}</button>
      <button type="submit">{zh ? '准备流程图审批请求' : 'Prepare flow approval'}</button>
    </form>
    {error && <p role="alert">{error}</p>}{request && <><p>{zh ? '尚未保存。复制到原生对话并核对审批。' : 'Not saved. Copy into native chat and review the approval.'}</p><textarea readOnly rows={10} aria-label={zh ? '流程图审批请求' : 'Flow approval request'} value={request} /><button onClick={() => { void navigator.clipboard.writeText(request).catch(() => setError(zh ? '复制失败，请手动选择。' : 'Copy failed; select manually.')) }}>{zh ? '复制流程图请求' : 'Copy flow request'}</button></>}
  </section>
}
