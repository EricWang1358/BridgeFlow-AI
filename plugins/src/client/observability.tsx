import { useEffect, useState } from 'react'
import { api, describeError, useUI, useGloss } from './ui.ts'
import { Explain } from './explain.tsx'

/**
 * What the system decided, and how it scores against its own claims.
 *
 * Two readings of the same product. The journal is what happened: every request, its
 * outcome, how long it took, and — when it refused — the sentence it refused with, in its own
 * words. The report is what should happen: the acceptance suite over three held-out
 * industries plus the adversarial half, generated rather than written.
 *
 * The refusals are deliberately the loudest thing on the page. A system whose defining
 * behaviour is "say no when the evidence is missing" should be able to show how often it did,
 * and for what — otherwise that claim is only a sentence in a document.
 */
type Entry = { trace: string; at: string; surface: string; method: string; status: number
  outcome: string; ms: number; actor: string; reason: string; facts: Record<string, unknown> }
type Journal = { day: string; total: number; by_outcome: Record<string, number>; median_ms: number
  slowest_ms: number; refusal_reasons: { reason: string; count: number }[]; entries: Entry[]; days: string[] }
type Check = { industry: string; name: string; passed: boolean; detail: string; owner: string; track: string }
type Report = { generated_at: string; passed?: number; total?: number
  tracks: Record<string, { passed: number; total: number }>; checks: Check[]; refusal?: string; age_hours?: number | null }

const OUTCOMES = ['', 'refused', 'wrote', 'served'] as const

type Step = { at: string; agent: string; tool: string; outcome: string; ms: number; reason: string; trace: string }
type Run = { run: string; started_at: string; ended_at: string; steps: number; agents: string[]
  refused: number; ms: number; batch_id: string; tools: string[]; timeline: Step[]
  tokens?: { input: number; output: number; total: number; model_steps: number } }

/**
 * One agent run, drawn as lanes (E13/E14 evidence, rubric: observability).
 *
 * A run is one model-requested call and everything under it, so the captain's step and each
 * department subagent's calls share a root and belong on the same picture. The lane is the
 * agent, the mark is a tool call, and a refusal is marked by shape and word — never by colour
 * alone. Duration is drawn to scale within the run, because "which step took the time" is the
 * question a reader actually has.
 */
function RunLanes({ run }: { run: Run }) {
  const { t } = useUI()
  const lanes = run.agents.length ? run.agents : ['']
  const span = Math.max(run.timeline.reduce((total, step) => total + step.ms, 0), 1)
  let elapsed = 0
  const placed = run.timeline.map(step => {
    const left = (elapsed / span) * 100
    elapsed += step.ms
    return { step, left, width: Math.max((step.ms / span) * 100, 2) }
  })
  return <div className="bf-run-lanes">
    {lanes.map(agent => <div className="bf-run-lane" key={agent || 'unnamed'}>
      <span className="bf-run-lane-name">{agent ? t(`agent_${agent}`) === `agent_${agent}` ? agent : t(`agent_${agent}`) : t('agentUnknown')}</span>
      <span className="bf-run-lane-track">
        {placed.filter(({ step }) => (step.agent || '') === agent).map(({ step, left, width }) => <button
          key={step.trace} className="bf-run-mark" data-outcome={step.outcome}
          style={{ left: `${left}%`, width: `${width}%` }}
          title={`${step.tool} · ${step.ms} ms${step.reason ? ` · ${step.reason}` : ''}`}>
          <span className="bf-run-mark-label">{step.outcome === 'refused' ? '✕ ' : ''}{step.tool}</span>
        </button>)}
      </span>
    </div>)}
  </div>
}

