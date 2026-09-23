import { useUI } from './ui.ts'

/**
 * The template-filling workflow as one picture: every stage a record passes through, who
 * acts at that stage, and how many records sit there now.
 *
 * The states are the workflow's own (`workflow/lifecycle.py`); this only groups them into
 * what a person would call a step. It is drawn even when the board is empty, because the
 * flow is the thing to understand first — records only fill it in.
 */
export const FLOW = [
  { id: 'input', states: ['needs_input'], actor: 'flowActorPerson' },
  { id: 'review', states: ['ready_for_review'], actor: 'flowActorYou' },
  { id: 'approved', states: ['reviewed', 'submitting', 'submit_failed'], actor: 'flowActorSystem' },
  { id: 'recorded', states: ['data_ready'], actor: 'flowActorSystem' },
  { id: 'handed', states: ['waiting', 'returned'], actor: 'flowActorDownstream' },
  { id: 'working', states: ['in_progress'], actor: 'flowActorDownstream' },
  { id: 'done', states: ['completed'], actor: 'flowActorDownstream' },
] as const

export function WorkflowFlow({ counts }: { counts: Record<string, number> }) {
  const { t } = useUI()
  const names: Record<string, string> = { input: t('flowStage_input'), review: t('flowStage_review'), approved: t('flowStage_approved'),
    recorded: t('flowStage_recorded'), handed: t('flowStage_handed'), working: t('flowStage_working'), done: t('flowStage_done') }
  const actors: Record<string, string> = { flowActorPerson: t('flowActorPerson'), flowActorYou: t('flowActorYou'),
    flowActorSystem: t('flowActorSystem'), flowActorDownstream: t('flowActorDownstream') }
  return <ol className="bf-pipeline" aria-label={t('workflowFlow')}>
    {FLOW.map(stage => {
      const count = stage.states.reduce((n, state) => n + (counts[state] ?? 0), 0)
      return <li key={stage.id} data-stage={stage.id} data-actor={stage.actor} data-active={count > 0}>
        <span className="bf-pipeline-actor">{actors[stage.actor]}</span>
        <b>{names[stage.id]}</b>
        <span className="bf-pipeline-count">{count}</span>
      </li>
    })}
  </ol>
}
