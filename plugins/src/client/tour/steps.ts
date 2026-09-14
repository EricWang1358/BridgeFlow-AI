export type Track = 'core' | 'review' | 'quotation'
export type Step = { id: string; target: string; event?: string; pane?: 'sources' | 'studio'; view?: 'integration' | 'source' | 'quotation' }
export const tours: Record<Track, Step[]> = {
  core: [
    { id: 'sample', target: 'sample', event: 'sample', pane: 'sources' },
    { id: 'master', target: 'master-open', event: 'master', pane: 'studio' },
    { id: 'result', target: 'master-status', pane: 'studio', view: 'integration' },
    { id: 'issues', target: 'master-issues', event: 'issues', pane: 'studio', view: 'integration' },
    { id: 'questionResult', target: 'master-questions', pane: 'studio', view: 'integration' },
    { id: 'evidence', target: 'master-evidence-open', event: 'evidence', pane: 'studio', view: 'integration' },
    { id: 'source', target: 'evidence-source', event: 'source', pane: 'studio' },
    { id: 'sourceDetails', target: 'source-details', event: 'sourceDetails', pane: 'studio', view: 'source' },
    { id: 'sourceVerified', target: 'source-provenance', pane: 'studio', view: 'source' },
    { id: 'download', target: 'master-download', event: 'download', pane: 'studio', view: 'integration' },
    { id: 'named', target: 'notebook-name', event: 'named' },
    { id: 'saved', target: 'notebook-save', event: 'saved' },
  ],
  review: [
    { id: 'reviewIntro', target: 'review-start', pane: 'studio' },
    { id: 'reviewState', target: 'state-open', pane: 'studio' },
    { id: 'reviewHistory', target: 'artifacts', pane: 'studio' },
  ],
  quotation: [
    { id: 'quoteOpen', target: 'quotation-open', event: 'quotation', pane: 'studio' },
    { id: 'quoteScope', target: 'quotation-scope', pane: 'studio', view: 'quotation' },
  ],
}
export const TOUR_VERSION = 1
export const required = tours.core.flatMap(s => s.event ? [s.event] : [])