export function AgentRuns({ batchId }: { batchId: string }) {
  const { t } = useUI()
  const [runs, setRuns] = useState<Run[] | null>(null), [error, setError] = useState('')
  const [open, setOpen] = useState('')
  useEffect(() => {
    const controller = new AbortController()
    setRuns(null); setError('')
    void api<{ runs: Run[] }>('/journal/runs', { signal: controller.signal })
      .then(value => setRuns(value.runs)).catch(e => { if (!controller.signal.aborted) setError(describeError(e, t)) })
    return () => controller.abort()
  }, [batchId])
  if (error) return <p role="alert" className="bf-error">{error}</p>
  if (!runs) return <p role="status" className="bf-loading">{t('loading')}</p>
  return <section className="bf-runs" aria-label={t('agentRuns')}>
    <h4>{t('agentRuns')}</h4>
    <p className="bf-hint">{t('agentRunsHelp')}</p>
    <Explain text={t('how_runs')} />
    {!runs.length && <p className="bf-hint">{t('agentRunsEmpty')}</p>}
    <ol className="bf-run-list">{runs.map(run => <li key={run.run}>
      <button className="bf-run-head" aria-expanded={open === run.run}
        onClick={() => setOpen(open === run.run ? '' : run.run)}>
        <span className="bf-run-when">{run.started_at.slice(11, 19)}</span>
        <span className="bf-run-summary">
          <strong>{run.steps} {t('runSteps')}</strong>
          <span className="bf-hint"> · {run.agents.length} {t('runAgents')} · {Math.round(run.ms)} ms
            {run.tokens?.model_steps ? ` · ${run.tokens.total.toLocaleString()} ${t('runTokens')}` : ''}
            {run.refused ? ` · ${run.refused} ${t('journal_refused')}` : ''}</span>
        </span>
        <span className="bf-run-tools bf-hint">{run.tools.slice(0, 3).join(' → ')}{run.tools.length > 3 ? ' …' : ''}</span>
      </button>
      {open === run.run && <div className="bf-run-detail">
        <RunLanes run={run} />
        <ol className="bf-run-steps">{run.timeline.map(step => <li key={step.trace} data-outcome={step.outcome}>
          <span className="bf-mono">{step.agent || t('agentUnknown')}</span>
          <span className="bf-mono">{step.tool}</span>
          <span>{step.ms} ms</span>
          <span>{t(`journal_${step.outcome}`)}</span>
          {step.reason && <span className="bf-run-step-reason">{step.reason}</span>}
        </li>)}</ol>
      </div>}
    </li>)}</ol>
  </section>
}

