export type Track = 'core' | 'review' | 'quotation' | 'workflow' | 'cases'
/** `optional`: the step still reacts to its action, but Next never waits for it. */
export type Step = { id: string; target: string; event?: string; optional?: true; pane?: 'sources' | 'studio'
  view?: 'integration' | 'source' | 'quotation' | 'data' | 'tasks' | 'discovery' | 'handoff' | 'overview' }
export const tours: Record<Track, Step[]> = {
  core: [
    { id: 'sample', target: 'sample', event: 'sample', pane: 'sources' },
    { id: 'master', target: 'master-open', event: 'master', pane: 'studio', view: 'data' },
    { id: 'result', target: 'master-status', pane: 'studio', view: 'integration' },
    { id: 'issues', target: 'master-issues', event: 'issues', pane: 'studio', view: 'integration' },
    { id: 'questionResult', target: 'master-questions', pane: 'studio', view: 'integration' },
    { id: 'evidence', target: 'master-evidence-open', event: 'evidence', pane: 'studio', view: 'integration' },
    { id: 'source', target: 'evidence-source', event: 'source', pane: 'studio' },
    { id: 'sourceDetails', target: 'source-details', event: 'sourceDetails', pane: 'studio', view: 'source' },
    { id: 'sourceVerified', target: 'source-provenance', pane: 'studio', view: 'source' },
    { id: 'download', target: 'master-download', event: 'download', optional: true, pane: 'studio', view: 'integration' },
    { id: 'named', target: 'notebook-name', event: 'named', optional: true },
    { id: 'saved', target: 'notebook-save', event: 'saved' },
  ],
  review: [
    { id: 'reviewIntro', target: 'review-start', pane: 'studio', view: 'tasks' },
    { id: 'reviewState', target: 'state-open', pane: 'studio' },
    { id: 'reviewHistory', target: 'artifacts', pane: 'studio' },
  ],
  // Inside one of the extra sample notebooks: where its planted problems show, how each is
  // settled, and when the month is ready for review. Nothing to do but read; no model call.
  cases: [
    { id: 'caseGuide', target: 'case-guide', pane: 'studio', view: 'tasks' },
    { id: 'caseItems', target: 'open-items', pane: 'studio', view: 'tasks' },
    { id: 'caseAsk', target: 'settle-ask-all', pane: 'studio', view: 'tasks' },
    { id: 'caseData', target: 'master-open', pane: 'studio', view: 'data' },
    { id: 'caseReview', target: 'review-start', pane: 'studio', view: 'tasks' },
  ],
  quotation: [
    { id: 'quoteOpen', target: 'quotation-open', event: 'quotation', pane: 'studio' },
    { id: 'quoteScope', target: 'quotation-scope', pane: 'studio', view: 'quotation' },
  ],
  // From an idea to records moving between departments (#143 → E02). No model call: the
  // captain's steps are pointed out, not run, so the tour stays free and repeatable.
  workflow: [
    { id: 'wfSample', target: 'discovery-sample', event: 'discoverySample', pane: 'studio', view: 'discovery' },
    { id: 'wfGraph', target: 'flow-diagram', pane: 'studio', view: 'discovery' },
    { id: 'wfScore', target: 'discovery-kind-score', event: 'discoveryScore', pane: 'studio', view: 'discovery' },
    { id: 'wfQuadrant', target: 'quadrant-chart', pane: 'studio', view: 'discovery' },
    { id: 'wfScope', target: 'workflow-scope', pane: 'studio', view: 'handoff' },
    { id: 'wfRecords', target: 'workflow-sample', event: 'workflowSample', pane: 'studio', view: 'handoff' },
    { id: 'wfFlow', target: 'workflow-flow', pane: 'studio', view: 'handoff' },
    { id: 'wfTimeline', target: 'workflow-timeline', event: 'workflowTimeline', pane: 'studio', view: 'handoff' },
    { id: 'wfOverview', target: 'overview-kpis', pane: 'studio', view: 'overview' },
  ],
}
export const TOUR_VERSION = 1
/** Every core event the tour records; `required` are the ones completion waits for. */
export const coreEvents = tours.core.flatMap(s => s.event ? [s.event] : [])
export const required = tours.core.flatMap(s => s.event && !s.optional ? [s.event] : [])
/** Events a supplementary track waits for; they are not tied to a batch. */
export const trackEvents = ['quotation', ...tours.workflow.flatMap(s => s.event ? [s.event] : [])]
