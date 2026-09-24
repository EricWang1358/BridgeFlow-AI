import { useEffect, useState } from 'react'
import { api, useUI } from './ui.ts'

/**
 * What an approval card needs besides the raw arguments: which workspace asked, one
 * sentence saying what will happen to what, and which arguments are plumbing (ids,
 * sequence numbers, digests) rather than something a person checks.
 *
 * A card that shows `workflow_record · template: settlement_basis · said: …` makes a
 * person reverse-engineer the request from parameter names (2026-09-24 feedback). The
 * tool name and ids stay available under "technical details" for the audit-minded.
 */
export type Detail = { label: string; value: string }

const AREAS: [RegExp, string][] = [
  [/^workflow_/, 'areaWorkflow'], [/^discovery_/, 'areaDiscovery'], [/^feishu_/, 'areaFeishu'],
  [/^quarantine_/, 'areaQuarantine'], [/^(confirm_mapping|confirm_column_match|dictionary_)/, 'areaDictionary'],
  [/^(convention_decide|risk_disposition)/, 'areaReview'],
]
export function areaOf(tool: string): string {
  return AREAS.find(([pattern]) => pattern.test(tool))?.[1] ?? 'areaOther'
}

/** Arguments that identify or version something; shown only under technical details. */
const TECHNICAL = new Set(['artifact_id', 'handoff_id', 'expected_seq', 'digest', 'confirmed_by', 'call_id',
  'decision_seq', 'policy_fingerprint', 'batch_id', 'review_id', 'report_id', 'expected_version', 'meeting_version',
  'opportunity_version', 'proposal_version'])
export function isTechnical(label: string): boolean {
  return TECHNICAL.has(label.split(' · ')[0]!)
}

type Catalogue = { templates: Record<string, { title: string; department: string }>
  stages: Record<string, { title: string; department: string }> }
let catalogue: Promise<Catalogue | null> | null = null

/** One plain sentence for the workflow tools, resolved against the declared catalogue. */
export function useApprovalSummary(tool: string, details: Detail[] | null): string {
  const { t } = useUI()
  const [names, setNames] = useState<Catalogue | null>(null)
  useEffect(() => {
    if (!tool.startsWith('workflow_')) return
    catalogue ??= api<Catalogue>('/workflow/catalogue').catch(() => null)
    let live = true
    void catalogue.then(value => { if (live) setNames(value) })
    return () => { live = false }
  }, [tool])
  if (!details) return ''
  const arg = (name: string) => details.find(d => d.label === name)?.value ?? ''
  const said = details.filter(d => d.label.startsWith('said · ')).length
  const template = (id: string) => {
    const found = names?.templates[id]
    return found ? t('summaryTemplate').replace('{title}', found.title).replace('{department}', found.department) : id
  }
  const stage = (handoff: string) => {
    const found = names?.stages[handoff.split(':')[0]!]
    return found ? t('summaryStage').replace('{title}', found.title).replace('{department}', found.department) : t('summaryThisHandoff')
  }
  switch (tool) {
    case 'workflow_record':
      return arg('artifact_id')
        ? t('summaryRecordAnswer').replace('{n}', String(said))
        : t('summaryRecordNew').replace('{n}', String(said)).replace('{template}', template(arg('template')))
    case 'workflow_approve_submit': return t('summaryApproveSubmit')
    case 'workflow_handoff': {
      const action = arg('action')
      const key = `summaryHandoff_${action}`
      return t(key) === key ? '' : t(key).replace('{stage}', stage(arg('handoff_id')))
    }
    case 'workflow_accept_scope':
      return t('summaryAcceptScope').replace('{project}', arg('project_id')).replace('{decision}', arg('decision_id'))
    default: return ''
  }
}