export function DecisionJournal({ batchId }: { batchId: string }) {
  const { t } = useUI(), gloss = useGloss()
  const [journal, setJournal] = useState<Journal | null>(null), [error, setError] = useState('')
  const [outcome, setOutcome] = useState<string>(''), [mine, setMine] = useState(true), [revision, setRevision] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    setJournal(null); setError('')
    const query = [outcome && `outcome=${outcome}`, mine && batchId && `batch_id=${batchId}`].filter(Boolean).join('&')
    void api<Journal>(`/journal${query ? `?${query}` : ''}`, { signal: controller.signal })
      .then(setJournal).catch(e => { if (!controller.signal.aborted) setError(describeError(e, t)) })
    return () => controller.abort()
  }, [outcome, mine, batchId, revision])
  if (error) return <p role="alert" className="bf-error">{error}</p>
  if (!journal) return <p role="status" className="bf-loading">{t('loading')}</p>
  return <section className="bf-journal" aria-label={t('decisionJournal')}>
    <div className="bf-card-head">
      <h4>{t('decisionJournal')} · {journal.day}</h4>
      <button onClick={() => setRevision(n => n + 1)}>{t('refresh')}</button>
    </div>
    <p className="bf-hint">{t('decisionJournalHelp')}</p>
    <Explain text={t('how_journal')} />

    <dl className="bf-facts bf-journal-summary">
      <dt>{t('journalDecisions')}</dt><dd>{journal.total}</dd>
      <dt>{t('journalRefused')}</dt><dd>{journal.by_outcome.refused ?? 0}</dd>
      <dt>{t('journalWrote')}</dt><dd>{journal.by_outcome.wrote ?? 0}</dd>
      <dt>{t('journalLatency')}</dt><dd>{journal.median_ms} / {journal.slowest_ms} ms</dd>
    </dl>

    {journal.refusal_reasons.length > 0 && <div className="bf-callout" data-tone="info">
      <h3>{t('journalTopRefusals')}</h3>
      <ol className="bf-journal-reasons">{journal.refusal_reasons.map(item => <li key={item.reason}>
        <span>{gloss.message(item.reason)}</span><span className="bf-badge">{item.count}</span>
      </li>)}</ol>
    </div>}

    <div className="bf-actions">
      {OUTCOMES.map(value => <button key={value || 'all'} aria-pressed={outcome === value}
        onClick={() => setOutcome(value)}>{t(value ? `journal_${value}` : 'journalAll')}</button>)}
      {batchId && <button aria-pressed={mine} onClick={() => setMine(!mine)}>{t('journalThisBatch')}</button>}
    </div>

    {!journal.entries.length && <p className="bf-hint">{t('journalEmpty')}</p>}
    <ol className="bf-journal-list">{journal.entries.map(item => <li key={item.trace + item.at} data-outcome={item.outcome}>
      <span className="bf-journal-time">{item.at.slice(11, 19)}</span>
      <span className="bf-journal-outcome" data-outcome={item.outcome}>{t(`journal_${item.outcome}`)}</span>
      <span className="bf-journal-surface bf-mono">{item.method} {item.surface}</span>
      <span className="bf-journal-ms">{item.ms} ms</span>
      {item.reason && <span className="bf-journal-reason">{gloss.message(item.reason)}</span>}
      <span className="bf-journal-trace bf-mono" title={t('journalTrace')}>{item.trace}</span>
    </li>)}</ol>
  </section>
}

export function EvalReport() {
  const { t } = useUI(), gloss = useGloss()
  const [report, setReport] = useState<Report | null>(null), [error, setError] = useState('')
  useEffect(() => {
    const controller = new AbortController()
    void api<Report>('/eval/report', { signal: controller.signal })
      .then(setReport).catch(e => { if (!controller.signal.aborted) setError(describeError(e, t)) })
    return () => controller.abort()
  }, [])
  if (error) return <p role="alert" className="bf-error">{error}</p>
  if (!report) return <p role="status" className="bf-loading">{t('loading')}</p>
  if (report.refusal) return <section className="bf-eval" aria-label={t('evalReport')}>
    <h4>{t('evalReport')}</h4><p className="bf-hint">{gloss.message(report.refusal)}</p>
  </section>
  const failed = report.checks.filter(c => !c.passed)
  return <section className="bf-eval" aria-label={t('evalReport')}>
    <h4>{t('evalReport')}</h4>
    <p className="bf-hint">{t('evalReportHelp')}
      {report.age_hours !== null && report.age_hours !== undefined
        ? ` · ${t('evalGenerated')} ${report.age_hours} h`
        : ''}</p>
    <Explain text={t('how_eval')} />
    <dl className="bf-facts">
      {Object.entries(report.tracks).map(([track, counts]) => <div key={track} style={{ display: 'contents' }}>
        <dt>{t(`evalTrack_${track}`)}</dt><dd>{counts.passed} / {counts.total}</dd>
      </div>)}
    </dl>
    {/* A red row names the issue that owns it: that is what stops a failing expectation
        being deleted so the table turns green. */}
    {failed.length > 0
      ? <ul className="bf-records-list">{failed.map(check => <li key={`${check.industry}-${check.name}`}>
        <span><strong>{check.industry}</strong> · {check.name}</span>
        <span className="bf-hint">{check.detail}{check.owner ? ` · ${check.owner}` : ''}</span>
      </li>)}</ul>
      : <p className="bf-hint">{t('evalAllGreen')}</p>}
  </section>
}
