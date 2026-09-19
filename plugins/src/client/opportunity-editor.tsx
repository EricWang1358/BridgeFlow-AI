import { useState, type FormEvent } from 'react'
import { Failure } from './failure.tsx'
import { useUI } from './ui.ts'

type Locator = { kind: 'header' | 'rows' | 'lines'; sheet?: string | null; start?: number | null; end?: number | null }
type Reference = { material_id: string; version: number; locator: Locator }
type Claim = { kind: string; text: string; basis: 'reported' | 'inferred'; references: Reference[] }
export type Opportunity = { id: string; project_id: string; title: string; departments: string[]; seq: number; claims: Claim[]; open_questions: string[]; stale_sources?: string[] }
const kinds = ['problem', 'input', 'output', 'human_checkpoint', 'rule_dependency', 'value_hypothesis'] as const
const emptyRef = (): Reference => ({ material_id: '', version: 1, locator: { kind: 'header', sheet: '' } })
const emptyClaim = (): Claim => ({ kind: 'problem', text: '', basis: 'inferred', references: [emptyRef()] })

export function OpportunityEditor({ project, initial }: { project: string; initial?: Opportunity | undefined }) {
  const { language } = useUI()
  const tr = (zh: string, en: string) => language === 'zh' ? zh : en
  const [claims, setClaims] = useState<Claim[]>(initial?.claims ?? [emptyClaim()])
  const [request, setRequest] = useState(''), [error, setError] = useState<unknown>(''), [copied, setCopied] = useState(false)
  function update(index: number, value: Partial<Claim>) { setClaims(items => items.map((item, i) => i === index ? { ...item, ...value } : item)) }
  function reference(index: number, refIndex: number, value: Partial<Reference>) {
    update(index, { references: claims[index]!.references.map((ref, i) => i === refIndex ? { ...ref, ...value } : ref) })
  }
  function prepare(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(''); setCopied(false)
    const form = new FormData(event.currentTarget)
    const proposal = { id: initial?.id ?? String(form.get('id')), project_id: project,
      title: String(form.get('title')), expected_seq: initial?.seq ?? 0,
      departments: initial?.departments ?? String(form.get('departments')).split('\n').map(v => v.trim()).filter(Boolean),
      open_questions: String(form.get('questions')).split('\n').map(v => v.trim()).filter(Boolean),
      claims: claims.map(claim => ({ ...claim, references: claim.references.map(ref => ({ ...ref, locator: {
        kind: ref.locator.kind,
        ...(ref.locator.kind !== 'lines' ? { sheet: ref.locator.sheet } : {}),
        ...(ref.locator.kind !== 'header' ? { start: ref.locator.start, end: ref.locator.end } : {}),
      } })) })),
    }
    if (!proposal.departments.length || proposal.departments.length > 20 || proposal.open_questions.length > 30) {
      setError(tr('请填写 1–20 个部门，待确认问题最多 30 条。', 'Enter 1–20 departments and at most 30 open questions.')); return
    }
    if (claims.some(c => c.references.some(r => r.locator.kind !== 'header' && Number(r.locator.end) < Number(r.locator.start)))) {
      setError(tr('来源结束行不能早于开始行。', 'Source end must not precede start.')); return
    }
    const body = JSON.stringify({ proposal }, null, 2)
    if (body.length > 60000) { setError(tr('提案过长，请拆分后审核。', 'Proposal is too large; split it for review.')); return }
    setRequest(`Please call discovery_propose with these exact arguments, and wait for native approval:\n${body}`)
  }
  return <section aria-label={tr('候选共创', 'Opportunity co-design')}>
    <h3>{tr(initial ? '修订候选' : '新建候选', initial ? 'Revise opportunity' : 'New opportunity')}</h3>
    <p>{tr('陈述必须带来源。材料存在不代表陈述正确；保留推断和待确认问题，交人复核。', 'Each statement needs sources. A source existing does not prove a claim; retain inferences and open questions for review.')}</p>
    {initial && <p>{tr('基于版本', 'Based on version')}: {initial.seq}</p>}
    {!!initial?.stale_sources?.length && <p role="alert">{tr('以下来源已修订，请重新核对版本：', 'Recheck revised sources: ')}{initial.stale_sources.join(', ')}</p>}
    <form onSubmit={prepare} onChange={() => { setRequest(''); setCopied(false) }}>
      <label>{tr('候选标识', 'Opportunity ID')}<input name="id" required pattern="[a-zA-Z0-9]([a-zA-Z0-9_]|-){0,79}" defaultValue={initial?.id ?? ''} readOnly={!!initial} /></label>
      <label>{tr('候选标题', 'Opportunity title')}<input name="title" required maxLength={200} defaultValue={initial?.title ?? ''} /></label>
      <label>{tr('涉及部门（每行一个准确名称）', 'Departments (one exact name per line)')}<textarea name="departments" required rows={3} defaultValue={initial?.departments.join('\n') ?? ''} readOnly={!!initial} /></label>
      {claims.map((claim, index) => <fieldset key={index}><legend>{tr('陈述', 'Statement')} {index + 1}</legend>
        <label>{tr('类别', 'Category')}<select value={claim.kind} onChange={e => update(index, { kind: e.target.value })}>{kinds.map((kind, i) => <option key={kind} value={kind}>{tr(['业务问题', '输入', '预期输出', '人工节点', '规则依赖', '价值假设'][i]!, kind)}</option>)}</select></label>
        <label>{tr('陈述内容', 'Statement text')}<textarea required maxLength={1200} rows={3} value={claim.text} onChange={e => update(index, { text: e.target.value })} /></label>
        <label>{tr('依据性质', 'Basis')}<select value={claim.basis} onChange={e => update(index, { basis: e.target.value as Claim['basis'] })}><option value="inferred">{tr('推断，待确认', 'Inferred, unconfirmed')}</option><option value="reported">{tr('材料或人员陈述', 'Reported by source/person')}</option></select></label>
        {claim.references.map((ref, ri) => <fieldset key={ri}><legend>{tr('来源', 'Source')} {ri + 1}</legend>
          <label>{tr('来源材料标识', 'Source material ID')}<input required pattern="[a-zA-Z0-9]([a-zA-Z0-9_]|-){0,79}" value={ref.material_id} onChange={e => reference(index, ri, { material_id: e.target.value })} /></label>
          <label>{tr('来源版本', 'Source version')}<input required type="number" min={1} step={1} value={ref.version} onChange={e => reference(index, ri, { version: Number(e.target.value) })} /></label>
          <label>{tr('位置类型', 'Location type')}<select value={ref.locator.kind} onChange={e => reference(index, ri, { locator: { kind: e.target.value as Locator['kind'], sheet: '', start: 1, end: 1 } })}><option value="header">{tr('工作表表头', 'Sheet header')}</option><option value="rows">{tr('工作表行区间', 'Sheet row range')}</option><option value="lines">{tr('文本行区间', 'Text line range')}</option></select></label>
          {ref.locator.kind !== 'lines' && <label>{tr('工作表名称', 'Sheet name')}<input required maxLength={200} value={ref.locator.sheet ?? ''} onChange={e => reference(index, ri, { locator: { ...ref.locator, sheet: e.target.value } })} /></label>}
          {ref.locator.kind !== 'header' && (['start', 'end'] as const).map(key => <label key={key}>{tr(key === 'start' ? '开始行' : '结束行', key === 'start' ? 'Start row' : 'End row')}<input required type="number" min={1} step={1} value={ref.locator[key] ?? 1} onChange={e => reference(index, ri, { locator: { ...ref.locator, [key]: Number(e.target.value) } })} /></label>)}
          <button type="button" disabled={claim.references.length === 1} onClick={() => { update(index, { references: claim.references.filter((_, i) => i !== ri) }); setRequest('') }}>{tr('移除此来源', 'Remove source')}</button>
        </fieldset>)}
        <button type="button" disabled={claim.references.length >= 10} onClick={() => { update(index, { references: [...claim.references, emptyRef()] }); setRequest('') }}>{tr('添加来源依据', 'Add source reference')}</button>
        <button type="button" disabled={claims.length === 1} onClick={() => { setClaims(items => items.filter((_, i) => i !== index)); setRequest('') }}>{tr('移除此陈述', 'Remove statement')}</button>
      </fieldset>)}
      <button type="button" disabled={claims.length >= 30} onClick={() => { setClaims(items => [...items, emptyClaim()]); setRequest('') }}>{tr('添加陈述', 'Add statement')}</button>
      <label>{tr('待确认问题（每行一条）', 'Open questions (one per line)')}<textarea name="questions" rows={3} defaultValue={initial?.open_questions.join('\n') ?? ''} /></label>
      <button type="submit">{tr('准备候选审批请求', 'Prepare proposal approval')}</button>
    </form>
    <Failure value={error}/>
    {request && <><p>{tr('尚未保存。粘贴到原生对话，核对后决定是否批准保存。', 'Not saved. Paste into native chat and review before approving the save.')}</p><textarea aria-label={tr('候选审批请求', 'Proposal approval request')} readOnly rows={10} value={request} /><button onClick={() => { void navigator.clipboard.writeText(request).then(() => setCopied(true)).catch(() => setError(tr('复制失败，请手动选择文本。', 'Copy failed; select the text manually.'))) }}>{tr('复制候选审批请求', 'Copy proposal approval request')}</button>{copied && <p role="status">{tr('已复制，等待您粘贴。', 'Copied; waiting for you to paste.')}</p>}</>}
  </section>
}
